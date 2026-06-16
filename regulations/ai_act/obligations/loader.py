"""AiActObligations: implements the ObligationsMap Protocol."""

from __future__ import annotations

from backend.agent.state import ClassificationResult, Obligation
from regulations.ai_act.obligations._data import OBLIGATIONS_BY_TIER
from regulations.ai_act.obligations._summaries_fr import FR_SUMMARIES


def localize_obligation(obligation: Obligation, language: str) -> Obligation:
    """Return a copy of obligation with its summary swapped into language."""
    if language.upper() != "FR":
        return obligation
    fr = FR_SUMMARIES.get(obligation.obligation_id)
    if fr is None:
        return obligation
    return obligation.model_copy(update={"summary": fr})


def localize_obligations(obligations: list[Obligation], language: str) -> list[Obligation]:
    return [localize_obligation(o, language) for o in obligations]


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
