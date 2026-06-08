"""AiActObligations: implements the ObligationsMap Protocol."""

from __future__ import annotations

from backend.agent.state import ClassificationResult, Obligation
from regulations.ai_act.obligations._data import OBLIGATIONS_BY_TIER


class AiActObligations:
    """Maps a ClassificationResult to the list of Obligations that follow."""

    def obligations_for(self, classification: ClassificationResult) -> list[Obligation]:
        return list(OBLIGATIONS_BY_TIER.get(classification.tier, ()))

    def all_articles(self) -> set[str]:
        """Debug helper: the set of article numbers referenced across all tiers."""
        articles: set[str] = set()
        for obligations in OBLIGATIONS_BY_TIER.values():
            for obligation in obligations:
                if obligation.citation.article:
                    articles.add(obligation.citation.article)
        return articles
