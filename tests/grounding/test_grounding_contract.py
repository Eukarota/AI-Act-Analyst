"""
The grounding contract is the single most important guarantee in this system.
These tests assert the contract by construction: anything that would let an
uncited or unsupported claim through must fail loudly.
"""

from __future__ import annotations

import pytest

from backend.agent.state import Citation, RetrievedPassage
from backend.rag.grounding import (
    Claim,
    GroundingError,
    assert_grounded,
)


def _cite(
    article: str | None = None, paragraph: str | None = None, annex_ref: str | None = None
) -> Citation:
    return Citation(
        celex_id="32024R1689",
        article=article,
        paragraph=paragraph,
        annex_ref=annex_ref,
        corpus_version="test-v1",
    )


def _passage(citation: Citation, text: str = "lorem ipsum") -> RetrievedPassage:
    return RetrievedPassage(text=text, citation=citation, score=0.5)


def test_uncited_claim_is_rejected() -> None:
    claim = Claim(text="High-risk systems must keep technical documentation.", citations=())
    with pytest.raises(GroundingError) as exc:
        assert_grounded([claim], retrieved=[_passage(_cite(article="11"))])
    assert exc.value.result.violation_count == 1
    assert exc.value.result.violations[0].uncited


def test_unsupported_citation_is_rejected() -> None:
    # Claim cites Annex IV, retrieval only returned Art. 11.
    claim = Claim(
        text="Annex IV requires a technical documentation skeleton.",
        citations=(_cite(annex_ref="IV"),),
    )
    with pytest.raises(GroundingError):
        assert_grounded([claim], retrieved=[_passage(_cite(article="11"))])


def test_matching_citation_is_accepted() -> None:
    claim = Claim(
        text="A risk management system must be established.",
        citations=(_cite(article="9"),),
    )
    result = assert_grounded([claim], retrieved=[_passage(_cite(article="9"))])
    assert result.grounded
    assert result.violation_count == 0
    assert result.checked_claims == 1


def test_partial_match_is_still_a_violation() -> None:
    # Claim cites Art. 9 paragraph 2; retrieval only contains Art. 9 paragraph 1.
    # Paragraph is part of the citation key: this must fail closed.
    claim = Claim(
        text="The system shall be planned across the lifecycle.",
        citations=(_cite(article="9", paragraph="2"),),
    )
    with pytest.raises(GroundingError):
        assert_grounded([claim], retrieved=[_passage(_cite(article="9", paragraph="1"))])


def test_eval_mode_returns_violations_without_raising() -> None:
    claims = [
        Claim(text="Cited claim.", citations=(_cite(article="9"),)),
        Claim(text="Uncited claim.", citations=()),
    ]
    result = assert_grounded(
        claims,
        retrieved=[_passage(_cite(article="9"))],
        fail_closed=False,
    )
    assert not result.grounded
    assert result.violation_count == 1
    assert result.checked_claims == 2


def test_empty_claim_text_is_skipped() -> None:
    result = assert_grounded(
        [Claim(text="   ", citations=())],
        retrieved=[],
        fail_closed=True,
    )
    assert result.grounded
    assert result.checked_claims == 0


def test_planted_uncited_claim_in_otherwise_clean_set_still_fails() -> None:
    """A regression guard: a single uncited claim must sink the whole set."""
    claims = [
        Claim(text="Grounded claim.", citations=(_cite(article="9"),)),
        Claim(text="Grounded claim two.", citations=(_cite(article="50"),)),
        Claim(text="UNGROUNDED PLANT.", citations=()),
    ]
    retrieved = [_passage(_cite(article="9")), _passage(_cite(article="50"))]
    with pytest.raises(GroundingError):
        assert_grounded(claims, retrieved=retrieved)
