"""Entry point for the Tuzi AI Tutor with UI selection."""

from dotenv import load_dotenv
import click


@click.command()
@click.option(
    "--ui",
    type=click.Choice(["cli", "gradio"]),
    default="cli",
    help="User interface to use.",
)
def main(ui: str):
    load_dotenv()

    from .config import AppConfig
    from .database import Database
    from .llm import LLMClient

    config = AppConfig.load()
    db = Database(config.db_path)
    llm = LLMClient()

    if ui == "gradio":
        from .session import SessionManager
        from .gradio_ui.app import run_gradio

        session_mgr = SessionManager(db, llm)
        run_gradio(session_mgr, db, llm)
    else:
        from .session import SessionManager
        from .cli.renderer import Renderer
        from .cli.repl import TutorREPL

        renderer = Renderer()
        session_mgr = SessionManager(db, llm, renderer)
        repl = TutorREPL(session_mgr, renderer, db)
        repl.run()


if __name__ == "__main__":
    main()
