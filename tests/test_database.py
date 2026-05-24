"""Tests for database CRUD operations."""

from tuzi.models import (
    Curriculum,
    Lesson,
    TestQuestion,
    TestResult,
    UserProfile,
)


class TestProfileCRUD:
    def test_save_and_get_profile(self, db, sample_profile):
        saved = db.save_profile(sample_profile)
        assert saved.id > 0

        loaded = db.get_profile()
        assert loaded is not None
        assert loaded.name == sample_profile.name
        assert loaded.depth == sample_profile.depth

    def test_no_profile_returns_none(self, db):
        assert db.get_profile() is None

    def test_update_existing_profile(self, db, sample_profile):
        saved = db.save_profile(sample_profile)
        saved.name = "Updated Name"
        db.save_profile(saved)

        loaded = db.get_profile()
        assert loaded is not None
        assert loaded.name == "Updated Name"


class TestCurriculumCRUD:
    def test_save_and_get_curriculum(self, db):
        curriculum = Curriculum(
            topic="Python Basics",
            depth="High School",
            prerequisites=[
                Lesson(id="0.1", title="Pre-req", description="A pre-requisite")
            ],
            main_curriculum=[
                Lesson(id="1.1", title="Lesson 1", description="First lesson"),
                Lesson(id="1.2", title="Lesson 2", description="Second lesson"),
            ],
        )
        saved = db.save_curriculum(curriculum)
        assert saved.id > 0

        loaded = db.get_curriculum(saved.id)
        assert loaded is not None
        assert loaded.topic == "Python Basics"
        assert len(loaded.prerequisites) == 1
        assert len(loaded.main_curriculum) == 2

    def test_list_curricula(self, db):
        c1 = Curriculum(topic="Topic A", depth="High School", prerequisites=[], main_curriculum=[])
        c2 = Curriculum(topic="Topic B", depth="Graduate", prerequisites=[], main_curriculum=[])
        db.save_curriculum(c1)
        db.save_curriculum(c2)

        all_curricula = db.get_curricula()
        assert len(all_curricula) == 2

    def test_get_nonexistent_curriculum(self, db):
        assert db.get_curriculum(999) is None

    def test_update_lesson_status(self, db):
        curriculum = Curriculum(
            topic="Test",
            depth="High School",
            prerequisites=[],
            main_curriculum=[
                Lesson(id="1.1", title="L1", description="First", status="pending")
            ],
        )
        saved = db.save_curriculum(curriculum)
        db.update_lesson_status(saved.id, "1.1", "completed")

        loaded = db.get_curriculum(saved.id)
        assert loaded is not None
        assert loaded.main_curriculum[0].status == "completed"


class TestTestResultCRUD:
    def test_save_and_get_results(self, db):
        result = TestResult(
            curriculum_id=1,
            topic="Python",
            questions=[
                TestQuestion(
                    id=1,
                    difficulty="simple",
                    question="Q1?",
                    student_answer="A1",
                )
            ],
            score=1.0,
        )
        saved = db.save_test_result(result)
        assert saved.id > 0

        results = db.get_test_results(1)
        assert len(results) == 1
        assert results[0].score == 1.0
        assert len(results[0].questions) == 1
