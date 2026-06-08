"""
AiActGlossary: implements the Glossary Protocol over the Art. 3 YAML data.

CLAUDE.md section 12.2: "when an extracted attribute references a defined
term, inject the legal definition so the model uses it over its prior".
This loader is the source of those injections.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

_GLOSSARY_PATH = Path(__file__).parent / "glossary.yaml"


@dataclass(frozen=True)
class DefinedTerm:
    key: str
    text: str
    article: str
    paragraph: str | None


class AiActGlossary:
    """Glossary implementation for the AI Act Art. 3 defined terms."""

    def __init__(self, path: Path = _GLOSSARY_PATH) -> None:
        raw: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        terms_raw: dict[str, Any] = raw.get("terms") or {}
        self._terms: dict[str, DefinedTerm] = {
            key: DefinedTerm(
                key=key,
                text=" ".join(str(entry.get("text") or "").split()),
                article=str(entry.get("article") or "3"),
                paragraph=(str(entry["paragraph"]) if entry.get("paragraph") is not None else None),
            )
            for key, entry in terms_raw.items()
        }

    def lookup(self, term: str) -> str | None:
        entry = self._terms.get(term.lower().replace(" ", "_"))
        return entry.text if entry else None

    def all_terms(self) -> dict[str, str]:
        return {key: entry.text for key, entry in self._terms.items()}

    def entries(self) -> list[DefinedTerm]:
        return list(self._terms.values())

    def entry(self, term: str) -> DefinedTerm | None:
        return self._terms.get(term.lower().replace(" ", "_"))
