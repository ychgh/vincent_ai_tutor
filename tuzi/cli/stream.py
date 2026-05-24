"""Streaming display helper for LLM responses."""

from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown

console = Console()


def stream_markdown(chunks, initial: str = ""):
    """Stream LLM tokens and render as markdown with Live display.

    Usage:
        for chunk in llm.chat_stream(messages):
            ...
    """
    buffer = initial
    with Live(Markdown(buffer), console=console, refresh_per_second=10) as live:
        for chunk in chunks:
            buffer += chunk
            live.update(Markdown(buffer))
    return buffer
