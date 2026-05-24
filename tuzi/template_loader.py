"""Jinja2 template loader for prompt rendering."""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined


_template_dir = Path(__file__).parent / "prompts"
_env = Environment(
    loader=FileSystemLoader(str(_template_dir)),
    undefined=StrictUndefined,
    trim_blocks=True,
    lstrip_blocks=True,
)


def render(template_name: str, **kwargs) -> str:
    """Render a Jinja2 template with the given variables."""
    template = _env.get_template(template_name)
    return template.render(**kwargs)
