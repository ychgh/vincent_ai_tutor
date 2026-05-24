"""Shared test fixtures."""

import os
import tempfile
from typing import Optional

import pytest

from tuzi.database import Database
from tuzi.models import (
    CommunicationStyle,
    Depth,
    LearningStyle,
    ReasoningFramework,
    ToneStyle,
    UserProfile,
)


@pytest.fixture
def db():
    """Create a temporary in-memory database for testing."""
    # Use a temp file so we get real SQLite behavior (no shared memory issues)
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    database = Database(path)
    yield database
    os.unlink(path)


@pytest.fixture
def sample_profile():
    """A sample user profile for testing."""
    return UserProfile(
        name="Test Student",
        depth=Depth.HIGH_SCHOOL,
        learning_style=LearningStyle.ACTIVE,
        communication_style=CommunicationStyle.SOCRATIC,
        tone_style=ToneStyle.ENCOURAGING,
        reasoning_framework=ReasoningFramework.CAUSAL,
        emojis_enabled=True,
        language="English",
    )


@pytest.fixture
def sample_curriculum_data():
    """Sample curriculum JSON as returned by LLM."""
    return {
        "prerequisites": [
            {"id": "0.1", "title": "Basic Python", "description": "Variables, functions, and control flow."},
            {"id": "0.2", "title": "Functions as Objects", "description": "Understanding first-class functions."},
        ],
        "main_curriculum": [
            {"id": "1.1", "title": "Intro to Decorators", "description": "What decorators are and why we use them."},
            {"id": "1.2", "title": "Writing Simple Decorators", "description": "Creating your first decorator."},
            {"id": "1.3", "title": "Decorators with Arguments", "description": "Parametrized decorators."},
        ],
    }
