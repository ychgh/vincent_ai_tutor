"""REPL loop for the Tuzi CLI tutor."""

from rich.prompt import Prompt

from ..database import Database
from ..models import SessionState
from ..session import SessionManager
from .renderer import Renderer


class TutorREPL:
    """Interactive REPL for the Tuzi AI Tutor."""

    def __init__(self, session_mgr: SessionManager, renderer: Renderer, db: Database):
        self.session_mgr = session_mgr
        self.renderer = renderer
        self.db = db

    def run(self):
        self.renderer.show_banner()
        self._check_profile()

        while True:
            try:
                prompt_text = self._build_prompt()
                raw = Prompt.ask(prompt_text)
                raw = raw.strip()

                if not raw:
                    continue

                result = self.session_mgr.handle_command(raw)

                if result.content == "__EXIT__":
                    self.renderer.print("[dim]Saving and exiting. Goodbye! 👋[/dim]")
                    break

                if result.content == "__HELP__":
                    self.renderer.show_help(self.session_mgr.state)
                    continue

                if result.content:
                    self.renderer.display_markdown(result.content)

            except KeyboardInterrupt:
                self.renderer.print("\n[dim]Use /exit to quit safely.[/dim]")
                continue
            except EOFError:
                break

    def _check_profile(self):
        if self.session_mgr.state == SessionState.UNINITIALIZED:
            self.renderer.print(
                "[yellow]No profile found![/yellow] "
                "Type [bold]/config[/bold] to set up your learning preferences."
            )
        else:
            self.renderer.print(
                f"[dim]Profile loaded. Type [bold]/help[/bold] to see commands. "
                f"State: [yellow]{self.session_mgr.state.value}[/yellow][/dim]\n"
            )

    def _build_prompt(self) -> str:
        state = self.session_mgr.state
        if state == SessionState.LESSON:
            return "[bold green]lesson[/bold green] > "
        elif state == SessionState.TEST:
            return "[bold yellow]test[/bold yellow] > "
        elif state == SessionState.WIZARD:
            return "[bold magenta]config[/bold magenta] > "
        else:
            topic = self.session_mgr.session.current_topic
            if topic:
                return f"[bold blue]tuzi[/bold blue] [{topic}] > "
            return "[bold blue]tuzi[/bold blue] > "
