"""
AI Act classification engine.

The engine wraps the per-area rule modules in a strict, deterministic order
and implements the RuleSet Protocol. CLAUDE.md §3 requires:

  - "Determinism where it matters." Risk classification runs through this
    explicit rules layer, not "ask the LLM what tier this is".
  - The classify() output records which rule fired and the supporting article
    refs. Same AttributeSet + same rules_version => identical result.

Ordering (CLAUDE.md §6):

  1. GPAI parallel track (only when is_gpai_model=True)
     -- a GPAI model is governed by Chapter V regardless of intended use; the
        system-level rules below address the system that uses such a model.
  2. Art. 5 prohibitions  (highest precedence among system-level rules)
  3. Annex I high-risk products
  4. Annex III standalone high-risk uses
  5. Art. 50 transparency triggers
  6. Minimal (default)

The engine's rules_version is bumped whenever the rule logic or article
mapping changes; it is pinned into RunManifest so an assessment can always
be reproduced against a specific rules vintage.
"""

from __future__ import annotations

from backend.agent.state import AttributeSet, ClassificationResult, Tier
from regulations.ai_act.rules import (
    annex_i,
    annex_iii,
    article_5,
    article_50,
    chapter_v,
)
from regulations.ai_act.rules._common import RuleMatch

RULES_VERSION = "ai_act-rules-v1.0.0"


class AiActRules:
    """RuleSet implementation for Regulation (EU) 2024/1689."""

    rules_version: str = RULES_VERSION

    def __init__(self, rules_version: str | None = None) -> None:
        if rules_version:
            self.rules_version = rules_version

    def classify(self, attributes: AttributeSet) -> ClassificationResult:
        match = self._first_match(attributes)
        if match is not None:
            return _materialise(match, self.rules_version)
        return ClassificationResult(
            tier=Tier.MINIMAL,
            fired_rule="default.minimal",
            supporting_refs=(),
            confidence=1.0,
            rationale=(
                "No prohibited practice, Annex I/III trigger, Art. 50 transparency "
                "trigger, or GPAI condition matched. The system is minimal-risk under "
                "the AI Act; no mandatory obligations under the Regulation, though "
                "general law (RGPD etc.) still applies."
            ),
            rules_version=self.rules_version,
        )

    def _first_match(self, attributes: AttributeSet) -> RuleMatch | None:
        if attributes.is_gpai_model:
            return chapter_v.evaluate(attributes)
        evaluators = (
            article_5.evaluate,
            annex_i.evaluate,
            annex_iii.evaluate,
            article_50.evaluate,
        )
        for evaluator in evaluators:
            match = evaluator(attributes)
            if match is not None:
                return match
        return None


def _materialise(match: RuleMatch, rules_version: str) -> ClassificationResult:
    return ClassificationResult(
        tier=match.tier,
        fired_rule=match.fired_rule,
        supporting_refs=match.supporting_refs,
        confidence=match.confidence,
        rationale=match.rationale,
        rules_version=rules_version,
    )
