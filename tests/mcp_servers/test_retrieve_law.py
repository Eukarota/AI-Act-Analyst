"""retrieve_law unit tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from backend.adapters.fake_embedder import FakeEmbedder
from backend.adapters.in_memory_store import InMemoryVectorStore
from backend.agent.state import Citation
from backend.mcp_servers.retrieve_law import RetrieveLawArgs, retrieve_law
from backend.rag.retrieve import HybridRetriever
from regulations.ai_act.corpus.loader import AiActChunkerConfig, AiActCorpusLoader

FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "regulations"
    / "ai_act"
    / "corpus"
    / "fixture_excerpt.txt"
)


@pytest.fixture()
async def retriever() -> HybridRetriever:
    loader = AiActCorpusLoader.from_text(FIXTURE.read_text(encoding="utf-8"))
    triples = list(loader.iter_chunks_with_scope(chunker=AiActChunkerConfig()))
    embedder = FakeEmbedder()
    store = InMemoryVectorStore(corpus_version=loader.corpus_version())
    vectors = await embedder.embed_documents([t[0] for t in triples])
    rows: list[tuple[str, list[float], Citation, str | None]] = [
        (text, vector, citation, scope)
        for (text, citation, scope), vector in zip(triples, vectors, strict=True)
    ]
    await store.upsert(rows)
    return HybridRetriever(store=store, embedder=embedder)


async def test_retrieve_law_returns_cited_passages(retriever: HybridRetriever) -> None:
    result = await retrieve_law(
        RetrieveLawArgs(query="recruitment selection of natural persons", top_k=5),
        retriever=retriever,
    )
    assert result.passages
    for passage in result.passages:
        assert passage.citation.celex_id == "32024R1689"
        assert passage.citation.corpus_version


async def test_retrieve_law_respects_top_k(retriever: HybridRetriever) -> None:
    result = await retrieve_law(
        RetrieveLawArgs(query="risk management system", top_k=2),
        retriever=retriever,
    )
    assert len(result.passages) <= 2


async def test_retrieve_law_scope_is_passed_through(retriever: HybridRetriever) -> None:
    result = await retrieve_law(
        RetrieveLawArgs(query="prohibited social scoring", scope="art_5_prohibited", top_k=5),
        retriever=retriever,
    )
    # Either the scope filter narrows results to Art. 5 chunks, or returns nothing
    # if dense+sparse both fail. The contract here is the scope is preserved.
    assert result.scope == "art_5_prohibited"
    for passage in result.passages:
        assert passage.retrieval_scope in (None, "art_5_prohibited")
