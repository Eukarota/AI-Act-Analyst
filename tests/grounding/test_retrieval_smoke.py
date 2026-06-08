"""
Phase 2 retrieval smoke (CLAUDE.md plan: "5 sample queries return cited passages").

Indexes the committed AI Act fixture excerpt into InMemoryVectorStore via
the same code path the production indexer uses, then runs 5 representative
queries against the HybridRetriever. Every returned passage must carry
a Citation, and at least one match must hit the expected article/annex for
each query.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from backend.adapters.fake_embedder import FakeEmbedder
from backend.adapters.in_memory_store import InMemoryVectorStore
from backend.agent.state import Citation
from backend.rag.retrieve import HybridRetriever, RetrievalConfig
from regulations.ai_act.corpus.loader import AiActChunkerConfig, AiActCorpusLoader

FIXTURE_PATH = (
    Path(__file__).resolve().parents[2]
    / "regulations"
    / "ai_act"
    / "corpus"
    / "fixture_excerpt.txt"
)


@pytest.fixture()
def indexed_store() -> tuple[InMemoryVectorStore, FakeEmbedder, str]:
    loader = AiActCorpusLoader.from_text(FIXTURE_PATH.read_text(encoding="utf-8"))
    version = loader.corpus_version()
    embedder = FakeEmbedder()
    store = InMemoryVectorStore(corpus_version=version)
    return store, embedder, version


async def _index(store: InMemoryVectorStore, embedder: FakeEmbedder) -> None:
    loader = AiActCorpusLoader.from_text(FIXTURE_PATH.read_text(encoding="utf-8"))
    triples = list(loader.iter_chunks_with_scope(chunker=AiActChunkerConfig()))
    vectors = await embedder.embed_documents([t[0] for t in triples])
    rows: list[tuple[str, list[float], Citation, str | None]] = [
        (text, vector, citation, scope)
        for (text, citation, scope), vector in zip(triples, vectors, strict=True)
    ]
    await store.upsert(rows)


@pytest.mark.parametrize(
    ("query", "expected_article", "expected_annex"),
    [
        ("prohibited social scoring practices", "5", None),
        ("risk management system high risk", "9", None),
        ("transparency obligations for AI systems interacting with natural persons", "50", None),
        ("technical documentation general purpose AI model", "53", None),
        ("recruitment selection of natural persons high risk", None, "III"),
    ],
)
async def test_five_queries_return_cited_passages(
    indexed_store: tuple[InMemoryVectorStore, FakeEmbedder, str],
    query: str,
    expected_article: str | None,
    expected_annex: str | None,
) -> None:
    store, embedder, _version = indexed_store
    await _index(store, embedder)
    retriever = HybridRetriever(store=store, embedder=embedder)

    # The committed fixture has ~18 chunks; FakeEmbedder gives noise on the
    # dense side, so we widen the candidate pool and let BM25 dominate RRF.
    # In prod with e5-large the dense signal is real and these sizes drop.
    cfg = RetrievalConfig(
        candidates_per_retriever=20,
        rrf_k=60,
        fused_top_n=18,
        rerank_top_k=8,
    )
    results = await retriever.retrieve(query, scope=None, config=cfg)

    assert results, f"no results for query {query!r}"
    for passage in results:
        assert passage.citation.celex_id == "32024R1689"
        assert passage.citation.corpus_version

    articles = {p.citation.article for p in results}
    annexes = {p.citation.annex_ref for p in results}
    if expected_article is not None:
        assert expected_article in articles, (
            f"expected Art. {expected_article} in retrieved articles {articles}"
        )
    if expected_annex is not None:
        assert expected_annex in annexes, (
            f"expected Annex {expected_annex} in retrieved annexes {annexes}"
        )
