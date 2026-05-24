"""Tests for Pydantic data models."""

from datetime import datetime

from tuzi.models import (
    CommunicationStyle,
    Curriculum,
    Depth,
    LearningStyle,
    Lesson,
    Message,
    ReasoningFramework,
    Session,
    SessionState,
    TestQuestion,
    TestResult,
    ToneStyle,
    UserProfile,
)


class TestUserProfile:
    def test_default_values(self):
        profile = UserProfile()
        assert profile.name == "Student"
        assert profile.depth == Depth.HIGH_SCHOOL
        assert profile.learning_style == LearningStyle.ACTIVE
        assert profile.communication_style == CommunicationStyle.SOCRATIC
        assert profile.tone_style == ToneStyle.ENCOURAGING
        assert profile.reasoning_framework == ReasoningFramework.CAUSAL
        assert profile.emojis_enabled is True
        assert profile.language == "English"

    def test_custom_values(self):
        profile = UserProfile(
            name="Alice",
            depth=Depth.GRADUATE,
            learning_style=LearningStyle.VISUAL,
            communication_style=CommunicationStyle.FORMAL,
            tone_style=ToneStyle.NEUTRAL,
            reasoning_framework=ReasoningFramework.DEDUCTIVE,
            emojis_enabled=False,
            language="French",
        )
        assert profile.name == "Alice"
        assert profile.depth == Depth.GRADUATE
        assert profile.emojis_enabled is False
        assert profile.language == "French"

    def test_json_roundtrip(self, sample_profile):
        data = sample_profile.model_dump()
        restored = UserProfile(**data)
        assert restored.name == sample_profile.name
        assert restored.depth == sample_profile.depth


class TestCurriculum:
    def test_create_curriculum(self, sample_curriculum_data):
        prereqs = [
            Lesson(
                id=p["id"], title=p["title"], description=p["description"]
            )
            for p in sample_curriculum_data["prerequisites"]
        ]
        main = [
            Lesson(
                id=m["id"], title=m["title"], description=m["description"]
            )
            for m in sample_curriculum_data["main_curriculum"]
        ]
        curriculum = Curriculum(
            topic="Python Decorators",
            depth="High School",
            prerequisites=prereqs,
            main_curriculum=main,
        )
        assert curriculum.topic == "Python Decorators"
        assert len(curriculum.prerequisites) == 2
        assert len(curriculum.main_curriculum) == 3
        assert curriculum.prerequisites[0].id == "0.1"
        assert curriculum.main_curriculum[0].id == "1.1"

    def test_all_lessons(self):
        p = [Lesson(id="0.1", title="P1", description="Pre-req 1")]
        m = [Lesson(id="1.1", title="M1", description="Main 1")]
        c = Curriculum(
            topic="Test", depth="Undergraduate", prerequisites=p, main_curriculum=m
        )
        all_lessons = c.prerequisites + c.main_curriculum
        assert len(all_lessons) == 2


class TestSession:
    def test_default_state(self):
        session = Session()
        assert session.state == SessionState.UNINITIALIZED
        assert session.conversation_history == []
        assert session.active_curriculum_id is None

    def test_state_transition(self):
        session = Session()
        session.state = SessionState.READY
        assert session.state == SessionState.READY


class TestTestQuestion:
    def test_create_question(self):
        q = TestQuestion(
            id=1,
            difficulty="simple familiar",
            question="What is Python?",
            student_answer="A programming language.",
            correct_answer="A high-level programming language.",
            feedback="Good!",
        )
        assert q.id == 1
        assert q.difficulty == "simple familiar"
        assert q.student_answer == "A programming language."


class TestEnumValues:
    def test_depth_has_all_levels(self):
        values = [d.value for d in Depth]
        assert len(values) == 9
        assert "Elementary (Grade 1-6)" in values
        assert "Ph.D" in values

    def test_learning_styles_count(self):
        assert len(LearningStyle) == 6

    def test_communication_styles_count(self):
        assert len(CommunicationStyle) == 5

    def test_tone_styles_count(self):
        assert len(ToneStyle) == 5

    def test_reasoning_frameworks_count(self):
        assert len(ReasoningFramework) == 5
