"""Rich-based output rendering for the Tuzi CLI."""

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm, Prompt
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from ..models import Curriculum, SessionState, TestResult, UserProfile

console = Console()


class Renderer:
    """Renders tutor content using Rich components."""

    def show_banner(self):
        banner = Panel(
            "[bold bright_blue]"
            "╔══════════════════════════════════════╗\n"
            "║   🦌  Mr. Ranedeer AI Tutor  🦌     ║\n"
            "║         Tuzi CLI v0.1.0              ║\n"
            "╚══════════════════════════════════════╝"
            "[/bold bright_blue]",
            border_style="bright_blue",
        )
        console.print(banner)
        console.print(
            "[dim]Welcome! Type [/dim][bold]/help[/bold][dim] to see available commands.[/dim]\n"
        )

    def show_help(self, state: SessionState):
        help_text = Text()
        help_text.append("Commands:\n\n", style="bold underline")

        commands = {
            "/config": "Set up or change your learning preferences",
            "/plan <topic>": "Generate a study plan for a topic",
            "/start [lesson_id]": "Start a lesson (e.g. /start 1.1)",
            "/continue": "Continue the current lesson",
            "/test": "Take a test on the current topic",
            "/status": "View your profile and progress",
            "/help": "Show this help message",
            "/exit": "Save and exit",
        }

        for cmd, desc in commands.items():
            help_text.append(f"  {cmd}", style="bold bright_blue")
            help_text.append(f"  — {desc}\n")

        help_text.append(f"\nCurrent state: [bold yellow]{state.value}[/bold yellow]")
        console.print(Panel(help_text, title="Help"))

    def display_markdown(self, content: str):
        console.print(Markdown(content))

    def display_code(self, code: str, language: str = "python"):
        syntax = Syntax(code, language, theme="monokai", line_numbers=True)
        console.print(Panel(syntax, title=f"{language} code"))

    def display_config(self, profile: UserProfile):
        table = Table(title="Your Configuration", border_style="bright_blue")
        table.add_column("Setting", style="bold")
        table.add_column("Value")

        table.add_row("🎯 Depth", profile.depth.value)
        table.add_row("🧠 Learning Style", profile.learning_style.value)
        table.add_row("🗣️ Communication", profile.communication_style.value)
        table.add_row("🌟 Tone", profile.tone_style.value)
        table.add_row("🔎 Reasoning", profile.reasoning_framework.value)
        table.add_row("😀 Emojis", "Enabled" if profile.emojis_enabled else "Disabled")
        table.add_row("🌐 Language", profile.language)

        console.print(table)

    def display_curriculum(self, curriculum: Curriculum):
        def _lesson_status_icon(status: str) -> str:
            return {
                "pending": "[dim]○[/dim]",
                "in_progress": "[bold yellow]→[/bold yellow]",
                "completed": "[bold green]✓[/bold green]",
            }.get(status, "[dim]○[/dim]")

        total = len(curriculum.prerequisites) + len(curriculum.main_curriculum)
        completed = sum(
            1
            for l in curriculum.prerequisites + curriculum.main_curriculum
            if l.status == "completed"
        )

        title = f"📚 Curriculum: {curriculum.topic} [{completed}/{total} lessons done]"
        table = Table(title=title, border_style="bright_blue")
        table.add_column("ID", style="bold")
        table.add_column("Lesson", style="bold")
        table.add_column("Description")
        table.add_column("Status")

        if curriculum.prerequisites:
            table.add_section()
            for lesson in curriculum.prerequisites:
                table.add_row(
                    lesson.id,
                    lesson.title,
                    lesson.description[:60] + ("..." if len(lesson.description) > 60 else ""),
                    f"{_lesson_status_icon(lesson.status)} {lesson.status}",
                )

        if curriculum.main_curriculum:
            table.add_section()
            for lesson in curriculum.main_curriculum:
                table.add_row(
                    lesson.id,
                    lesson.title,
                    lesson.description[:60] + ("..." if len(lesson.description) > 60 else ""),
                    f"{_lesson_status_icon(lesson.status)} {lesson.status}",
                )

        console.print(table)

    def display_test_result(self, result: TestResult):
        if result.score is not None:
            color = "green" if result.score >= 0.7 else "yellow" if result.score >= 0.4 else "red"
            score_text = f"[bold {color}]{result.score:.0%}[/bold {color}]"
        else:
            score_text = "[dim]N/A[/dim]"

        console.print(Panel(f"Test on [bold]{result.topic}[/bold] — Score: {score_text}"))

        for q in result.questions:
            console.print(f"\n[bold]Q{q.id}[/bold] ({q.difficulty}): {q.question}")
            if q.student_answer:
                console.print(f"  Your answer: [italic]{q.student_answer}[/italic]")
            if q.feedback:
                console.print(f"  Feedback: {q.feedback}")

    def status(self, message: str):
        return console.status(message)

    def confirm_action(self, message: str) -> bool:
        return Confirm.ask(message)

    def select_option(
        self, options: list[str], prompt: str = "Choose an option"
    ) -> str:
        for i, opt in enumerate(options, 1):
            console.print(f"  [bold]{i}[/bold]. {opt}")
        choice = Prompt.ask(prompt, choices=[str(i) for i in range(1, len(options) + 1)])
        return options[int(choice) - 1]

    def print(self, message: str):
        console.print(message)
