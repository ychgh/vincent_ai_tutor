"""Native interactive configuration wizard for Tuzi."""

from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

from ..models import (
    CommunicationStyle,
    Depth,
    LearningStyle,
    ReasoningFramework,
    ToneStyle,
    UserProfile,
)

console = Console()


def run_wizard(existing: Optional[UserProfile] = None) -> UserProfile:
    """Run the interactive configuration wizard. Returns a UserProfile."""
    profile = existing or UserProfile()

    console.print(
        Panel(
            "[bold bright_blue]🧙 Configuration Wizard 🧙[/bold bright_blue]\n\n"
            "Let's set up your learning preferences. Take your time — "
            "you can always change these later with [bold]/config[/bold].",
            border_style="bright_blue",
        )
    )

    # 1. Name
    profile.name = Prompt.ask("What's your name?", default=profile.name)

    # 2. Depth
    console.print("\n[bold]🎯 Depth[/bold] — How deep should lessons go?")
    depth_options = [d.value for d in Depth]
    choice = _menu_select(depth_options, "Depth", _find_index(depth_options, profile.depth.value))
    profile.depth = Depth(choice)

    # 3. Learning Style
    console.print(
        "\n[bold]🧠 Learning Style[/bold] — How do you learn best?"
    )
    style_options = [s.value for s in LearningStyle]
    choice = _menu_select(
        style_options,
        "Learning Style",
        _find_index(style_options, profile.learning_style.value),
    )
    profile.learning_style = LearningStyle(choice)

    # 4. Communication Style
    console.print(
        "\n[bold]🗣️ Communication Style[/bold] — How should the tutor explain things?"
    )
    comm_options = [c.value for c in CommunicationStyle]
    choice = _menu_select(
        comm_options,
        "Communication Style",
        _find_index(comm_options, profile.communication_style.value),
    )
    profile.communication_style = CommunicationStyle(choice)

    # 5. Tone
    console.print(
        "\n[bold]🌟 Tone[/bold] — What tone should the tutor use?"
    )
    tone_options = [t.value for t in ToneStyle]
    choice = _menu_select(
        tone_options, "Tone", _find_index(tone_options, profile.tone_style.value)
    )
    profile.tone_style = ToneStyle(choice)

    # 6. Reasoning Framework
    console.print(
        "\n[bold]🔎 Reasoning Framework[/bold] — How should the tutor build understanding?"
    )
    reason_options = [r.value for r in ReasoningFramework]
    choice = _menu_select(
        reason_options,
        "Reasoning",
        _find_index(reason_options, profile.reasoning_framework.value),
    )
    profile.reasoning_framework = ReasoningFramework(choice)

    # 7. Emojis
    profile.emojis_enabled = Confirm.ask(
        "😀 Use emojis in lessons?", default=profile.emojis_enabled
    )

    # 8. Language
    profile.language = Prompt.ask("🌐 Language", default=profile.language)

    console.print(
        Panel(
            "[bold green]Configuration complete![/bold green] "
            "Your profile has been saved.\n\n"
            "Next: try [bold]/plan <topic>[/bold] to generate a study plan!",
            border_style="green",
        )
    )

    return profile


def _menu_select(options: list[str], label: str, default_idx: int = 0) -> str:
    """Show a numbered menu and return the selected option string."""
    for i, opt in enumerate(options, 1):
        marker = " ← (default)" if i == default_idx + 1 else ""
        console.print(f"  [bold]{i}[/bold]. {opt}{marker}")

    choice = Prompt.ask(
        f"Choose {label}",
        choices=[str(i) for i in range(1, len(options) + 1)],
        default=str(default_idx + 1),
    )
    return options[int(choice) - 1]


def _find_index(options: list[str], value: str) -> int:
    """Find the index of a value in a list, defaulting to 0."""
    try:
        return options.index(value)
    except ValueError:
        return 0
