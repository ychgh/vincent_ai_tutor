"""Data models for the Tuzi AI Tutor."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ---- Configuration Enums ----


class Depth(str, Enum):
    ELEMENTARY = "Elementary (Grade 1-6)"
    MIDDLE_SCHOOL = "Middle School (Grade 7-9)"
    HIGH_SCHOOL = "High School (Grade 10-12)"
    UNDERGRADUATE = "Undergraduate"
    GRADUATE = "Graduate (Bachelor Degree)"
    MASTERS = "Master's"
    DOCTORAL = "Doctoral Candidate (Ph.D Candidate)"
    POSTDOC = "Postdoc"
    PHD = "Ph.D"


class LearningStyle(str, Enum):
    VISUAL = "Visual"
    VERBAL = "Verbal"
    ACTIVE = "Active"
    INTUITIVE = "Intuitive"
    REFLECTIVE = "Reflective"
    GLOBAL = "Global"


class CommunicationStyle(str, Enum):
    FORMAL = "Formal"
    TEXTBOOK = "Textbook"
    LAYMAN = "Layman"
    STORY_TELLING = "Story Telling"
    SOCRATIC = "Socratic"


class ToneStyle(str, Enum):
    ENCOURAGING = "Encouraging"
    NEUTRAL = "Neutral"
    INFORMATIVE = "Informative"
    FRIENDLY = "Friendly"
    HUMOROUS = "Humorous"


class ReasoningFramework(str, Enum):
    DEDUCTIVE = "Deductive"
    INDUCTIVE = "Inductive"
    ABDUCTIVE = "Abductive"
    ANALOGICAL = "Analogical"
    CAUSAL = "Causal"


# ---- Domain Models ----


class UserProfile(BaseModel):
    """A student's learning configuration profile."""

    id: int = 0
    name: str = "Student"
    depth: Depth = Depth.HIGH_SCHOOL
    learning_style: LearningStyle = LearningStyle.ACTIVE
    communication_style: CommunicationStyle = CommunicationStyle.SOCRATIC
    tone_style: ToneStyle = ToneStyle.ENCOURAGING
    reasoning_framework: ReasoningFramework = ReasoningFramework.CAUSAL
    emojis_enabled: bool = True
    language: str = "English"
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class Lesson(BaseModel):
    """A single lesson node in a curriculum."""

    id: str  # e.g. "0.1", "1.1"
    title: str
    description: str
    status: str = "pending"  # pending | in_progress | completed


class Curriculum(BaseModel):
    """A full curriculum for a topic."""

    id: int = 0
    topic: str
    depth: str
    prerequisites: list[Lesson] = []
    main_curriculum: list[Lesson] = []
    created_at: datetime = Field(default_factory=datetime.now)
    active_lesson_id: Optional[str] = None


class SessionState(str, Enum):
    UNINITIALIZED = "uninitialized"
    WIZARD = "wizard"
    READY = "ready"
    PLANNING = "planning"
    CURATED = "curated"
    LESSON = "lesson"
    TEST = "test"


class Message(BaseModel):
    """A single message in a conversation."""

    role: str  # "system" | "user" | "assistant"
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)


class Session(BaseModel):
    """Runtime session state."""

    state: SessionState = SessionState.UNINITIALIZED
    active_curriculum_id: Optional[int] = None
    conversation_history: list[Message] = []
    current_topic: Optional[str] = None
    current_lesson_id: Optional[str] = None


class TestQuestion(BaseModel):
    """A test question with student answer and evaluation."""

    id: int
    difficulty: str  # "simple familiar", "complex familiar", "complex unfamiliar"
    question: str
    student_answer: str = ""
    correct_answer: str = ""
    feedback: str = ""


class TestResult(BaseModel):
    """Results from a completed test."""

    id: int = 0
    curriculum_id: int
    topic: str
    questions: list[TestQuestion] = []
    score: Optional[float] = None
    completed_at: datetime = Field(default_factory=datetime.now)
