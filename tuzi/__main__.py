"""Entry point for the Tuzi CLI tutor."""

import sys
from dotenv import load_dotenv


def main():
    load_dotenv()

    from .config import AppConfig
    from .database import Database
    from .llm import LLMClient
    from .session import SessionManager
    from .cli.renderer import Renderer
    from .cli.repl import TutorREPL

    config = AppConfig.load()
    db = Database(config.db_path)
    llm = LLMClient()
    renderer = Renderer()
    session_mgr = SessionManager(db, llm)

    repl = TutorREPL(session_mgr, renderer, db)
    repl.run()


if __name__ == "__main__":
    main()
