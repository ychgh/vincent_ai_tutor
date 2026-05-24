# Architecture

## Overview

Tuzi is a Python CLI application that implements the Mr. Ranedeer AI Tutor as a stateful, persistent system with an LLM backend. It transforms what was originally a set of static prompt files (a "pseudo-programming language" interpreted by an LLM) into a real application where Python manages state, persistence, and orchestration, while the LLM handles content generation only.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      CLI Layer (Rich)                     │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │  REPL    │  │  Renderer    │  │  Config Wizard    │  │
│  │ (repl.py)│  │ (renderer.py)│  │  (wizard.py)      │  │
│  └────┬─────┘  └──────┬───────┘  └────────┬──────────┘  │
│       │               │                   │              │
├───────┴───────────────┴───────────────────┴──────────────┤
│                   Session Layer                           │
│  ┌──────────────────────────────────────────────────┐    │
│  │              SessionManager (session.py)          │    │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  │    │
│  │  │ State      │  │ Command    │  │ Conversation│  │    │
│  │  │ Machine    │  │ Routing    │  │ History     │  │    │
│  │  └────────────┘  └────────────┘  └────────────┘  │    │
│  └──────────────────────┬───────────────────────────┘    │
│                         │                                │
├─────────────────────────┴────────────────────────────────┤
│                    Core Services                          │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │ LLM      │  │ Database     │  │ Template Loader   │  │
│  │ (llm.py) │  │ (database.py)│  │ (template_loader) │  │
│  └────┬─────┘  └──────┬───────┘  └────────┬──────────┘  │
│       │               │                   │              │
├───────┴───────────────┴───────────────────┴──────────────┤
│                   Data Layer                              │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │ Models   │  │ SQLite DB    │  │ Jinja2 Templates  │  │
│  │(models.py│  │ (~/.tuzi/    │  │ (prompts/*.j2)    │  │
│  │          │  │  tutor.db)   │  │                   │  │
│  └──────────┘  └──────────────┘  └───────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## Layer Responsibilities

### CLI Layer

The user-facing interface built with [Rich](https://github.com/Textualize/rich).

- **TutorREPL** (`cli/repl.py`): The read-eval-print loop. Reads user input via Rich's `Prompt`, routes slash commands and free-text to `SessionManager`, and displays results through the `Renderer`. Handles `KeyboardInterrupt` and `EOFError` gracefully.
- **Renderer** (`cli/renderer.py`): Converts structured data and markdown strings into formatted terminal output. Uses Rich components: `Markdown` for lesson content, `Syntax` (with Pygments) for code blocks, `Table` for curriculum display, `Panel` for banners and test results.
- **Config Wizard** (`cli/wizard.py`): An interactive, numbered-menu flow that collects all 7 configuration dimensions from the user. Pure Python — no LLM required.

### Session Layer

The central orchestration module.

- **SessionManager** (`session.py`): Implements a 7-state finite state machine, command routing via a dispatch table, conversation history management, and LLM orchestration. Each command handler validates the current state, delegates to LLM and database as needed, and returns a `CommandResult` with the new state and display content. Contains three LLM response parsers (`_parse_curriculum_response`, `_parse_test_response`, `_parse_evaluation`) that extract JSON from potentially messy LLM output using regex fallback chains.

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
    → render("system.j2", ...)            # Build system prompt with config
    → render("curriculum.j2", ...)        # Build curriculum request
    → LLMClient.chat([system, user])      # Send to DeepSeek
    → _parse_curriculum_response()        # Extract JSON, build Curriculum
    → db.save_curriculum()                # Persist to SQLite
    → _format_curriculum_display()        # Format as Rich markup
    → CommandResult(state=CURATED)

User: /start 1.1
  → SessionManager._handle_start()
    → render("system.j2", ...)
    → render("lesson.j2", ...)
    → LLMClient.chat([system, user])
    → Store in conversation_history
    → db.update_lesson_status("in_progress")
    → CommandResult(state=LESSON)

User: how does the @syntax work?
  → SessionManager.handle_command()       # No "/" prefix + LESSON state
    → _handle_question()
    → _build_messages()                   # Full history + new question
    → LLMClient.chat(messages)
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
