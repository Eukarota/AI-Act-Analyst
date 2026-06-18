"""
Scope mapping for AI Act citations.

Per CLAUDE.md section 12.2: scoped retrieval per node, not a global pass.
classify retrieves over Art. 5 + Annex I/III; enumerate_obligations over
Art. 8-15, 26, 50, 53; etc.

The mapping is a property of the regulation, not of the agent core. Keep it
small, explicit, and conservative: an unknown citation maps to None (no
scope), which makes it visible to broad searches but invisible to scoped
ones. Adding new scope buckets is intentional and reviewable.
"""

from __future__ import annotations

from backend.agent.state import Citation

# Article -> scope bucket. Multiple articles map to the same bucket where the
# regulation already treats them as one topic.
_ARTICLE_SCOPES: dict[str, str] = {
    "5": "art_5_prohibited",
    "6": "high_risk_definition",
    "7": "high_risk_definition",
    "8": "high_risk_obligations",
    "9": "high_risk_obligations",
    "10": "high_risk_obligations",
    "11": "high_risk_obligations",
    "12": "high_risk_obligations",
    "13": "high_risk_obligations",
    "14": "high_risk_obligations",
    "15": "high_risk_obligations",
    "16": "high_risk_obligations",
    "17": "high_risk_obligations",
    "26": "deployer_obligations",
    "27": "deployer_obligations",
    "43": "conformity_assessment",
    "47": "conformity_assessment",
    "48": "conformity_assessment",
    "49": "conformity_assessment",
    "50": "art_50_transparency",
    "51": "gpai",
    "52": "gpai",
    "53": "gpai",
    "54": "gpai",
    "55": "gpai_systemic",
    "56": "gpai",
}

_ANNEX_SCOPES: dict[str, str] = {
    "I": "annex_i_high_risk_products",
    "III": "annex_iii_high_risk_uses",
    "IV": "annex_iv_technical_documentation",
    "XI": "gpai_documentation",
    "XII": "gpai_documentation",
}

# Paragraphs that sit inside a normally-scoped article but are non-operational
# (carve-outs, "without prejudice" clauses, Commission powers, codes of
# practice, transitional provisions). They stay in the corpus and remain
# searchable via a global pass, but scoped retrieval skips them because they
# add noise to the report: they reference duties without imposing any.
_NON_OPERATIONAL_PARAGRAPHS: set[tuple[str, str]] = {
    # Art. 50: paragraphs 1-4 are the operational transparency duties.
    # Paragraphs 5, 6 and 7 are without-prejudice / codes of practice /
    # AI Office encouragement, none of which compliance teams owe.
    ("50", "5"),
    ("50", "6"),
    ("50", "7"),
}


def scope_for_citation(citation: Citation) -> str | None:
    """
    Map a Citation to its retrieval scope.

    Returns None when the citation does not belong to a defined scope. Recitals
    are intentionally unscoped: they are retrieved alongside articles via the
    recital->article map at query time, not by direct scope filter.
    """
    if citation.article and citation.article in _ARTICLE_SCOPES:
        if (
            citation.paragraph
            and (citation.article, citation.paragraph) in _NON_OPERATIONAL_PARAGRAPHS
        ):
            return None
        return _ARTICLE_SCOPES[citation.article]
    if citation.annex_ref and citation.annex_ref in _ANNEX_SCOPES:
        return _ANNEX_SCOPES[citation.annex_ref]
    return None


def known_scopes() -> set[str]:
    """The set of scope tags this regulation emits. Use for validation."""
    return set(_ARTICLE_SCOPES.values()) | set(_ANNEX_SCOPES.values())
