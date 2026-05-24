# Design

## Design Philosophy

Tuzi translates a prompt-only AI tutor system into a stateful Python application. The core insight is separating concerns: **Python owns the what and when** (state, routing, persistence), while the **LLM owns the how** (what to teach, in what style, with what examples).

## State Machine

The tutor's behavior is governed by a 7-state finite state machine. Each state determines which commands are valid and how free-text input is interpreted.

```
                    ┌─────────────┐
                    │UNINITIALIZED │
                    └──────┬──────┘
                           │ /config
                           ▼
                    ┌─────────────┐
                    │   WIZARD    │
                    └──────┬──────┘
                           │ wizard completes
                           ▼
                    ┌─────────────┐
              ┌─────│    READY    │◄──────────────┐
              │     └──────┬──────┘               │
              │            │ /plan <topic>        │
              │            ▼                      │
              │     ┌─────────────┐              │
              │     │  PLANNING   │               │
              │     └──────┬──────┘              │
              │            │ curriculum ready     │
              │            ▼                      │
              │     ┌─────────────┐              │
              │     │   CURATED   │◄──────┐      │
              │     └──┬──────┬───┘       │      │
              │        │      │           │      │
              │  /start│      │/test      │      │
              │        ▼      ▼           │      │
              │  ┌──────────┐ ┌─────────┐ │      │
              │  │  LESSON  │ │  TEST   │ │      │
              │  └────┬─────┘ └────┬────┘ │      │
              │       │            │      │      │
              │       └────────────┘──────┘      │
              │         /test (from LESSON)       │
              │         test complete             │
              │                                  │
              └──────────────────────────────────┘
                      /config (from any state)
```

### State Definitions

| State | Meaning | Allowed Commands |
|---|---|---|
| `UNINITIALIZED` | No user profile exists | `/config`, `/help`, `/exit` |
| `WIZARD` | Configuration wizard active | Wizard prompts (numbered choices) |
| `READY` | Profile exists, no active curriculum | `/plan`, `/config`, `/status`, `/help`, `/exit` |
| `PLANNING` | LLM generating a curriculum | (none — transitions automatically) |
| `CURATED` | Curriculum ready, lessons available | `/start`, `/test`, `/plan`, `/config`, `/status`, `/help`, `/exit` |
| `LESSON` | Active teaching session | `/continue`, `/test`, free-text questions |
| `TEST` | Taking a test | Free-text answers (submitted per question) |

### State Transitions

- `/config` is valid from **any** state — it runs the wizard and transitions to `READY`
- `/plan` transitions through `PLANNING` → `CURATED` automatically
- During `LESSON`, non-command input is treated as a student question
- During `TEST`, non-command input is treated as an answer to the current question
- `/exit` sends a sentinel (`__EXIT__`) that the REPL loop handles

## Configuration Dimensions

Inherited from the original Mr. Ranedeer prompt system, the tutor supports 6 configurable dimensions:

### Depth (9 levels)
Controls the complexity and depth of explanations.

| Level | Typical Audience |
|---|---|
| Elementary (Grade 1-6) | Young children |
| Middle School (Grade 7-9) | Pre-teens |
| High School (Grade 10-12) | Teenagers |
| Undergraduate | College beginners |
| Graduate (Bachelor Degree) | College seniors |
| Master's | Graduate students |
| Doctoral Candidate (Ph.D Candidate) | PhD students |
| Postdoc | Early-career researchers |
| Ph.D | Expert researchers |

### Learning Style (6 options)
How content is presented to match the student's learning preference.

- **Visual**: Charts, diagrams, mind maps
- **Verbal**: Text-heavy explanations, reading
- **Active**: Hands-on exercises, coding along
- **Intuitive**: Big-picture first, theory before practice
- **Reflective**: Time to think, review, and revisit
- **Global**: Overview first, then drill into details

### Communication Style (5 options)
The rhetorical approach used in explanations.

- **Formal**: Professional, precise language
- **Textbook**: Structured like academic material
- **Layman**: Simple terms, everyday analogies
- **Story Telling**: Narrative-driven explanations
- **Socratic**: Learning through guided questions

### Tone Style (5 options)
The emotional register of the tutor's voice.

- **Encouraging**: Positive reinforcement, celebrating progress
- **Neutral**: Objective, fact-focused
- **Informative**: Detail-oriented, comprehensive
- **Friendly**: Warm, conversational
- **Humorous**: Light-hearted, jokes and fun examples

### Reasoning Framework (5 options)
The logical structure used to build understanding.

- **Deductive**: From general principles to specific cases
- **Inductive**: From specific examples to general rules
- **Abductive**: From observations to best explanations
- **Analogical**: Learning through comparison and metaphor
- **Causal**: Understanding through cause and effect

### Language
Any language the LLM supports. Default: English.

## Command Design

### Slash Commands

Commands use the `/command [args]` pattern, inspired by the original Mr. Ranedeer prompt commands. The `/` prefix provides a clear distinction between commands and free-text questions during a lesson.

### CommandResult Pattern

Every command handler returns a `CommandResult` dataclass:

```python
@dataclass
class CommandResult:
    content: str          # Display content (or sentinel)
    state: SessionState   # New state after command
    is_error: bool        # Whether this is an error result
```

Sentinels (`__EXIT__`, `__HELP__`) are special content strings the REPL loop intercepts before display. This avoids coupling the session layer to the I/O layer.

### Error Handling Strategy

| Scenario | Handling |
|---|---|
| Invalid state for command | `CommandResult` with `is_error=True` and helpful message |
| LLM API failure | Caught by `LLMError`, surface to user, revert state |
| LLM JSON parse failure | Regex fallback chain; if all fail, return empty result |
| KeyboardInterrupt | Graceful message, no state change |
| Missing arguments | Usage hint in error response |

## Conversation History

During a `LESSON` session, all messages (system prompt, user questions, assistant responses) accumulate in `Session.conversation_history`. This provides the LLM with full context for follow-up questions and `/continue`.

- **New lesson**: History resets to just the system prompt
- **`/continue`**: Sends full history with "Continue the lesson..." appended
- **Free-text questions**: Appended to history with the LLM response

## Database Schema

Four tables in a single SQLite file:

```
profiles        curricula       lessons           test_results
─────────       ──────────      ──────────        ────────────
id (PK)         id (PK)         curriculum_id(FK) id (PK)
name            topic           lesson_id          curriculum_id (FK)
depth           depth           title              topic
learning_style  created_at      description        questions (JSON)
communication_                  status             score
tone_style                      is_prerequisite    completed_at
reasoning_framework
emojis_enabled
language
created_at
updated_at
```

Design notes:
- **Single profile**: `get_profile()` returns the most recent row. The system is designed for one user per machine.
- **Lessons as rows**: Each lesson is a row keyed by `(curriculum_id, lesson_id)`. This allows querying progress per curriculum.
- **Test questions as JSON**: Stored as a JSON blob in the `questions` column. Simpler than a separate questions table for this scale.
- **ISO format timestamps**: Stored as text for SQLite compatibility and human readability.
