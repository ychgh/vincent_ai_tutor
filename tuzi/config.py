"""Application configuration loaded from environment and files."""

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class AppConfig:
    """Configuration for the Tuzi tutor application."""

    db_path: str = ""
    llm_model: str = ""
    data_dir: str = ""

    @classmethod
    def load(cls) -> "AppConfig":
        data_dir = os.getenv("TUZI_DATA_DIR", str(Path.home() / ".tuzi"))
        db_path = os.path.join(data_dir, "tutor.db")
        llm_model = os.getenv("LLM_MODEL", "deepseek-chat")

        os.makedirs(data_dir, exist_ok=True)

        return cls(db_path=db_path, llm_model=llm_model, data_dir=data_dir)
