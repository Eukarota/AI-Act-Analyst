"""RRF fusion tests."""

from __future__ import annotations

from backend.agent.state import Citation, RetrievedPassage
from backend.rag.rrf import reciprocal_rank_fusion


def _p(article: str, score: float = 1.0, text: str | None = None) -> RetrievedPassage:
    return RetrievedPassage(
        text=text or f"text-{article}",
        citation=Citation(celex_id="X", article=article, corpus_version="v1"),
        score=score,
    )


def test_rrf_promotes_consensus() -> None:
    dense = [_p("9"), _p("11"), _p("5")]
    sparse = [_p("11"), _p("9"), _p("50")]
    fused = reciprocal_rank_fusion([dense, sparse])
    articles = [p.citation.article for p in fused]
    # Articles appearing in both should outrank singletons.
    assert articles.index("9") < articles.index("5")
    assert articles.index("11") < articles.index("50")


def test_rrf_dedupes_by_citation_key() -> None:
    dense = [_p("9", text="dense"), _p("9", text="dense2")]  # same citation, different text
    sparse = [_p("9", text="sparse")]
    fused = reciprocal_rank_fusion([dense, sparse])
    assert len(fused) == 1
    assert fused[0].citation.article == "9"


def test_rrf_respects_top_n() -> None:
    dense = [_p(str(i)) for i in range(20)]
    sparse = [_p(str(i)) for i in range(20)]
    fused = reciprocal_rank_fusion([dense, sparse], top_n=5)
    assert len(fused) == 5


def test_rrf_empty_inputs_return_empty() -> None:
    assert reciprocal_rank_fusion([]) == []
    assert reciprocal_rank_fusion([[], []]) == []
