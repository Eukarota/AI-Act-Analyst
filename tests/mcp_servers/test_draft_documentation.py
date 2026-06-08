"""draft_documentation unit tests."""

from __future__ import annotations

from backend.agent.state import (
    AttributeSet,
    Citation,
    ClassificationResult,
    RetrievedPassage,
    Tier,
)
from backend.mcp_servers.draft_documentation import (
    DraftDocumentationArgs,
    draft_documentation,
)
from regulations.ai_act.document_templates import AiActTemplates
from regulations.ai_act.rules import RULES_VERSION


def _classification(tier: Tier, refs: tuple[Citation, ...] = ()) -> ClassificationResult:
    return ClassificationResult(
        tier=tier,
        fired_rule="test",
        supporting_refs=refs,
        rules_version=RULES_VERSION,
        rationale="Test classification.",
    )


def _attrs() -> AttributeSet:
    return AttributeSet(purpose="Filter job applications and rank candidates for recruitment.")


def _passage(article: str, text: str = "Article text") -> RetrievedPassage:
    return RetrievedPassage(
        text=text,
        citation=Citation(
            celex_id="32024R1689",
            article=article,
            corpus_version="test",
        ),
        score=0.5,
    )


async def test_draft_documentation_renders_annex_iv_for_high_risk() -> None:
    result = await draft_documentation(
        DraftDocumentationArgs(
            system_name="Recruitment Assistant",
            classification=_classification(Tier.HIGH_RISK_ANNEX_III, (_passage("6").citation,)),
            attributes=_attrs(),
            retrieved_passages=(_passage("9"), _passage("11")),
            documents_to_draft=(),
            language="en",
        ),
        templates=AiActTemplates(),
    )
    assert len(result.documents) == 1
    annex = result.documents[0]
    assert annex.kind == "annex_iv"
    assert "Recruitment Assistant" in annex.body
    assert "Annex IV" in annex.body
    assert annex.citations, "Annex IV draft must carry citations"


async def test_draft_documentation_renders_art_50_paragraphs_from_supporting_refs() -> None:
    # A transparency classification supported by Art. 50(1) and Art. 50(2) should
    # default to drafting both the interaction and synthetic-content notices.
    refs = (
        Citation(celex_id="32024R1689", article="50", paragraph="1", corpus_version="rules"),
        Citation(celex_id="32024R1689", article="50", paragraph="2", corpus_version="rules"),
    )
    result = await draft_documentation(
        DraftDocumentationArgs(
            system_name="Marketing Studio",
            classification=_classification(Tier.TRANSPARENCY, refs),
            attributes=_attrs(),
            retrieved_passages=(),
            documents_to_draft=(),
            language="fr",
        ),
        templates=AiActTemplates(),
    )
    kinds = {d.kind for d in result.documents}
    assert "art_50_interaction" in kinds
    assert "art_50_synthetic" in kinds


async def test_draft_documentation_explicit_kinds_override_suggestion() -> None:
    result = await draft_documentation(
        DraftDocumentationArgs(
            system_name="Deepfake Tool",
            classification=_classification(Tier.TRANSPARENCY, ()),
            attributes=_attrs(),
            retrieved_passages=(),
            documents_to_draft=("art_50_deepfake",),
            language="fr",
        ),
        templates=AiActTemplates(),
    )
    assert len(result.documents) == 1
    assert result.documents[0].kind == "art_50_deepfake"
    body = result.documents[0].body
    assert "50(4)" in body or "50 (4)" in body


async def test_draft_documentation_french_copy_renders_in_french() -> None:
    result = await draft_documentation(
        DraftDocumentationArgs(
            system_name="ChatBot",
            classification=_classification(Tier.TRANSPARENCY, ()),
            attributes=_attrs(),
            retrieved_passages=(),
            documents_to_draft=("art_50_interaction",),
            language="fr",
        ),
        templates=AiActTemplates(),
    )
    body = result.documents[0].body
    # French markers we expect from the template.
    assert "intelligence artificielle" in body


async def test_draft_documentation_unknown_kind_raises() -> None:
    import pytest

    with pytest.raises(ValueError):
        await draft_documentation(
            DraftDocumentationArgs(
                system_name="X",
                classification=_classification(Tier.HIGH_RISK_ANNEX_III, ()),
                attributes=_attrs(),
                retrieved_passages=(),
                documents_to_draft=("art_99_unknown",),
                language="en",
            ),
            templates=AiActTemplates(),
        )
