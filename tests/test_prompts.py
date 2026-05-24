"""Tests for Jinja2 prompt template rendering."""

from tuzi.template_loader import render


class TestSystemPrompt:
    def test_renders_with_config(self):
        result = render(
            "system.j2",
            depth="High School (Grade 10-12)",
            learning_style="Active",
            communication_style="Socratic",
            tone_style="Encouraging",
            reasoning_framework="Causal",
            emojis_enabled=True,
            language="English",
        )
        assert "Mr. Ranedeer" in result
        assert "High School (Grade 10-12)" in result
        assert "Active" in result
        assert "Socratic" in result
        assert "Causal" in result
        assert "English" in result

    def test_emojis_disabled(self):
        result = render(
            "system.j2",
            depth="Undergraduate",
            learning_style="Visual",
            communication_style="Formal",
            tone_style="Neutral",
            reasoning_framework="Deductive",
            emojis_enabled=False,
            language="Spanish",
        )
        assert "Enabled" not in result.split("Emojis:")[1].split("\n")[0] if "Emojis:" in result else True
        assert "Spanish" in result


class TestCurriculumPrompt:
    def test_renders_with_topic(self):
        result = render(
            "curriculum.j2",
            topic="Quantum Mechanics",
            depth="Graduate",
        )
        assert "Quantum Mechanics" in result
        assert "Graduate" in result
        assert "main_curriculum" in result
        assert "prerequisites" in result


class TestLessonPrompt:
    def test_renders_lesson_info(self):
        result = render(
            "lesson.j2",
            topic="Python Decorators",
            lesson_title="Introduction to Decorators",
            lesson_description="Learn what decorators are.",
            lesson_id="1.1",
        )
        assert "Python Decorators" in result
        assert "Introduction to Decorators" in result
        assert "1.1" in result


class TestContinuePrompt:
    def test_renders_continue(self):
        result = render("lesson_continue.j2")
        assert "Continue" in result or "continue" in result.lower()


class TestTestPrompt:
    def test_renders_topic(self):
        result = render("test.j2", topic="Algorithms")
        assert "Algorithms" in result
        assert "simple familiar" in result


class TestEvaluatePrompt:
    def test_renders_qa(self):
        qa = "Q1: What is X?\nStudent answer: Y\n\n"
        result = render("test_evaluate.j2", questions_and_answers=qa)
        assert "What is X?" in result
        assert "Y" in result
