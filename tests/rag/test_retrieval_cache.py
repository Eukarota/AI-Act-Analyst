"""Unit tests for the LRU retrieval cache."""

from __future__ import annotations

from collections.abc import Sequence

from backend.adapters.fake_embedder import FakeEmbedder
from backend.agent.state import Citation, RetrievedPassage
from backend.rag.retrieval_cache import CachingRetriever
from backend.rag.retrieve import HybridRetriever, RetrievalConfig


class _CountingRetriever(HybridRetriever):
    """Stand-in HybridRetriever that returns canned passages and counts calls."""

    def __init__(self, passages: Sequence[RetrievedPassage]) -> None:
        # We never actually use store/embedder in the test; pass None-like
        # objects by reusing FakeEmbedder so the parent constructor is happy.
        super().__init__(store=object(), embedder=FakeEmbedder())  # type: ignore[arg-type]
        self._canned = list(passages)
        self.calls = 0

    async def retrieve(
        self,
        query: str,
        *,
        scope: str | None,
        config: RetrievalConfig | None = None,
    ) -> list[RetrievedPassage]:
        self.calls += 1
        return list(self._canned)


def _passage(article: str) -> RetrievedPassage:
    return RetrievedPassage(
        text=f"Article {article} text",
        citation=Citation(celex_id="X", article=article, lang="en", corpus_version="v1"),
        score=0.9,
        retrieval_scope=None,
    )


async def test_second_lookup_with_same_args_hits_cache() -> None:
    inner = _CountingRetriever([_passage("9")])
    cache = CachingRetriever(inner=inner, corpus_version="v1")

    await cache.retrieve("article 9?", scope="high_risk_obligations")
    await cache.retrieve("article 9?", scope="high_risk_obligations")

    assert inner.calls == 1
    assert cache.stats.hits == 1
    assert cache.stats.misses == 1


async def test_scope_difference_misses_cache() -> None:
    inner = _CountingRetriever([_passage("5")])
    cache = CachingRetriever(inner=inner, corpus_version="v1")

    await cache.retrieve("same query", scope="art_5_prohibited")
    await cache.retrieve("same query", scope="annex_iii_high_risk_uses")

    assert inner.calls == 2
    assert cache.stats.hits == 0
    assert cache.stats.misses == 2


async def test_invalidate_drops_entries() -> None:
    inner = _CountingRetriever([_passage("9")])
    cache = CachingRetriever(inner=inner, corpus_version="v1")

    await cache.retrieve("q", scope="any")
    cache.invalidate(corpus_version="v2")
    await cache.retrieve("q", scope="any")

    assert inner.calls == 2
    assert cache.corpus_version == "v2"
    assert cache.stats.invalidations == 1


async def test_max_entries_evicts_lru() -> None:
    inner = _CountingRetriever([_passage("9")])
    cache = CachingRetriever(inner=inner, corpus_version="v1", max_entries=2)

    await cache.retrieve("q1", scope="a")
    await cache.retrieve("q2", scope="a")
    await cache.retrieve("q3", scope="a")  # evicts q1, cache holds {q2, q3}

    assert cache.stats.evictions == 1
    assert inner.calls == 3

    # q1 was evicted, so the next lookup misses and re-evicts q2.
    await cache.retrieve("q1", scope="a")
    assert cache.stats.evictions == 2
    assert inner.calls == 4
