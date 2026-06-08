"""
Prompt registry loader.

CLAUDE.md sections 9 and 12.4: no inlined prompts, all prompts versioned in
the registry, and prompt_set_version is a deterministic hash over the
registry plus every referenced template.

A registered prompt's sha256 may be null during dev (Phase 1). Phase 6 adds
`make freeze-prompts` which writes the canonical sha256 of every template
into the registry. After that, mismatches raise PromptDriftError.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

REGISTRY_FILENAME = "registry.yaml"


class PromptError(RuntimeError):
    """Base class for prompt registry errors."""


class PromptNotFound(PromptError):
    pass


class PromptDriftError(PromptError):
    """Raised when a template's actual sha256 differs from the registry."""


@dataclass(frozen=True)
class PromptEntry:
    name: str
    version: int
    path: Path
    sha256: str | None
    description: str

    def template_text(self) -> str:
        return self.path.read_text(encoding="utf-8")

    def computed_sha(self) -> str:
        return hashlib.sha256(self.template_text().encode("utf-8")).hexdigest()


class PromptRegistry:
    def __init__(self, prompts_dir: Path) -> None:
        self.prompts_dir = prompts_dir
        registry_path = prompts_dir / REGISTRY_FILENAME
        if not registry_path.exists():
            raise PromptError(f"prompt registry not found at {registry_path}")
        data: dict[str, Any] = yaml.safe_load(registry_path.read_text(encoding="utf-8")) or {}
        raw_prompts: dict[str, Any] = data.get("prompts") or {}

        self._entries: dict[str, PromptEntry] = {}
        for name, raw in raw_prompts.items():
            rel_path = Path(raw["path"])
            # Paths in registry.yaml are repo-relative (e.g. prompts/foo.j2).
            # Resolve against the prompts_dir parent so they resolve correctly.
            full_path = (prompts_dir.parent / rel_path).resolve()
            self._entries[name] = PromptEntry(
                name=name,
                version=int(raw["version"]),
                path=full_path,
                sha256=raw.get("sha256"),
                description=raw.get("description", "").strip(),
            )

        self._env = Environment(
            loader=FileSystemLoader(str(prompts_dir)),
            autoescape=select_autoescape(default=False),
            undefined=StrictUndefined,
            keep_trailing_newline=True,
        )

    def get(self, name: str) -> PromptEntry:
        if name not in self._entries:
            raise PromptNotFound(f"prompt {name!r} not in registry")
        entry = self._entries[name]
        if entry.sha256 is not None and entry.computed_sha() != entry.sha256:
            raise PromptDriftError(
                f"prompt {name!r} sha mismatch: registry={entry.sha256} actual={entry.computed_sha()}"
            )
        return entry

    def render(self, name: str, context: dict[str, Any]) -> str:
        entry = self.get(name)
        template = self._env.get_template(entry.path.name)
        return template.render(**context)

    def prompt_set_version(self) -> str:
        """
        Deterministic hash over the registry plus every referenced template.

        Pinned into RunManifest. A prompt edit changes this; the manifest
        records exactly what was rendered, never a guess.
        """
        h = hashlib.sha256()
        for name in sorted(self._entries):
            entry = self._entries[name]
            h.update(name.encode("utf-8"))
            h.update(str(entry.version).encode("utf-8"))
            h.update(entry.template_text().encode("utf-8"))
        return h.hexdigest()[:16]

    def names(self) -> list[str]:
        return sorted(self._entries)


def default_registry() -> PromptRegistry:
    """Load the project-default registry at <repo>/prompts/."""
    here = Path(__file__).resolve()
    # backend/prompts/loader.py -> repo root is parents[2]
    repo_root = here.parents[2]
    return PromptRegistry(repo_root / "prompts")
