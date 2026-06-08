"""
Chapter V general-purpose AI (GPAI) track.

Per Art. 3(63), a general-purpose AI model is a model trained on a large
amount of data using self-supervision at scale, displays significant
generality, and is capable of competently performing a wide range of
distinct tasks. Chapter V (Art. 51-56) imposes obligations on providers of
such models.

Art. 51 designates a subset as "GPAI with systemic risk". The presumption
threshold (Art. 51(2)) is cumulative training compute > 10^25 FLOPs, or
Commission designation under Art. 51(1)(b).

This track is *parallel* to the system track: if `is_gpai_model` is True we
return a GPAI tier, not a system tier. A system *built on* a GPAI model is
not itself a GPAI model -- the system-level rules apply, and the upstream
model provider has separate Ch. V obligations.

AttributeSet support:
  - is_gpai_model            -> GPAI track activated
  - extras["compute_flops"]  -> optional float; if > 1e25, GPAI_SYSTEMIC
  - extras["designated_systemic"] -> optional bool override
"""

from __future__ import annotations

from typing import Any

from backend.agent.state import AttributeSet, Tier
from regulations.ai_act.rules._common import RuleMatch, article_citation

SYSTEMIC_FLOPS_THRESHOLD = 1e25


def _extract_float(extras: dict[str, Any], key: str) -> float | None:
    value = extras.get(key)
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def evaluate(attributes: AttributeSet) -> RuleMatch | None:
    if not attributes.is_gpai_model:
        return None

    extras = attributes.extras or {}
    designated = bool(extras.get("designated_systemic", False))
    flops = _extract_float(extras, "compute_flops")
    systemic = designated or (flops is not None and flops > SYSTEMIC_FLOPS_THRESHOLD)

    if systemic:
        reason = (
            "Designated under Art. 51(1)(b)."
            if designated
            else f"Cumulative training compute {flops:.2e} FLOPs exceeds the "
            f"Art. 51(2) presumption threshold of {SYSTEMIC_FLOPS_THRESHOLD:.0e} FLOPs."
        )
        return RuleMatch(
            tier=Tier.GPAI_SYSTEMIC,
            fired_rule="chapter_v.gpai_systemic",
            supporting_refs=(
                article_citation("51"),
                article_citation("55"),
            ),
            rationale=(
                "General-purpose AI model with systemic risk under Art. 51-52. "
                + reason
                + " Subject to Chapter V obligations including Art. 55 (model evaluation, "
                "adversarial testing, incident reporting, cybersecurity)."
            ),
        )

    return RuleMatch(
        tier=Tier.GPAI,
        fired_rule="chapter_v.gpai",
        supporting_refs=(
            article_citation("51"),
            article_citation("53"),
        ),
        rationale=(
            "General-purpose AI model under Art. 51-53. Provider obligations include "
            "technical documentation (Art. 53 + Annexes XI/XII), copyright policy, "
            "and a publicly available summary of training content."
        ),
    )
