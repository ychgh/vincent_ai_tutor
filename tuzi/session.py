"""State machine and command routing for the Tuzi AI Tutor."""

import json
import re
import threading
from dataclasses import dataclass
from typing import Optional

from .cli.stream import stream_markdown
from .cli.wizard import run_wizard
from .database import Database
from .llm import LLMClient, LLMError
from .models import (
    Curriculum,
    Lesson,
    Message,
    Session,
    SessionState,
    TestQuestion,
    TestResult,
    UserProfile,
)
from .template_loader import render


@dataclass
class CommandResult:
    """Result of handling a command."""

    content: str
    state: SessionState
    is_error: bool = False
    curriculum: Optional[Curriculum] = None


class SessionManager:
    """Manages tutor state, command routing, and LLM orchestration."""

    def __init__(self, db: Database, llm: LLMClient, renderer=None):
        self.db = db
        self.llm = llm
        self.renderer = renderer
        self._lock = threading.Lock()
        self.session = Session()
        self._profile: Optional[UserProfile] = None
        self._curriculum: Optional[Curriculum] = None
        self._test_questions: list[TestQuestion] = []
        self._test_index: int = 0
        self._restore()

    def _restore(self):
        """Restore state from database on startup."""
        self._profile = self.db.get_profile()
        if self._profile:
            self.session.state = SessionState.READY

    # ---- Public helpers for streaming UIs ----

    def prepare_start_lesson(self, args: str) -> tuple:
        """Validate and prepare a /start command without calling the LLM.

        Returns (success, error_or_empty, system_prompt_or_none, lesson_prompt_or_none).
        On success: sets session state to LESSON, clears conversation history,
        marks lesson in_progress, and returns the constructed prompts.
        """
        with self._lock:
            return self._prepare_start_lesson_locked(args)

    def _prepare_start_lesson_locked(self, args: str) -> tuple:
        if self.session.state != SessionState.CURATED:
            return (False, "No curriculum available. Run /plan <topic> first.", None, None)

        if not self._curriculum:
            return (False, "No active curriculum. Run /plan <topic> first.", None, None)

        lesson_id = args.strip() if args else None
        if not lesson_id:
            all_lessons = self._curriculum.prerequisites + self._curriculum.main_curriculum
            for lesson in all_lessons:
                if lesson.status == "pending":
                    lesson_id = lesson.id
                    break
            if not lesson_id:
                return (False, "All lessons completed! Try /plan for a new topic or /test to review.", None, None)

        lesson = self._find_lesson(lesson_id)
        if lesson is None:
            return (False, f"Lesson {lesson_id} not found in the current curriculum.", None, None)

        self.session.state = SessionState.LESSON
        self.session.current_lesson_id = lesson_id
        self.session.active_curriculum_id = self._curriculum.id
        self.db.update_lesson_status(self._curriculum.id, lesson_id, "in_progress")

        system_prompt = render(
            "system.j2",
            depth=self._profile.depth.value,
            learning_style=self._profile.learning_style.value,
            communication_style=self._profile.communication_style.value,
            tone_style=self._profile.tone_style.value,
            reasoning_framework=self._profile.reasoning_framework.value,
            emojis_enabled=self._profile.emojis_enabled,
            language=self._profile.language,
        )

        lesson_prompt = render(
            "lesson.j2",
            topic=self._curriculum.topic,
            lesson_title=lesson.title,
            lesson_description=lesson.description,
            lesson_id=lesson_id,
        )

        self.session.conversation_history = [
            Message(role="system", content=system_prompt)
        ]

        return (True, "", system_prompt, lesson_prompt)

    def finalize_start_lesson(self, lesson_prompt: str, response: str) -> None:
        """Update conversation history after a lesson has been streamed."""
        with self._lock:
            self.session.conversation_history.append(
                Message(role="user", content=lesson_prompt)
            )
            self.session.conversation_history.append(
                Message(role="assistant", content=response)
            )

    def prepare_plan(self, args: str) -> tuple:
        """Validate and prepare a /plan command without calling the LLM.

        Returns (success, error_or_empty, system_prompt_or_none, curriculum_prompt_or_none).
        On success: sets session state to PLANNING and returns prompts.
        """
        with self._lock:
            return self._prepare_plan_locked(args)

    def _prepare_plan_locked(self, args: str) -> tuple:
        if not args:
            return (False, "Usage: /plan <topic> — e.g., /plan quantum mechanics", None, None)

        if self.session.state not in (SessionState.READY, SessionState.CURATED):
            return (False, f"Cannot plan in state: {self.session.state.value}. Run /config first.", None, None)

        if not self._profile:
            return (False, "No profile found. Run /config first.", None, None)

        self.session.state = SessionState.PLANNING
        topic = args.strip()
        self.session.current_topic = topic

        system_prompt = render(
            "system.j2",
            depth=self._profile.depth.value,
            learning_style=self._profile.learning_style.value,
            communication_style=self._profile.communication_style.value,
            tone_style=self._profile.tone_style.value,
            reasoning_framework=self._profile.reasoning_framework.value,
            emojis_enabled=self._profile.emojis_enabled,
            language=self._profile.language,
        )

        curriculum_prompt = render(
            "curriculum.j2",
            topic=topic,
            depth=self._profile.depth.value,
        )

        return (True, "", system_prompt, curriculum_prompt)

    def finalize_plan(self, response: str, topic: str):
        """Parse curriculum from LLM response, save to DB, update state.

        Returns the Curriculum object, or None on failure.
        Sets session state to CURATED on success, READY on failure.
        """
        with self._lock:
            return self._finalize_plan_locked(response, topic)

    def _finalize_plan_locked(self, response: str, topic: str):
        try:
            curriculum = self._parse_curriculum_response(response, topic)
            curriculum = self.db.save_curriculum(curriculum)
            self._curriculum = curriculum
            self.session.active_curriculum_id = curriculum.id
            self.session.state = SessionState.CURATED
            return curriculum
        except Exception:
            self.session.state = SessionState.READY
            return None

    @property
    def profile(self) -> Optional[UserProfile]:
        return self._profile

    @property
    def curriculum(self) -> Optional[Curriculum]:
        return self._curriculum

    @property
    def state(self) -> SessionState:
        return self.session.state

    # ---- Command Routing ----

    def handle_command(self, raw: str) -> CommandResult:
        """Route a command or free-text input to the appropriate handler."""
        with self._lock:
            return self._handle_command_locked(raw)

    def _handle_command_locked(self, raw: str) -> CommandResult:
        raw = raw.strip()

        if raw.startswith("/"):
            parts = raw.split(maxsplit=1)
            cmd = parts[0]
            args = parts[1] if len(parts) > 1 else ""
            return self._dispatch(cmd, args)

        # Free-text input
        if self.session.state == SessionState.LESSON:
            return self._handle_question(raw)
        elif self.session.state == SessionState.TEST:
            return self._handle_test_answer(raw)
        else:
            return CommandResult(
                content=f"Type [bold]/help[/bold] to see available commands. "
                f"Current state: [yellow]{self.session.state.value}[/yellow]",
                state=self.session.state,
            )

    def _dispatch(self, cmd: str, args: str) -> CommandResult:
        """Dispatch a slash command."""
        handlers = {
            "/config": self._handle_config,
            "/plan": self._handle_plan,
            "/start": self._handle_start,
            "/continue": self._handle_continue,
            "/test": self._handle_test,
            "/status": self._handle_status,
            "/help": self._handle_help,
            "/exit": self._handle_exit,
        }

        handler = handlers.get(cmd)
        if handler is None:
            return CommandResult(
                f"Unknown command: {cmd}. Type /help for available commands.",
                self.session.state,
                is_error=True,
            )
        return handler(args)

    # ---- Command Handlers ----

    def _handle_config(self, args: str) -> CommandResult:
        self.session.state = SessionState.WIZARD
        self._profile = run_wizard(self._profile)
        self._profile = self.db.save_profile(self._profile)
        self.session.state = SessionState.READY
        return CommandResult(
            content="[bold green]Profile saved![/bold green] Type /plan <topic> to get started.",
            state=SessionState.READY,
        )

    def _handle_plan(self, args: str) -> CommandResult:
        success, error, system_prompt, curriculum_prompt = self._prepare_plan_locked(args)
        if not success:
            return CommandResult(error, self.session.state, is_error=True)

        topic = self.session.current_topic

        try:
            if self.renderer is not None:
                chunks = self.llm.chat_stream(
                    [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": curriculum_prompt},
                    ],
                    max_tokens=4000,
                )
                response = stream_markdown(chunks)
            else:
                response = self.llm.chat(
                    [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": curriculum_prompt},
                    ],
                    max_tokens=4000,
                )

            curriculum = self._finalize_plan_locked(response, topic)
            if curriculum is None:
                return CommandResult(
                    "Failed to parse curriculum. Please try again.",
                    self.session.state,
                    is_error=True,
                )

            return CommandResult(
                content=self._format_curriculum_display(curriculum),
                state=SessionState.CURATED,
                curriculum=curriculum,
            )
        except LLMError as e:
            self.session.state = SessionState.READY
            return CommandResult(str(e), self.session.state, is_error=True)
        except Exception as e:
            self.session.state = SessionState.READY
            return CommandResult(
                f"Failed to generate curriculum: {e}", self.session.state, is_error=True
            )

    def _handle_start(self, args: str) -> CommandResult:
        success, error, system_prompt, lesson_prompt = self._prepare_start_lesson_locked(args)
        if not success:
            return CommandResult(error, self.session.state, is_error=True)

        try:
            if self.renderer is not None:
                chunks = self.llm.chat_stream(
                    [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": lesson_prompt},
                    ],
                    max_tokens=4000,
                )
                response = stream_markdown(chunks)
                self.renderer.print(
                    "\n[dim]─── Type /continue for more, or ask a question ───[/dim]"
                )
            else:
                response = self.llm.chat(
                    [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": lesson_prompt},
                    ],
                    max_tokens=4000,
                )

            self.session.conversation_history.append(
                Message(role="user", content=lesson_prompt)
            )
            self.session.conversation_history.append(
                Message(role="assistant", content=response)
            )

            if self.renderer is not None:
                return CommandResult(
                    content="",
                    state=SessionState.LESSON,
                )
            return CommandResult(
                content=response + "\n\n[dim]─── Type /continue for more, or ask a question ───[/dim]",
                state=SessionState.LESSON,
            )
        except LLMError as e:
            self.session.state = SessionState.CURATED
            return CommandResult(str(e), self.session.state, is_error=True)

    def _handle_continue(self, args: str) -> CommandResult:
        if self.session.state != SessionState.LESSON:
            return CommandResult(
                "No active lesson. Use /start to begin one.",
                self.session.state,
                is_error=True,
            )

        try:
            messages = self._build_messages("Continue the lesson from where you left off.")
            response = self.llm.chat(messages, max_tokens=4000)

            self.session.conversation_history.append(
                Message(role="assistant", content=response)
            )

            return CommandResult(
                content=response + "\n\n[dim]─── Type /continue for more, or ask a question ───[/dim]",
                state=SessionState.LESSON,
            )
        except LLMError as e:
            return CommandResult(str(e), self.session.state, is_error=True)

    def _handle_test(self, args: str) -> CommandResult:
        if self.session.state not in (SessionState.CURATED, SessionState.LESSON):
            return CommandResult(
                "No curriculum available. Run /plan <topic> first.",
                self.session.state,
                is_error=True,
            )

        prev_state = self.session.state
        self.session.state = SessionState.TEST

        if args.strip() == "evaluate":
            if self._test_index == 0:
                return CommandResult(
                    "No test in progress. Type /test to start a new test.",
                    self.session.state,
                    is_error=True,
                )
            return self._evaluate_test()

        try:
            system_prompt = render(
                "system.j2",
                depth=self._profile.depth.value,
                learning_style=self._profile.learning_style.value,
                communication_style=self._profile.communication_style.value,
                tone_style=self._profile.tone_style.value,
                reasoning_framework=self._profile.reasoning_framework.value,
                emojis_enabled=self._profile.emojis_enabled,
                language=self._profile.language,
            )

            topic = self._curriculum.topic if self._curriculum else self.session.current_topic
            test_prompt = render("test.j2", topic=topic or "the current topic")

            response = self.llm.chat(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": test_prompt},
                ],
                max_tokens=3000,
            )

            questions = self._parse_test_response(response)
            if not questions:
                return CommandResult(
                    "Failed to generate test questions. Please try again.",
                    prev_state,
                    is_error=True,
                )

            self._test_questions = questions
            self._test_index = 0
            self.session.state = SessionState.TEST

            first_q = questions[0]
            return CommandResult(
                content=f"📝 [bold]Test on {topic}[/bold] — {len(questions)} questions\n\n"
                f"[bold]Question {first_q.id}[/bold] ({first_q.difficulty})\n"
                f"{first_q.question}\n\n"
                f"[dim]Type your answer and press Enter.[/dim]",
                state=SessionState.TEST,
            )
        except LLMError as e:
            self.session.state = prev_state
            return CommandResult(str(e), self.session.state, is_error=True)

    def _handle_test_answer(self, answer: str) -> CommandResult:
        if self._test_index >= len(self._test_questions):
            return self._evaluate_test()

        self._test_questions[self._test_index].student_answer = answer
        self._test_index += 1

        if self._test_index < len(self._test_questions):
            q = self._test_questions[self._test_index]
            return CommandResult(
                content=f"[bold]Question {q.id}[/bold] ({q.difficulty})\n{q.question}",
                state=SessionState.TEST,
            )
        else:
            return self._evaluate_test()

    def _evaluate_test(self) -> CommandResult:
        try:
            system_prompt = render(
                "system.j2",
                depth=self._profile.depth.value,
                learning_style=self._profile.learning_style.value,
                communication_style=self._profile.communication_style.value,
                tone_style=self._profile.tone_style.value,
                reasoning_framework=self._profile.reasoning_framework.value,
                emojis_enabled=self._profile.emojis_enabled,
                language=self._profile.language,
            )

            qa_text = ""
            for q in self._test_questions:
                qa_text += f"Q{q.id}: {q.question}\nStudent answer: {q.student_answer}\n\n"

            eval_prompt = render("test_evaluate.j2", questions_and_answers=qa_text)

            response = self.llm.chat(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": eval_prompt},
                ]
            )

            parsed = self._parse_evaluation(response)
            if parsed:
                for i, (correct, feedback) in enumerate(parsed):
                    if i < len(self._test_questions):
                        self._test_questions[i].correct_answer = correct
                        self._test_questions[i].feedback = feedback

            correct_count = sum(
                1 for q in self._test_questions if q.correct_answer
            )
            score = correct_count / len(self._test_questions) if self._test_questions else 0

            # Save result
            result = TestResult(
                curriculum_id=self.session.active_curriculum_id or 0,
                topic=self.session.current_topic or "Unknown",
                questions=self._test_questions,
                score=score,
            )
            self.db.save_test_result(result)

            self.session.state = SessionState.CURATED
            self._test_questions = []
            self._test_index = 0

            return CommandResult(
                content=response + f"\n\n[bold]Score: {score:.0%}[/bold] ({correct_count}/{len(self._test_questions)})",
                state=SessionState.CURATED,
            )
        except LLMError as e:
            self.session.state = SessionState.CURATED
            return CommandResult(str(e), self.session.state, is_error=True)

    def _handle_question(self, question: str) -> CommandResult:
        try:
            messages = self._build_messages(question)
            response = self.llm.chat(messages, max_tokens=4000)

            self.session.conversation_history.append(
                Message(role="user", content=question)
            )
            self.session.conversation_history.append(
                Message(role="assistant", content=response)
            )

            return CommandResult(
                content=response + "\n\n[dim]─── Type /continue for more, or ask another question ───[/dim]",
                state=SessionState.LESSON,
            )
        except LLMError as e:
            return CommandResult(str(e), self.session.state, is_error=True)

    def _handle_status(self, args: str) -> CommandResult:
        output = ""
        if self._profile:
            profile = self._profile
            config_lines = [
                f"🎯 Depth: {profile.depth.value}",
                f"🧠 Learning Style: {profile.learning_style.value}",
                f"🗣️ Communication: {profile.communication_style.value}",
                f"🌟 Tone: {profile.tone_style.value}",
                f"🔎 Reasoning: {profile.reasoning_framework.value}",
                f"😀 Emojis: {'Enabled' if profile.emojis_enabled else 'Disabled'}",
                f"🌐 Language: {profile.language}",
            ]
            output += "[bold]Profile[/bold]\n" + "\n".join(config_lines) + "\n\n"

        output += f"[bold]State:[/bold] [yellow]{self.session.state.value}[/yellow]\n"

        if self._curriculum:
            total = len(self._curriculum.prerequisites) + len(self._curriculum.main_curriculum)
            completed = sum(
                1
                for l in self._curriculum.prerequisites + self._curriculum.main_curriculum
                if l.status == "completed"
            )
            output += f"[bold]Topic:[/bold] {self._curriculum.topic}\n"
            output += f"[bold]Progress:[/bold] {completed}/{total} lessons completed\n"

        if self.session.state == SessionState.LESSON:
            output += f"[bold]Current Lesson:[/bold] {self.session.current_lesson_id}\n"

        return CommandResult(content=output, state=self.session.state)

    def _handle_help(self, args: str) -> CommandResult:
        return CommandResult(content="__HELP__", state=self.session.state)

    def _handle_exit(self, args: str) -> CommandResult:
        return CommandResult(content="__EXIT__", state=self.session.state)

    # ---- Helpers ----

    def _build_messages(self, user_content: str) -> list[dict]:
        msgs = []
        for m in self.session.conversation_history:
            msgs.append({"role": m.role, "content": m.content})
        msgs.append({"role": "user", "content": user_content})
        self.session.conversation_history.append(
            Message(role="user", content=user_content)
        )
        return msgs

    def _find_lesson(self, lesson_id: str) -> Optional[Lesson]:
        if not self._curriculum:
            return None
        for lesson in self._curriculum.prerequisites + self._curriculum.main_curriculum:
            if lesson.id == lesson_id:
                return lesson
        return None

    def _parse_curriculum_response(self, response: str, topic: str) -> Curriculum:
        json_str = response

        # Try extracting JSON from code blocks
        code_block_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", response, re.DOTALL)
        if code_block_match:
            json_str = code_block_match.group(1)

        # Try extracting JSON object
        brace_match = re.search(r"\{.*\}", json_str, re.DOTALL)
        if brace_match:
            json_str = brace_match.group(0)

        data = json.loads(json_str)

        prerequisites = [
            Lesson(
                id=p.get("id", f"0.{i + 1}"),
                title=p["title"],
                description=p.get("description", ""),
                status="pending",
            )
            for i, p in enumerate(data.get("prerequisites", []))
        ]

        main_curriculum = [
            Lesson(
                id=m.get("id", f"1.{i + 1}"),
                title=m["title"],
                description=m.get("description", ""),
                status="pending",
            )
            for i, m in enumerate(data.get("main_curriculum", []))
        ]

        return Curriculum(
            topic=topic,
            depth=self._profile.depth.value if self._profile else "High School",
            prerequisites=prerequisites,
            main_curriculum=main_curriculum,
        )

    def _parse_test_response(self, response: str) -> list[TestQuestion]:
        json_str = response
        code_block_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", response, re.DOTALL)
        if code_block_match:
            json_str = code_block_match.group(1)

        brace_match = re.search(r"\[.*\]", json_str, re.DOTALL)
        if brace_match:
            json_str = brace_match.group(0)
        else:
            obj_match = re.search(r"\{.*\}", json_str, re.DOTALL)
            if obj_match:
                json_str = f"[{obj_match.group(0)}]"

        try:
            data = json.loads(json_str)
            if isinstance(data, dict):
                data = [data]
            return [
                TestQuestion(
                    id=i + 1,
                    difficulty=q.get("difficulty", "medium"),
                    question=q.get("question", str(q)),
                )
                for i, q in enumerate(data)
            ]
        except json.JSONDecodeError:
            return []

    def _parse_evaluation(self, response: str) -> list[tuple[str, str]]:
        json_str = response
        code_block_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", response, re.DOTALL)
        if code_block_match:
            json_str = code_block_match.group(1)

        brace_match = re.search(r"\[.*\]", json_str, re.DOTALL)
        if brace_match:
            json_str = brace_match.group(0)

        try:
            data = json.loads(json_str)
            if isinstance(data, dict):
                data = [data]
            return [
                (
                    q.get("correct_answer", ""),
                    q.get("feedback", str(q)),
                )
                for q in data
            ]
        except json.JSONDecodeError:
            return []

    def _format_curriculum_display(self, curriculum: Curriculum) -> str:
        total = len(curriculum.prerequisites) + len(curriculum.main_curriculum)
        output = f"📚 [bold]Curriculum: {curriculum.topic}[/bold] ({total} lessons)\n\n"

        if curriculum.prerequisites:
            output += "[bold underline]Prerequisites[/bold underline]\n"
            for l in curriculum.prerequisites:
                output += f"  [bold]{l.id}[/bold] — {l.title}: {l.description}\n"
            output += "\n"

        output += "[bold underline]Main Curriculum[/bold underline]\n"
        for l in curriculum.main_curriculum:
            output += f"  [bold]{l.id}[/bold] — {l.title}: {l.description}\n"

        output += "\n[dim]Type /start <id> to begin a lesson (e.g., /start 1.1)[/dim]"
        return output
