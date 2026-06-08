"""
AiActTemplates: implements the TemplateSet Protocol.

Templates render with Jinja2's StrictUndefined so missing context variables
fail loudly during draft_documentation instead of silently producing
truncated output. CLAUDE.md non-negotiable: every drafted document carries
the pre-assessment framing, never legal advice.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

_TEMPLATES_DIR = Path(__file__).parent / "templates"


class TemplateNotFound(KeyError):
    pass


class AiActTemplates:
    def __init__(self, templates_dir: Path = _TEMPLATES_DIR) -> None:
        self.templates_dir = templates_dir
        self._env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=select_autoescape(default=False),
            undefined=StrictUndefined,
            keep_trailing_newline=True,
        )

    def render(self, name: str, context: dict[str, Any]) -> str:
        try:
            template = self._env.get_template(self._normalise(name))
        except Exception as exc:
            raise TemplateNotFound(name) from exc
        return template.render(**context)

    def names(self) -> list[str]:
        return sorted(path.stem for path in self.templates_dir.glob("*.j2") if path.is_file())

    @staticmethod
    def _normalise(name: str) -> str:
        return name if name.endswith(".j2") else f"{name}.j2"
