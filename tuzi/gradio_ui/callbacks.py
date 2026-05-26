"""Gradio event handlers for the Tuzi AI Tutor."""

import re
from typing import Optional

import gradio as gr

from ..llm import LLMClient, LLMError
from ..models import (
    CommunicationStyle,
    Curriculum,
    Depth,
    LearningStyle,
    ReasoningFramework,
    SessionState,
    ToneStyle,
    UserProfile,
)
from ..session import SessionManager
from ..database import Database
from ..template_loader import render


def _strip_rich_markup(text: str) -> str:
    """Remove Rich console markup tags for plain-text display."""
    return re.sub(r"\[/?\w+\]", "", text)


def _format_curriculum_html(curriculum: Optional[Curriculum]) -> str:
    """Render curriculum as an HTML table."""
    if not curriculum:
        return "<p style='color: gray;'>No curriculum loaded. Use the Chat tab to /plan a topic.</p>"

    total = len(curriculum.prerequisites) + len(curriculum.main_curriculum)
    completed = sum(
        1
        for l in curriculum.prerequisites + curriculum.main_curriculum
        if l.status == "completed"
    )

    status_icons = {
        "pending": "&#9679;",
        "in_progress": "&#9654;",
        "completed": "&#10003;",
    }

    html = "<div style='font-family: sans-serif; max-width: 800px;'>"
    html += f"<h2>Curriculum: {curriculum.topic}</h2>"
    html += f"<p><strong>Progress:</strong> {completed}/{total} lessons completed</p>"

    def _lesson_table(lessons, title):
        if not lessons:
            return ""
        rows = ""
        for l in lessons:
            icon = status_icons.get(l.status, "&#9679;")
            desc = l.description[:80] + ("..." if len(l.description) > 80 else "")
            rows += (
                f"<tr><td><strong>{l.id}</strong></td>"
                f"<td>{l.title}</td>"
                f"<td>{desc}</td>"
                f"<td>{icon} {l.status}</td></tr>"
            )
        return (
            f"<h3>{title}</h3>"
            f"<table border='1' style='border-collapse: collapse; width: 100%;'>"
            f"<tr style='background: #f0f0f0;'>"
            f"<th>ID</th><th>Lesson</th><th>Description</th><th>Status</th></tr>"
            f"{rows}</table>"
        )

    html += _lesson_table(curriculum.prerequisites, "Prerequisites")
    html += _lesson_table(curriculum.main_curriculum, "Main Curriculum")
    html += "</div>"
    return html


_HELP_TEXT = """**Available Commands**

- `/config` — Set up or change your learning preferences
- `/plan <topic>` — Generate a study plan for a topic
- `/start [lesson_id]` — Start a lesson (e.g., `/start 1.1`)
- `/continue` — Continue the current lesson
- `/test` — Take a test on the current topic
- `/status` — View your profile and progress
- `/help` — Show this message
- `/exit` — End the session
"""


def _user_msg(content: str) -> dict:
    return {"role": "user", "content": content}


def _asst_msg(content: str) -> dict:
    return {"role": "assistant", "content": content}


class ChatCallbacks:
    """Handles chat messages with streaming and sync command routing."""

    def __init__(self, session_mgr: SessionManager, llm: LLMClient):
        self.session_mgr = session_mgr
        self.llm = llm

    def handle_message(
        self, message: str, history: list, ui_state: dict
    ):
        """Main chat callback. Routes to streaming or sync handlers."""
        if not message or not message.strip():
            yield self._outputs(history, ui_state)
            return

        history = history or []
        ui_state = ui_state or {}

        raw = message.strip()
        cmd = raw.split(maxsplit=1)[0] if raw.startswith("/") else None

        if cmd == "/start":
            yield from self._handle_start_streaming(raw, history, ui_state)
        elif cmd == "/plan":
            yield from self._handle_plan_streaming(raw, history, ui_state)
        elif cmd == "/config":
            yield from self._handle_config_cmd(raw, history, ui_state)
        elif cmd == "/help":
            yield from self._handle_help_cmd(raw, history, ui_state)
        elif cmd == "/exit":
            yield from self._handle_exit_cmd(raw, history, ui_state)
        else:
            yield from self._handle_sync(raw, history, ui_state)

    # ---- Streaming handlers ----

    def _handle_start_streaming(self, raw: str, history: list, ui_state: dict):
        history.append(_user_msg(raw))
        history.append(_asst_msg(""))
        yield self._outputs(history, ui_state)

        args = raw[len("/start"):].strip()
        success, error, sys_prompt, lesson_prompt = (
            self.session_mgr.prepare_start_lesson(args)
        )
        if not success:
            history[-1] = _asst_msg(f"**Error:** {error}")
            yield self._outputs(history, ui_state)
            return

        accumulated = ""
        try:
            for chunk in self.llm.chat_stream(
                [
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": lesson_prompt},
                ],
                max_tokens=4000,
            ):
                accumulated += chunk
                history[-1] = _asst_msg(accumulated)
                yield self._outputs(history, ui_state, status="lesson")
        except LLMError as e:
            history[-1] = _asst_msg(f"**Error:** {e}")
            yield self._outputs(history, ui_state)
            return

        self.session_mgr.finalize_start_lesson(lesson_prompt, accumulated)
        history[-1] = _asst_msg(accumulated)
        yield self._outputs(history, ui_state, status="lesson")

    def _handle_plan_streaming(self, raw: str, history: list, ui_state: dict):
        history.append(_user_msg(raw))
        history.append(_asst_msg(""))
        yield self._outputs(history, ui_state)

        args = raw[len("/plan"):].strip()
        success, error, sys_prompt, curric_prompt = (
            self.session_mgr.prepare_plan(args)
        )
        if not success:
            history[-1] = _asst_msg(f"**Error:** {error}")
            yield self._outputs(history, ui_state)
            return

        accumulated = ""
        try:
            for chunk in self.llm.chat_stream(
                [
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": curric_prompt},
                ],
                max_tokens=4000,
            ):
                accumulated += chunk
                history[-1] = _asst_msg(accumulated)
                yield self._outputs(history, ui_state, status="planning")
        except LLMError as e:
            history[-1] = _asst_msg(f"**Error:** {e}")
            yield self._outputs(history, ui_state)
            return

        curriculum = self.session_mgr.finalize_plan(accumulated, args)
        if curriculum:
            ui_state["topic"] = curriculum.topic
            ui_state["curriculum_id"] = curriculum.id
            ui_state["session_state"] = "curated"
            history[-1] = _asst_msg("Curriculum generated! See the **Curriculum** tab for details.")
            yield self._outputs(
                history, ui_state,
                curriculum_html=_format_curriculum_html(curriculum),
                status="curated",
            )
        else:
            history[-1] = _asst_msg("**Error:** Failed to parse curriculum. Please try again.")
            yield self._outputs(history, ui_state)

    # ---- Sync handler ----

    def _handle_sync(self, raw: str, history: list, ui_state: dict):
        result = self.session_mgr.handle_command(raw)

        if result.content == "__EXIT__":
            history.append(_user_msg(raw))
            history.append(_asst_msg("Session ended. You can close this tab."))
            yield self._outputs(history, ui_state)
            return

        if result.content == "__HELP__":
            history.append(_user_msg(raw))
            history.append(_asst_msg(_HELP_TEXT))
            yield self._outputs(history, ui_state, status=result.state.value)
            return

        content = _strip_rich_markup(result.content) if result.content else ""
        if content:
            history.append(_user_msg(raw))
            history.append(_asst_msg(content))

        curriculum_html = None
        if result.curriculum:
            curriculum_html = _format_curriculum_html(result.curriculum)
        elif ui_state.get("curriculum_id") and self.session_mgr.curriculum:
            curriculum_html = _format_curriculum_html(self.session_mgr.curriculum)

        ui_state["session_state"] = result.state.value
        yield self._outputs(
            history, ui_state,
            curriculum_html=curriculum_html,
            status=result.state.value,
        )

    # ---- Command redirects ----

    def _handle_config_cmd(self, raw: str, history: list, ui_state: dict):
        msg = (
            "Please go to the **Settings** tab to configure your learning preferences. "
            "Fill in the form and click **Save Profile**."
        )
        history.append(_user_msg(raw))
        history.append(_asst_msg(msg))
        ui_state["session_state"] = "wizard"
        yield self._outputs(history, ui_state, status="wizard")

    def _handle_help_cmd(self, raw: str, history: list, ui_state: dict):
        history.append(_user_msg(raw))
        history.append(_asst_msg(_HELP_TEXT))
        yield self._outputs(history, ui_state)

    def _handle_exit_cmd(self, raw: str, history: list, ui_state: dict):
        history.append(_user_msg(raw))
        history.append(_asst_msg("Session ended. You can close this tab."))
        yield self._outputs(history, ui_state)

    # ---- Helpers ----

    def _outputs(
        self, history, ui_state, curriculum_html=None, status=None
    ):
        if curriculum_html is None:
            curriculum_html = gr.skip()
        if status is None:
            status = ui_state.get("session_state", "uninitialized")
        status_md = f"**State:** {status}"
        return (history, curriculum_html, status_md, ui_state)


class SettingsCallbacks:
    """Handles Settings tab form submission."""

    def __init__(self, session_mgr: SessionManager, db: Database):
        self.session_mgr = session_mgr
        self.db = db

    def save_profile(
        self, name, depth, learning_style, communication_style,
        tone, reasoning, emojis, language,
    ):
        profile = UserProfile(
            name=name or "Student",
            depth=Depth(depth),
            learning_style=LearningStyle(learning_style),
            communication_style=CommunicationStyle(communication_style),
            tone_style=ToneStyle(tone),
            reasoning_framework=ReasoningFramework(reasoning),
            emojis_enabled=emojis,
            language=language or "English",
        )
        profile = self.db.save_profile(profile)
        self.session_mgr._profile = profile
        self.session_mgr.session.state = SessionState.READY

        return (
            "Profile saved successfully! You can now `/plan <topic>` in the Chat tab.",
            "**State:** ready",
        )

    def load_profile(self):
        """Return current profile values to populate the settings form."""
        profile = self.session_mgr.profile
        if profile:
            return (
                profile.name,
                profile.depth.value,
                profile.learning_style.value,
                profile.communication_style.value,
                profile.tone_style.value,
                profile.reasoning_framework.value,
                profile.emojis_enabled,
                profile.language,
            )
        return (
            "Student",
            Depth.HIGH_SCHOOL.value,
            LearningStyle.ACTIVE.value,
            CommunicationStyle.SOCRATIC.value,
            ToneStyle.ENCOURAGING.value,
            ReasoningFramework.CAUSAL.value,
            True,
            "English",
        )
