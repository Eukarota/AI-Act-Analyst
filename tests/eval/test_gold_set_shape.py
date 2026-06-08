"""
Schema tests on eval/gold_set.jsonl.

These guard against accidental shape regressions: a malformed row breaks
the eval gate, which then blocks deploys. We also assert the stratified /
hard / adversarial slice is non-empty so the per-slice metrics stay
meaningful.
"""

from __future__ import annotations

import json
from pathlib import Path

GOLD_PATH = Path(__file__).resolve().parents[2] / "eval" / "gold_set.jsonl"

REQUIRED_KEYS = {
    "id",
    "draft",
    "slice",
    "difficulty",
    "domain",
    "expected_tier",
    "expected_articles",
    "system_description",
    "scripted_extraction",
    "rationale",
}
ALLOWED_TIERS = {
    "prohibited",
    "high_risk_annex_i",
    "high_risk_annex_iii",
    "transparency",
    "minimal",
    "gpai",
    "gpai_systemic",
}
ALLOWED_SLICES = {"stratified", "hard", "adversarial"}


def _load_cases() -> list[dict]:  # type: ignore[type-arg]
    rows: list[dict] = []  # type: ignore[type-arg]
    for line in GOLD_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def test_gold_set_has_at_least_thirty_cases() -> None:
    rows = _load_cases()
    assert len(rows) >= 30


def test_every_row_has_required_keys_and_valid_values() -> None:
    rows = _load_cases()
    seen_ids: set[str] = set()
    for row in rows:
        missing = REQUIRED_KEYS - row.keys()
        assert not missing, f"row {row.get('id')!r} missing {missing}"
        assert row["id"] not in seen_ids, f"duplicate id {row['id']!r}"
        seen_ids.add(row["id"])
        assert row["expected_tier"] in ALLOWED_TIERS, row["expected_tier"]
        assert row["slice"] in ALLOWED_SLICES, row["slice"]
        assert isinstance(row["expected_articles"], list)
        for article in row["expected_articles"]:
            assert isinstance(article, str)


def test_every_slice_is_non_empty() -> None:
    rows = _load_cases()
    seen_slices = {row["slice"] for row in rows}
    assert seen_slices >= ALLOWED_SLICES


def test_all_tiers_are_represented_in_the_set() -> None:
    rows = _load_cases()
    seen_tiers = {row["expected_tier"] for row in rows}
    assert seen_tiers >= ALLOWED_TIERS, ALLOWED_TIERS - seen_tiers
