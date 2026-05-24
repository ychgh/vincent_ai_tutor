# Testing

## Overview

The test suite covers models, database operations, and prompt template rendering. LLM integration and the REPL loop are tested manually (they require an API key and interactive terminal respectively).

## Test Structure

```
tests/
├── __init__.py
├── conftest.py          # Shared fixtures
├── test_models.py       # 28 tests total across 3 files
├── test_database.py
└── test_prompts.py
```

## Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_models.py -v

# Run with coverage (if installed)
pip install pytest-cov
pytest tests/ --cov=tuzi --cov-report=term-missing
```

## Fixtures (`conftest.py`)

### `db`
Creates a temporary SQLite database file for each test. Uses `tempfile.mkstemp` with automatic cleanup via `os.unlink`. Each test gets an isolated database with the full schema.

```python
@pytest.fixture
def db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    database = Database(path)
    yield database
    os.unlink(path)
```

### `sample_profile`
A pre-built `UserProfile` with High School depth, Active learning, Socratic communication, Encouraging tone, and Causal reasoning.

### `sample_curriculum_data`
A dictionary matching the expected JSON format from the LLM's curriculum response, with 2 prerequisites and 3 main curriculum lessons about Python decorators.

## Test Categories

### Model Tests (`test_models.py`) — 13 tests

| Class | Tests | What It Verifies |
|---|---|---|
| `TestUserProfile` | 3 | Default values match expectations; custom values override defaults; JSON serialization round-trip preserves data |
| `TestCurriculum` | 2 | Curriculum creation from parsed LLM response; concatenation of prereqs + main lessons |
| `TestSession` | 2 | Default state is UNINITIALIZED; state transitions work |
| `TestTestQuestion` | 1 | Question creation with all fields |
| `TestEnumValues` | 5 | All 5 enums have the correct number of members; specific values exist |

### Database Tests (`test_database.py`) — 8 tests

| Class | Tests | What It Verifies |
|---|---|---|
| `TestProfileCRUD` | 3 | Save creates an ID; get returns the saved profile; get returns None when empty; update modifies existing profile |
| `TestCurriculumCRUD` | 4 | Save + get round-trip preserves lessons; list returns all curricula; get nonexistent returns None; update_lesson_status persists changes |
| `TestTestResultCRUD` | 1 | Save + get round-trip preserves questions as JSON |

### Prompt Tests (`test_prompts.py`) — 7 tests

| Class | Tests | What It Verifies |
|---|---|---|
| `TestSystemPrompt` | 2 | Rendered output contains all configuration values; emojis disabled state excludes the emoji guideline |
| `TestCurriculumPrompt` | 1 | Topic and depth appear in rendered prompt; JSON structure fields present |
| `TestLessonPrompt` | 1 | Lesson metadata (topic, title, id) rendered correctly |
| `TestContinuePrompt` | 1 | Template renders without errors (minimal template) |
| `TestTestPrompt` | 1 | Topic and difficulty levels present in rendered prompt |
| `TestEvaluatePrompt` | 1 | Q&A content injected and present in rendered prompt |

## Test Results

```
======================== 28 passed, 4 warnings in 0.11s ========================
```

The 4 warnings are pytest collection warnings for `TestQuestion` and `TestResult` Pydantic models — pytest sees the `Test` prefix and attempts to collect them as test classes, but can't because they have `__init__` constructors. This is harmless.

## What's Not Covered by Automated Tests

| Module | Reason | How It's Verified |
|---|---|---|
| `session.py` | Requires LLM API calls | Manual smoke test with DeepSeek |
| `cli/repl.py` | Interactive terminal I/O | Manual run-through of command flow |
| `cli/renderer.py` | Visual terminal output | Visual inspection |
| `cli/wizard.py` | Interactive prompts | Visual inspection |
| `llm.py` | Requires API key | Manual test with valid credentials |

## Manual Smoke Test Procedure

1. Copy `.env.example` to `.env` and set `DEEPSEEK_API_KEY`
2. Run `tuzi`
3. Complete the configuration wizard (select depth, styles, tone, etc.)
4. Type `/plan python decorators`
5. Verify curriculum displays with prerequisites and main lessons
6. Type `/start 1.1`
7. Verify lesson content appears with markdown formatting
8. Ask a follow-up question: "can you show me a real example?"
9. Verify the LLM responds in context of the lesson
10. Type `/continue`
11. Verify the lesson continues naturally
12. Type `/test`
13. Answer all 3 test questions
14. Verify score and feedback display
15. Type `/status`
16. Verify profile config and progress are shown
17. Type `/exit`
18. Run `tuzi` again — verify profile is restored (state should be `ready` not prompting for `/config`)

## Adding New Tests

To add tests for a new prompt template:
1. Create a test class in `tests/test_prompts.py`
2. Call `render("template_name.j2", **vars)` with test variables
3. Assert expected strings appear in the output

To add tests for a new model:
1. Add test methods to `tests/test_models.py`
2. Create model instances with various inputs
3. Assert field values, defaults, and serialization

To add tests for a new database method:
1. Add test methods to `tests/test_database.py`
2. Use the `db` fixture for isolated SQLite
3. Call the method, assert the result matches expectations
