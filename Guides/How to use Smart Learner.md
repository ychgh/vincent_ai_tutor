# How to use Smart Learner

**Table of Contents**

- [How to use Smart Learner](#how-to-use-smart-learner)
  - [Getting Started](#getting-started)
  - [Create a new lesson plan](#create-a-new-lesson-plan)
  - [Starting the lesson plan](#starting-the-lesson-plan)
  - [Continuing the lesson](#continuing-the-lesson)
  - [Asking a question](#asking-a-question)
  - [Testing yourself](#testing-yourself)
  - [Changing Language](#changing-language)
  - [Using the Configuration Wizard](#using-the-configuration-wizard)
- [Troubleshooting](#troubleshooting)

## Getting Started

1. **Install OpenCode** if you haven't already: [opencode.ai](https://opencode.ai/)

2. **Clone the repository**:
   ```bash
   git clone https://github.com/ychgh/vincent_ai_tutor.git
   cd vincent_ai_tutor
   ```

3. **Start OpenCode**:
   ```bash
   opencode
   ```

4. **Switch to the Tutor agent** by pressing Tab or mentioning `@tutor`

There are many ways to use Smart Learner, but here is the recommended workflow:

## Create a new lesson plan

`/plan [SUBJECT]`

Examples:

- `/plan I want to learn the photoelectric effect`
- `/plan I want to understand how 1 + 1 = 2`
- `/plan I want to learn Japanese, but I have no experience with it.`
- `/plan Introduction to machine learning`

The curriculum planner will create:
- **Prerequisite lessons** (0.1 - 0.9): Foundation knowledge
- **Main lessons** (1.1 onwards): The actual topic content

## Starting the lesson plan

`/start`

Examples:

- `/start` - Start from the beginning
- `/start 1.3` - Jump to lesson 1.3
- `/start 0.5` - Start from prerequisite lesson 0.5

## Continuing the lesson

`/continue`

This will move to the next section of your current lesson, or advance to the next lesson if you've completed the current one.

## Asking a question

There is no specific command for this. Just ask your question naturally and Smart Learner will answer it in context of your current lesson.

Examples:
- "Can you explain that again?"
- "What does this term mean?"
- "Can you give me another example?"

## Testing yourself

`/test`

This will generate a practice test for your current topic, including:
- An example problem with full solution
- A simple problem (difficulty 3/10)
- A complex familiar problem (difficulty 6/10)
- A complex unfamiliar problem (difficulty 9/10)

## Changing Language

`/language [LANGUAGE]`

Examples:

- `/language Chinese`
- `/language Japanese`
- `/language Spanish`
- `/language French`

Smart Learner will continue all lessons in your chosen language.

## Using the Configuration Wizard

If you're not sure what configuration is best for you, use the wizard:

```
@tutor-wizard help me find my ideal learning configuration
```

The wizard will:
1. Ask you questions about your learning preferences
2. Guide you through each configuration option
3. Provide a summary of your ideal settings

# Troubleshooting

### Agent not responding correctly

If Smart Learner doesn't respond as expected:
- Make sure you're in the correct agent (use Tab to switch)
- Try rephrasing your request
- Use explicit commands like `/plan`, `/start`, `/test`

### Wrong agent selected

If you accidentally switch to a different agent:
- Press Tab to cycle through agents
- Or type `@tutor` to mention the tutor directly

### Lessons not continuing properly

If the lesson seems stuck:
- Use `/continue` to advance
- Or `/start [lesson number]` to jump to a specific lesson

### Want to reset configuration

Use `/config` to view and modify your current settings at any time.
