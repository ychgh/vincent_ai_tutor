# Implementation

## Project Structure

```
vincent_ai_tutor/
├── tuzi/                          # Python package
│   ├── __init__.py                # Package metadata, version 0.1.0
│   ├── __main__.py                # Entry point: wires dependencies, starts REPL
│   ├── models.py                  # 5 enums + 9 Pydantic models
│   ├── database.py                # SQLite CRUD (4 tables)
│   ├── config.py                  # AppConfig dataclass, .env loading
│   ├── llm.py                     # LiteLLM wrapper with error handling
│   ├── session.py                 # State machine, command routing, LLM orchestration
│   ├── template_loader.py         # Jinja2 environment singleton
│   ├── prompts/                   # Jinja2 templates
│   │   ├── system.j2              # Mr. Ranedeer system prompt
│   │   ├── curriculum.j2          # Curriculum generation request
│   │   ├── lesson.j2              # Lesson teaching request
│   │   ├── lesson_continue.j2     # Lesson continuation request
│   │   ├── test.j2                # Test question generation
│   │   ├── test_evaluate.j2       # Test answer evaluation
│   │   └── wizard.j2              # LLM-powered config wizard (opt-in)
│   ├── cli/
│   │   ├── __init__.py
│   │   ├── repl.py                # REPL loop
│   │   ├── renderer.py            # Rich output components
│   │   ├── stream.py              # Streaming LLM display
│   │   └── wizard.py              # Native config wizard
│   └── gradio_ui/
│       ├── __init__.py
│       ├── app.py                 # Gradio layout (4 tabs)
│       └── callbacks.py           # Streaming + sync event handlers
├── tests/
│   ├── __init__.py
│   ├── conftest.py                # Pytest fixtures (db, sample_profile)
│   ├── test_models.py             # Model validation, enums, serialization
│   ├── test_database.py           # CRUD operations, constraints
│   └── test_prompts.py            # Template rendering verification
├── docs/                          # Documentation
├── pyproject.toml                 # Project config, dependencies, entry points
├── .env.example                   # Environment variable template
└── .gitignore
```

## Module Details

### `tuzi/__main__.py` — Entry Point

The `main()` function is a Click command with a `--ui [cli|gradio]` option (default: `cli`). It wires all dependencies and starts the selected interface:

1. Loads `.env` via `python-dotenv`
2. Creates `AppConfig` from environment (db path, model name)
3. Initializes `Database` (creates tables if needed)
4. Initializes `LLMClient` (reads `LLM_MODEL` env var)
5. **CLI mode**: Initializes `Renderer`, creates `SessionManager(db, llm, renderer)`, runs `TutorREPL`
6. **Gradio mode**: Creates `SessionManager(db, llm)` (no renderer — streaming handled by Gradio callbacks), calls `run_gradio()`

### `tuzi/models.py` — Data Models

146 lines. All models use Pydantic's `BaseModel` for validation and serialization.

**Configuration Enums** (5 total, all `str, Enum`):
- `Depth`: 9 levels from Elementary to Ph.D
- `LearningStyle`: 6 options (Visual, Verbal, Active, Intuitive, Reflective, Global)
- `CommunicationStyle`: 5 options (Formal, Textbook, Layman, Story Telling, Socratic)
- `ToneStyle`: 5 options (Encouraging, Neutral, Informative, Friendly, Humorous)
- `ReasoningFramework`: 5 options (Deductive, Inductive, Abductive, Analogical, Causal)

**Domain Models** (6 total):
- `UserProfile`: Student configuration with all 7 dimensions + timestamps
- `Lesson`: A single curriculum node (id, title, description, status)
- `Curriculum`: Topic + prerequisite list + main curriculum list
- `Session`: Runtime state, curriculum reference, conversation history
- `Message`: Single conversation turn (role, content, timestamp)
- `TestQuestion`: Question with student answer and evaluation fields
- `TestResult`: Collection of questions with score

### `tuzi/database.py` — Persistence

290 lines. SQLite database with automatic schema creation.

**Tables**:
- `profiles` — 10 columns (1 row typical)
- `curricula` — 4 columns
- `lessons` — 6 columns, composite PK on `(curriculum_id, lesson_id)`
- `test_results` — 6 columns, stores questions as JSON

**Key methods**:
- `get_profile()` → `Optional[UserProfile]` — Returns most recent profile
- `save_profile(profile)` → `UserProfile` — INSERT or UPDATE based on `profile.id`
- `save_curriculum(curriculum)` → `Curriculum` — Inserts curriculum + all lessons in one transaction
- `get_curriculum(id)` → `Optional[Curriculum]` — Joins lessons, separates prereqs from main
- `get_curricula()` → `list[Curriculum]` — All curricula ordered by date DESC
- `update_lesson_status(curriculum_id, lesson_id, status)` — For marking progress
- `save_test_result(result)` → `TestResult` — Serializes questions to JSON
- `get_test_results(curriculum_id)` → `list[TestResult]` — Deserializes JSON

### `tuzi/llm.py` — LLM Integration

77 lines. LiteLLM wrapper providing provider-agnostic chat completion.

**`LLMClient`**:
- `__init__(model=None)`: Defaults to `deepseek-chat` from `LLM_MODEL` env var
- `chat(messages, max_tokens=4000, temperature=0.7)` → `str`
- `chat_stream(messages, ...)` → `Iterator[str]`

**Error handling**:
- `RateLimitError` → Clear "please wait" message
- `AuthenticationError` → "Check your API key" with model name
- `Empty response` → `LLMError("LLM returned empty response.")`
- All other exceptions → Wrapped in `LLMError` with original as cause

**`LLMError`**: Custom exception class for clean error propagation to the session layer.

### `tuzi/session.py` — State Machine and Command Routing

~500 lines. The central module that orchestrates all tutor behavior.

**`SessionManager`** fields:
- `db: Database` — Persistence
- `llm: LLMClient` — Content generation
- `renderer: Optional[Renderer]` — Rich renderer (CLI only; None in Gradio mode)
- `_lock: threading.Lock` — Ensures thread-safe state mutation
- `session: Session` — Current state + metadata
- `_profile: Optional[UserProfile]` — Loaded from DB on startup
- `_curriculum: Optional[Curriculum]` — Active curriculum
- `_test_questions: list[TestQuestion]` — Current test (if any)
- `_test_index: int` — Current question index

**Command Routing**:
`handle_command(raw: str)` acquires the lock, then dispatches based on:
1. Starts with `/` → `_dispatch(cmd, args)` → handler lookup in dict
2. State is `LESSON` → `_handle_question(raw)`
3. State is `TEST` → `_handle_test_answer(raw)`
4. Otherwise → "Type /help to see available commands"

**Streaming Support — Prepare/Finalize Pattern**:
To support streaming UIs (CLI Rich Live and Gradio generators), LLM-dependent commands are split into two phases:

- `prepare_plan(args)` → `(success, error, system_prompt, curriculum_prompt)` — Validates state, sets PLANNING, builds prompts. Does not call LLM.
- `finalize_plan(response, topic)` → `Optional[Curriculum]` — Parses JSON from the accumulated stream, saves to DB, sets CURATED.
- `prepare_start_lesson(args)` → `(success, error, system_prompt, lesson_prompt)` — Validates state, finds lesson, sets LESSON, clears history, builds prompts.
- `finalize_start_lesson(lesson_prompt, response)` — Appends user and assistant messages to conversation history.

`_handle_plan` and `_handle_start` use these internally. The Gradio UI calls them directly so it can drive the streaming loop between prepare and finalize.

**Thread Safety**:
All public methods that mutate state (`handle_command`, `prepare_*`, `finalize_*`) acquire `self._lock` before delegating to `_*_locked` internal methods.

**LLM Response Parsers** (3 methods):

1. `_parse_curriculum_response(response, topic)` → `Curriculum`
   - Regex extract from ` ```json ``` ` code fences
   - Regex extract from `{...}` braces
   - `json.loads()` then iterate `prerequisites` and `main_curriculum` arrays
   - Falls back to assigning auto-IDs if LLM omits them

2. `_parse_test_response(response)` → `list[TestQuestion]`
   - Same regex fallback chain
   - Handles both array `[...]` and object `{...}` (wraps as single-element array)
   - Returns empty list on parse failure

3. `_parse_evaluation(response)` → `list[tuple[str, str]]`
   - Same regex fallback chain
   - Extracts `correct_answer` and `feedback` per question
   - Used to populate `TestQuestion` fields after evaluation

**Conversation Management**:
- `_build_messages(user_content)` → `list[dict]`: Converts `Message` history to LiteLLM format, appends new user message, stores in history
- History grows during a lesson; resets when a new lesson starts

### `tuzi/cli/repl.py` — REPL Loop

76 lines. The interactive read-eval-print loop.

**`TutorREPL.run()`**:
1. Shows banner via `Renderer.show_banner()`
2. Checks for existing profile; prompts `/config` if none
3. Enters loop:
   - Builds context-aware prompt string (shows state and topic)
   - Reads input via `Prompt.ask()`
   - Routes to `SessionManager.handle_command()`
   - Intercepts `__EXIT__` and `__HELP__` sentinels
   - Displays result via `Renderer.display_markdown()`

**Prompt string varies by state**:
- `lesson >` (green) during LESSON
- `test >` (yellow) during TEST
- `config >` (magenta) during WIZARD
- `tuzi [topic] >` (blue) otherwise

### `tuzi/cli/renderer.py` — Output

155 lines. Wraps Rich components for consistent terminal output.

**Key methods**:
- `show_banner()`: ASCII art banner in blue panel
- `show_help(state)`: Command list with state context
- `display_markdown(content)`: Lesson content, test feedback
- `display_code(code, language)`: Syntax-highlighted with line numbers
- `display_config(profile)`: Configuration table
- `display_curriculum(curriculum)`: Table with status icons (○ → ✓)
- `display_test_result(result)`: Score (color-coded) + per-question feedback
- `confirm_action(message)` → `bool`
- `select_option(options, prompt)` → `str` (numbered menu)

### `tuzi/cli/wizard.py` — Configuration Wizard

129 lines. Interactive numbered-menu flow.

**Flow** (8 steps):
1. Name — free text input
2. Depth — 9 options, numbered menu
3. Learning Style — 6 options, numbered menu
4. Communication Style — 5 options, numbered menu
5. Tone Style — 5 options, numbered menu
6. Reasoning Framework — 5 options, numbered menu
7. Emojis — yes/no confirm
8. Language — free text input (default "English")

Uses `_menu_select()` helper that shows numbered options, marks the default, and validates input is within range. Uses `_find_index()` to pre-select the current value when reconfiguring.

### `tuzi/gradio_ui/` — Gradio Web UI

Two files providing an alternative web-based interface.

**`gradio_ui/app.py`** — `run_gradio(session_mgr, db, llm)` builds the `gr.Blocks` layout:

- **Chat tab**: `gr.Chatbot` + `gr.Textbox` + Send/Clear buttons + state indicator
- **Curriculum tab**: `gr.HTML` showing the active curriculum as a styled HTML table
- **Settings tab**: Form with dropdowns for all 7 `UserProfile` dimensions + Save button
- **Status tab**: `gr.HTML` showing profile, state, topic, and progress + Refresh button
- `demo.queue(default_concurrency_limit=1)` ensures serial callback execution
- Launches on `http://127.0.0.1:7860`

**`gradio_ui/callbacks.py`** — Event handler classes:

`ChatCallbacks`:
- `handle_message(message, history, ui_state)` — Generator-based callback. Routes to streaming handlers for `/plan` and `/start`, sync handler for all other commands.
- `_handle_start_streaming()` — Calls `session_mgr.prepare_start_lesson()`, loops over `llm.chat_stream()`, yields `(chatbot, curriculum_html, status, ui_state)` on each token, then calls `session_mgr.finalize_start_lesson()`.
- `_handle_plan_streaming()` — Calls `session_mgr.prepare_plan()`, streams tokens, calls `session_mgr.finalize_plan()`, updates curriculum HTML.
- `_handle_sync()` — Calls `session_mgr.handle_command()` for `/continue`, `/test`, `/status`, free-text questions. Strips Rich markup from displayed text.
- `/config` redirects to the Settings tab. `/help` displays a markdown command reference. `/exit` ends the session.

`SettingsCallbacks`:
- `save_profile()` — Builds `UserProfile` from form values, saves via `db.save_profile()`, updates `session_mgr` state.
- `load_profile()` — Returns current profile values to populate the form on startup.

### `tuzi/prompts/` — Jinja2 Templates

7 templates total.

**`system.j2`** (39 lines): The base system prompt sent with every LLM call. Encodes:
- Mr. Ranedeer persona (friendly reindeer)
- All 6 configuration dimensions injected as variables
- 12 teaching guidelines derived from the configuration
- Output formatting rules (markdown, code fences, tables)

**`curriculum.j2`** (39 lines): Requests a JSON curriculum with prerequisites (2-4 items, ids 0.x) and main curriculum (6-10 lessons, ids 1.x). Includes example JSON format to guide the LLM.

**`lesson.j2`** (20 lines): Requests a structured lesson with 5 sections: Introduction, Core Concepts, Practical Examples, Check Understanding, Summary. Template variables: `topic`, `lesson_id`, `lesson_title`, `lesson_description`.

**`lesson_continue.j2`** (7 lines): Minimal prompt asking the LLM to continue from conversation context. Relies entirely on the accumulated history.

**`test.j2`** (36 lines): Requests 3 questions at increasing difficulty (simple familiar 3/10, complex familiar 6/10, complex unfamiliar 9/10) with JSON output format.

**`test_evaluate.j2`** (22 lines): Provides student answers and requests evaluation with correct answers and constructive feedback in JSON.

**`wizard.j2`** (29 lines): LLM-powered configuration interview persona (wizard-themed). Not used by default — the native `cli/wizard.py` is preferred.

## Dependency Details

| Package | Version | Purpose |
|---|---|---|
| `litellm` | ≥1.40.0 | Multi-provider LLM access (DeepSeek, OpenAI, Anthropic) |
| `rich` | ≥13.0.0 | Terminal UI: markdown, syntax highlighting, tables, panels |
| `jinja2` | ≥3.1.0 | Prompt template rendering with variable substitution |
| `pydantic` | ≥2.0.0 | Data models with validation and JSON serialization |
| `python-dotenv` | ≥1.0.0 | Loading `.env` file for API keys |
| `click` | ≥8.0.0 | CLI entry point framework |
| `pytest` (dev) | ≥8.0.0 | Test framework |
| `gradio` (optional) | ≥4.0.0 | Web UI (use `tuzi --ui gradio`) |
