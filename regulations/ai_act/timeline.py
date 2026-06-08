"""AI Act timeline loader (TimelineConfig implementation)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_TIMELINE_PATH = Path(__file__).parent / "config" / "timeline.yaml"


class AiActTimeline:
    """TimelineConfig for the AI Act. Reads dates and sources from YAML."""

    def __init__(self, path: Path = _TIMELINE_PATH) -> None:
        raw: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        self._milestones: dict[str, dict[str, str]] = raw.get("milestones", {})
        self._meta = {
            "regulation": raw.get("regulation"),
            "celex_id": raw.get("celex_id"),
            "last_reviewed": raw.get("last_reviewed"),
        }
        self._amendments: list[dict[str, Any]] = raw.get("amendments_in_flight", [])

    def applicable_on(self, milestone: str) -> str | None:
        entry = self._milestones.get(milestone)
        return entry.get("date") if entry else None

    def all_milestones(self) -> dict[str, dict[str, str]]:
        return dict(self._milestones)

    @property
    def regulation(self) -> str | None:
        return self._meta["regulation"]

    @property
    def celex_id(self) -> str | None:
        return self._meta["celex_id"]

    @property
    def amendments_in_flight(self) -> list[dict[str, Any]]:
        return list(self._amendments)
