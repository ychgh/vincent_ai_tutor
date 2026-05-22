# Smart Learner: Your Personalized AI Tutor for OpenCode

Unlock personalized learning experiences with Smart Learner, a set of custom OpenCode agents that deliver tailored tutoring for users with diverse needs and interests.

## Table of Contents
- [Smart Learner: Your Personalized AI Tutor for OpenCode](#smart-learner-your-personalized-ai-tutor-for-opencode)
  - [Why Smart Learner?](#why-smart-learner)
  - [Requirements](#requirements)
  - [Quick Start Guide](#quick-start-guide)
  - [Available Agents](#available-agents)
  - [Personalization Options](#personalization-options)
  - [Commands](#commands)
  - [Usage Examples](#usage-examples)
  - [Guides](#guides)
  - [Different Languages](#different-languages)
  - [Screenshot Examples](#screenshot-examples)

## Why Smart Learner?

Smart Learner allows you to:

- Adjust the depth of knowledge to match your learning needs
- Customize your learning style, communication type, tone, and reasoning framework
- Create the ultimate AI tutor tailored just for you
- Generate comprehensive curricula for any topic
- Test your knowledge with adaptive difficulty assessments

## Requirements

- [OpenCode CLI](https://opencode.ai/) installed
- An AI provider configured (Anthropic Claude recommended, but works with any provider)

## Quick Start Guide

1. **Clone this repository** into your workspace:
   ```bash
   git clone https://github.com/ychgh/vincent_ai_tutor.git
   cd vincent_ai_tutor
   ```

2. **Start OpenCode** in the repository directory:
   ```bash
   opencode
   ```

3. **Switch to the Tutor agent** using the Tab key or type `@tutor`

4. **Configure your preferences** with `/config` or let the wizard help you:
   ```
   @tutor-wizard help me find my ideal learning configuration
   ```

5. **Create a lesson plan**:
   ```
   /plan quantum mechanics
   ```

6. **Start learning**:
   ```
   /start
   ```

## Available Agents

| Agent | Mode | Description |
|-------|------|-------------|
| **Smart Learner** (`tutor`) | Primary | Your main AI tutor - teaches topics, manages lessons, and tracks progress |
| **Configuration Wizard** (`tutor-wizard`) | Subagent | Helps discover your ideal learning preferences through a guided interview |
| **Curriculum Planner** (`curriculum-planner`) | Subagent | Creates comprehensive prerequisite and main curricula for any topic |
| **Test Creator** (`test-creator`) | Subagent | Generates practice tests with varying difficulty levels |

## Personalization Options

| Configuration | Options |
|--------------|---------|
| **Depth** | Elementary (Grade 1-6), Middle School (Grade 7-9), High School (Grade 10-12), Undergraduate, Graduate, Master's, Doctoral Candidate, Postdoc, Ph.D |
| **Learning Styles** | Visual, Verbal, Active, Intuitive, Reflective, Global |
| **Communication** | Formal, Textbook, Layman, Story Telling, Socratic |
| **Tone Styles** | Encouraging, Neutral, Informative, Friendly, Humorous |
| **Reasoning Frameworks** | Deductive, Inductive, Abductive, Analogical, Causal |
| **Language** | English (Default), or any language you prefer |

## Commands

The AI Tutor supports the following commands:

| Command | Description |
|---------|-------------|
| `/config` | View and update your learning configuration |
| `/plan [topic]` | Create a lesson plan for a topic |
| `/start [lesson]` | Start or continue a lesson |
| `/continue` | Continue to the next section |
| `/test` | Generate a practice test for the current topic |
| `/language [lang]` | Change the teaching language |
| `/example` | See how your configuration affects lessons |

## Usage Examples

### Creating a Lesson Plan
```
/plan I want to learn the photoelectric effect
```

### Starting a Specific Lesson
```
/start 1.3
```

### Configuring Preferences
```
/config Ph.D, Intuitive, Encouraging, Deductive
```
or describe yourself:
```
/config A high school student who learns best through storytelling
```

### Taking a Test
```
/test
```

## Guides

- [How to Use Smart Learner](Guides/How%20to%20use%20Smart%20Learner.md)
- [Configuration Guide](Guides/Config%20Guide.md)

## Different Languages

Smart Learner can teach in any language. Simply use:
```
/language Spanish
```
or
```
/language 日本語
```

The tutor will continue all lessons in your chosen language.

## Screenshot Examples

### Lesson Structure
When you start a lesson, Smart Learner will:
1. State the topic clearly
2. Provide engaging content at your level
3. Include relevant examples
4. Ask comprehension questions
5. Wait for your responses before continuing

### Test Structure
Tests include:
- **Example Problem**: Full solution walkthrough
- **Simple Problem** (3/10 difficulty): Basic concept application
- **Complex Familiar** (6/10 difficulty): Combining multiple concepts
- **Complex Unfamiliar** (9/10 difficulty): Creative problem-solving

---

## For Developers

This repository provides OpenCode agent configurations. The agents are defined in:

- `.opencode/agents/tutor.md` - Main tutor agent
- `.opencode/agents/tutor-wizard.md` - Configuration wizard
- `.opencode/agents/curriculum-planner.md` - Curriculum planning
- `.opencode/agents/test-creator.md` - Test generation
- `opencode.json` - Project configuration

Feel free to customize these agents for your specific educational needs!

---

**Original Project**: Based on [Mr. Ranedeer AI Tutor](https://github.com/JushBJJ/Mr.-Ranedeer-AI-Tutor) by JushBJJ, adapted for OpenCode.
