"""
draft_documentation: render Annex IV skeleton + Art. 50 language as applicable.

This is the only tool allowed to call the LLM at non-zero temperature, per
CLAUDE.md section 12.3. The templates do the structural heavy lifting; the
LLM is invoked only for short, optional prose flourishes (e.g. an executive
summary) that do not change the legal content. The grounded text comes from
the templates and from the retrieved passages.

Citation guarantee:
  Every DraftedDocument carries the citations supplied by the caller (the
  agent's previous nodes assembled the retrieved set). Templates render
  citation references inline so a downstream grounding check matches them
  against the same retrieved set.

Document kinds:
  - "annex_iv"               Annex IV technical-documentation skeleton.
  - "art_50_interaction"     Art. 50(1) disclosure copy.
  - "art_50_synthetic"       Art. 50(2) synthetic-content notice.
  - "art_50_emotion"         Art. 50(3) emotion / biometric notice.
  - "art_50_deepfake"        Art. 50(4) deepfake disclosure.
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.agent.state import (
    AttributeSet,
    Citation,
    ClassificationResult,
    DraftedDocument,
    RetrievedPassage,
    Tier,
)
from backend.ports.llm_provider import LLMProvider
from backend.ports.regulation import TemplateSet


@dataclass(frozen=True)
class DraftDocumentationArgs:
    system_name: str
    classification: ClassificationResult
    attributes: AttributeSet
    retrieved_passages: tuple[RetrievedPassage, ...]
    documents_to_draft: tuple[str, ...]
    language: str = "fr"


@dataclass(frozen=True)
class DraftDocumentationResult:
    documents: list[DraftedDocument]


_TEMPLATE_BY_KIND: dict[str, str] = {
    "annex_iv": "annex_iv_skeleton",
    "art_50_interaction": "art_50_interaction_disclosure",
    "art_50_synthetic": "art_50_synthetic_content_notice",
    "art_50_emotion": "art_50_emotion_biometric_notice",
    "art_50_deepfake": "art_50_deepfake_disclosure",
}

_TITLES_BY_LANG: dict[str, dict[str, str]] = {
    "en": {
        "annex_iv": "Annex IV: Technical Documentation Skeleton",
        "art_50_interaction": "Art. 50(1): Interaction Disclosure",
        "art_50_synthetic": "Art. 50(2): Synthetic Content Notice",
        "art_50_emotion": "Art. 50(3): Emotion or Biometric Categorisation Notice",
        "art_50_deepfake": "Art. 50(4): Deepfake Disclosure",
    },
    "fr": {
        "annex_iv": "Annexe IV : squelette de documentation technique",
        "art_50_interaction": "Art. 50(1) : information d'interaction avec une IA",
        "art_50_synthetic": "Art. 50(2) : marquage de contenu synthétique",
        "art_50_emotion": "Art. 50(3) : information de reconnaissance d'émotion ou catégorisation biométrique",
        "art_50_deepfake": "Art. 50(4) : information de contenu hypertruqué",
    },
}


def _title_for(kind: str, language: str) -> str:
    titles = _TITLES_BY_LANG.get(language.lower(), _TITLES_BY_LANG["en"])
    return titles.get(kind, kind)


def _suggest_kinds(classification: ClassificationResult) -> tuple[str, ...]:
    """Default selection if the caller does not specify which documents to draft."""
    tier = classification.tier
    if tier in (Tier.HIGH_RISK_ANNEX_I, Tier.HIGH_RISK_ANNEX_III):
        return ("annex_iv",)
    if tier == Tier.TRANSPARENCY:
        # Best-effort selection from supporting refs; the caller can override.
        paragraphs = {ref.paragraph for ref in classification.supporting_refs}
        kinds: list[str] = []
        if "1" in paragraphs:
            kinds.append("art_50_interaction")
        if "2" in paragraphs:
            kinds.append("art_50_synthetic")
        if "3" in paragraphs:
            kinds.append("art_50_emotion")
        if "4" in paragraphs:
            kinds.append("art_50_deepfake")
        return tuple(kinds) or ("art_50_interaction",)
    return ()


def _citations_in_context(
    passages: tuple[RetrievedPassage, ...],
    classification: ClassificationResult,
) -> tuple[Citation, ...]:
    """Citations used to populate the rendered document references block."""
    out: list[Citation] = list(classification.supporting_refs)
    seen = {(c.celex_id, c.article, c.paragraph, c.annex_ref, c.recital_ref) for c in out}
    for passage in passages:
        key = (
            passage.citation.celex_id,
            passage.citation.article,
            passage.citation.paragraph,
            passage.citation.annex_ref,
            passage.citation.recital_ref,
        )
        if key not in seen:
            out.append(passage.citation)
            seen.add(key)
    return tuple(out)


async def draft_documentation(
    args: DraftDocumentationArgs,
    *,
    templates: TemplateSet,
    llm: LLMProvider | None = None,
) -> DraftDocumentationResult:
    kinds = args.documents_to_draft or _suggest_kinds(args.classification)
    citations = _citations_in_context(args.retrieved_passages, args.classification)

    drafted: list[DraftedDocument] = []
    for kind in kinds:
        if kind not in _TEMPLATE_BY_KIND:
            raise ValueError(f"draft_documentation: unknown document kind {kind!r}")
        template_name = _TEMPLATE_BY_KIND[kind]
        title = _title_for(kind, args.language)
        context: dict[str, object] = {
            "system_name": args.system_name,
            "classification": args.classification,
            "citations": citations,
            "attributes": args.attributes,
            "language": args.language,
        }
        body = templates.render(template_name, context)
        drafted.append(
            DraftedDocument(
                kind=kind,
                title=title,
                body=body,
                citations=citations,
            )
        )

    return DraftDocumentationResult(documents=drafted)
