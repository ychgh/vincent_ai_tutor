# Architecture

## Overview

Tuzi is a Python application that implements the Mr. Ranedeer AI Tutor as a stateful, persistent system with an LLM backend. It transforms what was originally a set of static prompt files (a "pseudo-programming language" interpreted by an LLM) into a real application where Python manages state, persistence, and orchestration, while the LLM handles content generation only. Tuzi supports two interfaces: a CLI (via Rich) and a web UI (via Gradio), selectable with the `--ui` flag.

## High-Level Architecture

```
┌───────────────────────────────────────────────────────────────┐
│                     UI Layer (CLI + Web)                       │
│  ┌──────────┐  ┌──────────────┐  ┌─────────────────────────┐ │
│  │  REPL    │  │  Renderer    │  │  Config Wizard          │ │
│  │ (repl.py)│  │ (renderer.py)│  │  (wizard.py)            │ │
│  └────┬─────┘  └──────┬───────┘  └────────┬────────────────┘ │
│       │               │                   │                   │
│  ┌────┴───────────────┴───────────────────┴────────────────┐  │
│  │              Gradio Web UI (gradio_ui/)                  │  │
│  │  ┌──────────┐  ┌──────────────┐  ┌───────────────────┐  │  │
│  │  │  Chat    │  │  Callbacks   │  │  Settings Form    │  │  │
│  │  │  Tab     │  │(callbacks.py)│  │                   │  │  │
│  │  └──────────┘  └──────────────┘  └───────────────────┘  │  │
│  └──────────────────────┬───────────────────────────────────┘  │
│                         │                                      │
├─────────────────────────┴──────────────────────────────────────┤
│                      Session Layer                             │
│  ┌───────────────────────────────────────────────────────┐    │
│  │              SessionManager (session.py)               │    │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────────┐   │    │
│  │  │ State      │  │ Command    │  │ Conversation   │   │    │
│  │  │ Machine    │  │ Routing    │  │ History         │   │    │
│  │  └────────────┘  └────────────┘  └────────────────┘   │    │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────────┐   │    │
│  │  │ Prepare/   │  │ Threading  │  │ Streaming      │   │    │
│  │  │ Finalize   │  │ Lock       │  │ Orchestration  │   │    │
│  │  └────────────┘  └────────────┘  └────────────────┘   │    │
│  └──────────────────────┬────────────────────────────────┘    │
│                         │                                      │
├─────────────────────────┴──────────────────────────────────────┤
│                      Core Services                             │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────────┐       │
│  │ LLM      │  │ Database     │  │ Template Loader   │       │
│  │ (llm.py) │  │ (database.py)│  │ (template_loader) │       │
│  └────┬─────┘  └──────┬───────┘  └────────┬──────────┘       │
│       │               │                   │                   │
├───────┴───────────────┴───────────────────┴───────────────────┤
│                      Data Layer                               │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────────┐       │
│  │ Models   │  │ SQLite DB    │  │ Jinja2 Templates  │       │
│  │(models.py│  │ (~/.tuzi/    │  │ (prompts/*.j2)    │       │
│  │          │  │  tutor.db)   │  │                   │       │
│  └──────────┘  └──────────────┘  └───────────────────┘       │
└───────────────────────────────────────────────────────────────┘
```

## Layer Responsibilities

### UI Layer

Tuzi provides two user interfaces, selectable via `tuzi --ui [cli|gradio]`.

**CLI** (default) — built with [Rich](https://github.com/Textualize/rich):

- **TutorREPL** (`cli/repl.py`): The read-eval-print loop. Reads user input via Rich's `Prompt`, routes slash commands and free-text to `SessionManager`, and displays results through the `Renderer`. Handles `KeyboardInterrupt` and `EOFError` gracefully. Detects `CommandResult.curriculum` to use the structured `display_curriculum()` table renderer.
- **Renderer** (`cli/renderer.py`): Converts structured data and markdown strings into formatted terminal output. Uses Rich components: `Markdown` for lesson content, `Syntax` (with Pygments) for code blocks, `Table` for curriculum display, `Panel` for banners and test results.
- **Config Wizard** (`cli/wizard.py`): An interactive, numbered-menu flow that collects all 7 configuration dimensions from the user. Pure Python — no LLM required.
- **Streaming** (`cli/stream.py`): Uses Rich's `Live` display to render LLM tokens as they arrive for `/plan` and `/start`, giving immediate feedback instead of waiting for the full response.

**Gradio Web UI** — built with [Gradio](https://gradio.app):

- **Chat Tab** (`gradio_ui/app.py`, `gradio_ui/callbacks.py`): A `gr.Chatbot` with streaming support. The callback is a Python generator that calls `SessionManager`'s `prepare_*` methods, streams tokens via `LLMClient.chat_stream()`, and calls `finalize_*` methods to update state. Rich markup is stripped for plain-text display.
- **Curriculum Tab**: Displays the active curriculum as an HTML table with lesson IDs, titles, descriptions, and status icons. Updated automatically after `/plan` succeeds.
- **Settings Tab**: A form with dropdowns for all 7 configuration dimensions. Replaces the CLI wizard. Calls `db.save_profile()` directly.
- **Status Tab**: Shows current profile, state, topic, and lesson progress. Refreshable.

### Session Layer

The central orchestration module shared by both UIs.

- **SessionManager** (`session.py`): Implements a 7-state finite state machine, command routing via a dispatch table, conversation history management, and LLM orchestration. Each command handler validates the current state, delegates to LLM and database as needed, and returns a `CommandResult(content, state, is_error, curriculum)` with the new state and display content. Contains three LLM response parsers (`_parse_curriculum_response`, `_parse_test_response`, `_parse_evaluation`) that extract JSON from potentially messy LLM output using regex fallback chains.
- **Prepare/Finalize pattern**: To support streaming UIs, the session layer exposes four public helper methods that split LLM-dependent commands into "prepare" (validate + build prompts) and "finalize" (parse response + update state) phases: `prepare_plan()`, `finalize_plan()`, `prepare_start_lesson()`, `finalize_start_lesson()`. The UI layer handles streaming between these two phases.
- **Thread safety**: All public methods that mutate state acquire a `threading.Lock`, ensuring safe concurrent access from Gradio's thread pool.

### Core Services

- **LLMClient** (`llm.py`): Wraps LiteLLM for provider-agnostic chat completion. Supports both `chat()` (synchronous) and `chat_stream()` (streaming iterator). Handles rate limiting, authentication errors, and empty responses with typed `LLMError` exceptions.
- **Database** (`database.py`): SQLite persistence with four tables (`profiles`, `curricula`, `lessons`, `test_results`). Uses `row_factory = sqlite3.Row` for dict-like row access. Methods follow a simple CRUD pattern: `get_*`, `save_*`, `update_*`.
- **Template Loader** (`template_loader.py`): Jinja2 environment singleton with `StrictUndefined` (fails fast on missing variables) and `trim_blocks`/`lstrip_blocks` for clean output.

### Data Layer

- **Models** (`models.py`): 5 string enums for configuration dimensions + 9 Pydantic BaseModel classes. Pydantic provides validation, serialization (`model_dump()`), and JSON round-tripping.
- **SQLite**: Stored at `~/.tuzi/tutor.db` (configurable via `TUZI_DATA_DIR`).
- **Templates** (`prompts/*.j2`): 7 Jinja2 templates encoding the Mr. Ranedeer teaching personality and task-specific prompts.

## Data Flow

### Lesson Flow (most complex path)

```
User: /plan python decorators
  → SessionManager._handle_plan()
    → _prepare_plan_locked()              # Validate state, build prompts
    → LLMClient.chat_stream([system, user])  # Stream tokens to UI
    → stream_markdown(chunks)             # CLI: Rich Live display
       (or Gradio: yield to Chatbot)
    → _finalize_plan_locked()             # Parse JSON, save to DB
    → Curriculum table rendered via       # CLI: Rich Table
      Renderer.display_curriculum()       # Gradio: HTML table in tab
    → CommandResult(state=CURATED, curriculum=...)

User: /start 1.1
  → SessionManager._handle_start()
    → _prepare_start_lesson_locked()      # Validate, build prompts, set state
    → LLMClient.chat_stream([system, user])  # Stream tokens
    → stream_markdown(chunks)             # Token-by-token display
    → finalize_start_lesson()             # Store in conversation_history
    → CommandResult(state=LESSON)

User: how does the @syntax work?
  → SessionManager.handle_command()       # No "/" prefix + LESSON state
    → _handle_question()
    → _build_messages()                   # Full history + new question
    → LLMClient.chat(messages)            # Synchronous (non-streaming)
    → Append to conversation_history
    → CommandResult(state=LESSON)

User: /test
  → SessionManager._handle_test()
    → render("test.j2", ...)
    → LLMClient.chat()
    → _parse_test_response()              # Extract questions
    → Display question 1
    → CommandResult(state=TEST)

User: <answer to Q1>
  → _handle_test_answer()
    → Store answer in _test_questions[0]
    → Display question 2...

User: <answer to Q3>
  → _evaluate_test()
    → render("test_evaluate.j2", ...)
    → LLMClient.chat()
    → _parse_evaluation()
    → db.save_test_result()
    → CommandResult(state=CURATED)
```

## Key Architectural Decisions

1. **Python is the program, not the prompt.** The original Mr. Ranedeer uses the LLM as an interpreter for a custom pseudo-language with `[BEGIN]...[END]` blocks and `execute <Function>` calls. Tuzi discards this entirely. Python manages the state machine, command routing, and data flow. Prompts only guide content generation.

2. **Provider-agnostic LLM access via LiteLLM.** One env var (`LLM_MODEL`) switches between DeepSeek, OpenAI, Anthropic, and others. The application code never references a specific provider.

3. **No LangChain/LangGraph.** The 7-state FSM is simple enough for a hand-rolled state machine in `session.py`. LangGraph would add dependency weight without proportional benefit for this PoC.

4. **Jinja2 over LangChain templates.** Jinja2 is a well-known, zero-abstraction template engine. LangChain's `ChatPromptTemplate` adds an abstraction layer that isn't needed when prompts are static templates with variable substitution.

5. **LLM responses parsed as JSON with regex fallback.** Modern LLMs reliably produce JSON when asked, but the parser defends against code fences, extra text, and malformed output with a fallback chain: try direct `json.loads()` → try extracting from ` ```json ``` ` fences → try extracting from `{...}` braces.

6. **Conversation history grows with the lesson.** Each lesson starts with a clean `conversation_history` containing just the system prompt. As the student asks questions, user/assistant messages accumulate, providing full context for the LLM.

7. **Dual UI with shared session layer.** The CLI and Gradio UIs share the same `SessionManager`, `LLMClient`, `Database`, and templates. The `--ui` switch selects the entry point. The prepare/finalize pattern lets both UIs stream LLM output: the CLI uses Rich's `Live` display, and Gradio uses generator-based callbacks that yield into `gr.Chatbot`. When Gradio is active, Rich markup tags are stripped from displayed text since they have no meaning in HTML.

8. **Streaming for long-generation commands.** `/plan` and `/start` stream LLM tokens as they arrive rather than waiting for the full response. This is implemented by splitting each handler into prepare (validation + prompt construction) and finalize (parsing + state update) phases, with the UI layer driving the streaming loop between them.
