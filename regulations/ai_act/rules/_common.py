"""
Shared helpers for the AI Act rules layer.

CLAUDE.md non-negotiable: the LLM extracts attributes; the rules decide the
tier. The rules layer is a pure function over AttributeSet -> RuleMatch | None
with table-driven tests. Nothing in this layer makes network calls, reads a
prompt, or consults the model.

Citations emitted here are *rule-layer pointers* -- they record which Article
or Annex fired the rule. The grounding contract uses the citation key
(celex_id + article + paragraph + annex_ref + recital_ref) for matching, so
these pointers line up cleanly with the citations on retrieved passages. We
stamp corpus_version with the constant RULES_CORPUS_VERSION so a rule's
provenance is distinguishable from a retrieval's provenance during debugging.
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.agent.state import AttributeSet, Citation, Tier

CELEX_ID = "32024R1689"
RULES_CORPUS_VERSION = "ai_act-rules"
AI_ACT_EUR_LEX_BASE = "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R1689"


def article_citation(
    article: str,
    *,
    paragraph: str | None = None,
    point: str | None = None,
) -> Citation:
    """Build a Citation pointing at an article (optionally a paragraph/point)."""
    suffix = f"#art_{article}"
    if paragraph:
        suffix += f"_{paragraph}"
    return Citation(
        celex_id=CELEX_ID,
        article=article,
        paragraph=paragraph,
        annex_ref=None,
        recital_ref=None,
        lang="en",
        url=AI_ACT_EUR_LEX_BASE + suffix,
        corpus_version=RULES_CORPUS_VERSION,
    )


def annex_citation(annex: str, *, point: str | None = None) -> Citation:
    """Build a Citation pointing at an Annex (optionally a numbered point)."""
    suffix = f"#anx_{annex}"
    if point:
        suffix += f"_{point}"
    return Citation(
        celex_id=CELEX_ID,
        article=None,
        paragraph=point,
        annex_ref=annex,
        recital_ref=None,
        lang="en",
        url=AI_ACT_EUR_LEX_BASE + suffix,
        corpus_version=RULES_CORPUS_VERSION,
    )


@dataclass(frozen=True)
class RuleMatch:
    """
    A single rule firing. The engine converts the first match into the final
    ClassificationResult, stamping in the engine's rules_version.
    """

    tier: Tier
    fired_rule: str
    supporting_refs: tuple[Citation, ...]
    rationale: str
    confidence: float = 1.0


def text_search(attributes: AttributeSet) -> str:
    """
    Concatenate the free-text attributes for keyword-based rule checks.

    Keeps rule conditions small and readable. Pre-lowercased.
    """
    parts: list[str] = [
        attributes.purpose,
        attributes.domain or "",
        attributes.deployment_context or "",
        attributes.user_population or "",
    ]
    return " ".join(parts).lower()


def any_phrase(haystack: str, phrases: tuple[str, ...]) -> bool:
    return any(p in haystack for p in phrases)
