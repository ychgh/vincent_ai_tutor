# User Guide

## Installation

### Prerequisites
- Python 3.9 or later
- A DeepSeek API key ([platform.deepseek.com](https://platform.deepseek.com))

### Setup

```bash
# Clone the repository
git clone https://github.com/ychgh/vincent_ai_tutor.git
cd vincent_ai_tutor

# Install the package
pip install -e .

# Configure your API key
cp .env.example .env
# Edit .env and set your DEEPSEEK_API_KEY
```

### Switching LLM Providers

Tuzi uses LiteLLM, which supports many providers. Edit `.env`:

```env
# For OpenAI
LLM_MODEL=gpt-4o
OPENAI_API_KEY=sk-...

# For Anthropic
LLM_MODEL=claude-sonnet-4-20250514
ANTHROPIC_API_KEY=sk-ant-...

# For DeepSeek (default)
LLM_MODEL=deepseek-chat
DEEPSEEK_API_KEY=sk-...
```

## Quick Start

Tuzi supports two interfaces. Use the `--ui` flag to choose:

```bash
tuzi --ui cli      # CLI mode (default)
tuzi --ui gradio   # Web UI at http://127.0.0.1:7860
```

### CLI Mode

```bash
tuzi
```

On first launch, you'll be prompted to configure your profile:

```
╔══════════════════════════════════════╗
║   🦌  Mr. Ranedeer AI Tutor  🦌     ║
║         Tuzi CLI v0.1.0              ║
╚══════════════════════════════════════╝

No profile found! Type /config to set up your learning preferences.
tuzi > /config
```

## Configuration Wizard

The wizard walks you through 8 steps:

1. **Name** — What should the tutor call you?
2. **Depth** — How deep should lessons go? (Elementary through Ph.D)
3. **Learning Style** — How do you learn best? (Visual, Verbal, Active, Intuitive, Reflective, Global)
4. **Communication Style** — How should the tutor explain things? (Formal, Textbook, Layman, Story Telling, Socratic)
5. **Tone** — What tone should the tutor use? (Encouraging, Neutral, Informative, Friendly, Humorous)
6. **Reasoning Framework** — How should the tutor build understanding? (Deductive, Inductive, Abductive, Analogical, Causal)
7. **Emojis** — Use emojis in lessons?
8. **Language** — What language should lessons be in?

You can reconfigure at any time by running `/config` again.

### Gradio Web UI

Launch the web interface:

```bash
tuzi --ui gradio
```

This opens a browser at `http://127.0.0.1:7860` with four tabs:

- **Chat** — The main interface. Type commands (`/plan`, `/start`, etc.) and questions just like the CLI. LLM responses for `/plan` and `/start` stream token-by-token.
- **Curriculum** — Shows the active study plan as a formatted table with lesson IDs, titles, descriptions, and status.
- **Settings** — Configure your learning profile via dropdown menus instead of the terminal wizard.
- **Status** — View your current profile, session state, topic, and lesson progress.

To install with Gradio support:

```bash
pip install -e ".[gradio]"
```

## Commands

Commands work the same in both CLI and Gradio. In Gradio, type them in the Chat tab's text input.

### `/help`
Show available commands and the current state.

### `/help`
Show available commands and the current state.

### `/plan <topic>`
Generate a detailed study plan for a topic. The response streams token-by-token so you can see progress immediately. The tutor creates:
- **Prerequisites** (2-4 lessons): Foundational concepts you should know first
- **Main Curriculum** (6-10 lessons): Progressive lessons from fundamentals to advanced

Example:
```
tuzi > /plan python decorators
```

The plan is displayed as a formatted table (CLI: Rich table, Gradio: HTML table in the Curriculum tab) and saved for future sessions.

### `/start [lesson_id]`
Begin a lesson. The response streams token-by-token so you can start reading immediately instead of waiting for the full response. You can specify a lesson ID or omit it to start the first pending lesson.

```
tuzi [python decorators] > /start 1.1
```

If you omit the ID, the tutor automatically picks the first uncompleted lesson.

### `/continue`
Continue the current lesson where you left off. The tutor remembers the full conversation context.

```
lesson > /continue
```

### Asking Questions
During a lesson, just type your question. Any input that doesn't start with `/` is treated as a question for the tutor.

```
lesson > can you explain the difference between @staticmethod and @classmethod?
lesson > show me a real-world example of a decorator with arguments
```

### `/test`
Take a test on the current topic. The tutor generates 3 questions:
1. **Simple Familiar** (3/10 difficulty) — Basic recall
2. **Complex Familiar** (6/10 difficulty) — Apply concepts in a familiar context
3. **Complex Unfamiliar** (9/10 difficulty) — Apply concepts to a new scenario

Answer each question in the prompt. After all answers are submitted, the tutor evaluates them and provides:
- Correct/model answers for each question
- Constructive feedback on your answers
- An overall score

Test results are saved and can be reviewed later.

### `/status`
View your current profile configuration, state, topic, and lesson progress.

```
tuzi [python decorators] > /status
Profile
🎯 Depth: High School (Grade 10-12)
🧠 Learning Style: Active
🗣️ Communication: Socratic
🌟 Tone: Encouraging
🔎 Reasoning: Causal
😀 Emojis: Enabled
🌐 Language: English

State: curated
Topic: python decorators
Progress: 0/5 lessons completed
```

### `/config`
Re-run the configuration wizard to change your learning preferences.

### `/exit`
Exit the tutor. Your profile and progress are saved automatically.

```
tuzi > /exit
Saving and exiting. Goodbye! 👋
```

## Example Session

```
$ tuzi

╔══════════════════════════════════════╗
║   🦌  Mr. Ranedeer AI Tutor  🦌     ║
║         Tuzi CLI v0.1.0              ║
╚══════════════════════════════════════╝

Profile loaded. Type /help to see commands. State: ready

tuzi > /plan python decorators

📚 Curriculum: python decorators (8 lessons)

Prerequisites
  0.1 — Basic Python: Variables, functions, and control flow.
  0.2 — Functions as Objects: Understanding first-class functions in Python.

Main Curriculum
  1.1 — Introduction to Decorators: What decorators are and why we use them.
  1.2 — Writing Simple Decorators: Creating your first decorator function.
  1.3 — Decorators with Arguments: Implementing parametrized decorators.
  1.4 — Built-in Decorators: @staticmethod, @classmethod, @property.
  1.5 — Stacking Decorators: Applying multiple decorators and understanding order.
  1.6 — Practical Applications: Logging, timing, access control, caching.

Type /start <id> to begin a lesson (e.g., /start 1.1)

tuzi [python decorators] > /start 1.1

# Introduction to Decorators

Welcome! Today we're going to explore one of Python's most elegant features...

[... lesson content with markdown formatting, code examples, and explanations ...]

─── Type /continue for more, or ask a question ───

lesson > can you show me a timing decorator?

Great question! Here's a practical timing decorator...

```python
import time
from functools import wraps

def timing_decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()
        print(f"{func.__name__} took {end - start:.4f} seconds")
        return result
    return wrapper

@timing_decorator
def slow_function():
    time.sleep(1)
    return "Done!"
```

─── Type /continue for more, or ask another question ───

lesson > /test

📝 Test on python decorators — 3 questions

Question 1 (simple familiar)
What is a Python decorator and what problem does it solve?

[dim]Type your answer and press Enter.[/dim]

test > A decorator is a function that wraps another function to add behavior without modifying the source code.

Question 2 (complex familiar)
Write a decorator that logs the arguments and return value of a function.

[dim]Type your answer and press Enter.[/dim]

test > [student writes code...]

Question 3 (complex unfamiliar)
How would you design a decorator-based rate limiting system for an API?

[dim]Type your answer and press Enter.[/dim]

test > [student explains approach...]

[... evaluation with feedback and score ...]

Score: 83% (2.5/3)

tuzi [python decorators] > /status
Profile
🎯 Depth: High School (Grade 10-12)
...

State: curated
Topic: python decorators
Progress: 1/8 lessons completed

tuzi [python decorators] > /exit
Saving and exiting. Goodbye! 👋
```

## Tips

- **Be specific with topics**: `/plan "quantum mechanics"` works better than `/plan physics`
- **Ask follow-ups freely**: During a lesson, every question is answered in context
- **Use `/test` to check understanding**: Tests help identify gaps before moving to the next lesson
- **Reconfigure anytime**: `/config` won't lose your curriculum progress
- **DeepSeek is fast and affordable**: The default model works well for educational content

## Troubleshooting

| Problem | Solution |
|---|---|
| "No API key found" | Check your `.env` file has `DEEPSEEK_API_KEY` set correctly |
| "Rate limited" | Wait a minute and try again |
| "Failed to generate curriculum" | Try a more specific topic, or check your internet connection |
| Commands not recognized | Make sure you're using the `/` prefix (e.g., `/plan`, not `plan`) |
| Lesson seems stuck | Type `/continue` to prompt the tutor to move forward |
| "All lessons completed" | Type `/plan <new topic>` to start a new subject |

## Data Storage

All your data is stored locally in `~/.tuzi/`:
- `tutor.db` — SQLite database with your profile, curricula, lesson progress, and test results
- Set `TUZI_DATA_DIR` env var to change the location

To reset everything, delete `~/.tuzi/tutor.db`:

```bash
rm ~/.tuzi/tutor.db
```
