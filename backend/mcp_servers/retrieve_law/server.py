"""
FastMCP server for retrieve_law.

Production wiring lives in the agent (Phase 6); this module exists so an
external MCP client can connect to the tool over stdio, which is one of the
load-bearing showcase elements of the project.

Run with: `python -m backend.mcp_servers.retrieve_law`

The server depends on a pre-built HybridRetriever instance. Wiring it up
requires a corpus already indexed and an embedder; production uses the
factory in backend.api.dependencies (Phase 7). For Phase 5 standalone use,
this module exposes build_default_server() which reads from environment.
"""

from __future__ import annotations

import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from backend.adapters.fake_embedder import FakeEmbedder
from backend.adapters.in_memory_store import InMemoryVectorStore
from backend.agent.state import Citation
from backend.mcp_servers._common import JsonDict, passage_to_json
from backend.mcp_servers.retrieve_law.core import RetrieveLawArgs, retrieve_law
from backend.rag.retrieve import HybridRetriever
from regulations.ai_act.corpus.loader import AiActChunkerConfig, AiActCorpusLoader


def _fixture_path() -> Path:
    return Path(
        os.environ.get(
            "BOUSSOLE_AI_ACT_FIXTURE",
            str(
                Path(__file__).resolve().parents[3]
                / "regulations"
                / "ai_act"
                / "corpus"
                / "fixture_excerpt.txt"
            ),
        )
    )


def _new_store_and_embedder() -> tuple[InMemoryVectorStore, FakeEmbedder]:
    """Empty store + fresh embedder; the indexer fills the store lazily on first call."""
    loader = AiActCorpusLoader.from_text(_fixture_path().read_text(encoding="utf-8"))
    store = InMemoryVectorStore(corpus_version=loader.corpus_version())
    return store, FakeEmbedder()


def build_default_server() -> FastMCP:
    mcp = FastMCP("boussole.retrieve_law")
    store, embedder = _new_store_and_embedder()
    retriever = HybridRetriever(store=store, embedder=embedder)
    indexed = False

    async def _ensure_indexed() -> None:
        nonlocal indexed
        if indexed:
            return
        loader = AiActCorpusLoader.from_text(_fixture_path().read_text(encoding="utf-8"))
        triples = list(loader.iter_chunks_with_scope(chunker=AiActChunkerConfig()))
        vectors = await embedder.embed_documents([t[0] for t in triples])
        rows: list[tuple[str, list[float], Citation, str | None]] = [
            (text, vector, citation, scope)
            for (text, citation, scope), vector in zip(triples, vectors, strict=True)
        ]
        await store.upsert(rows)
        indexed = True

    @mcp.tool()
    async def search(query: str, scope: str | None = None, top_k: int = 8) -> JsonDict:
        """
        Retrieve up to top_k passages from the AI Act corpus.

        Every returned passage carries citation metadata (CELEX, article,
        paragraph, annex, recital, URL, corpus_version).
        """
        await _ensure_indexed()
        result = await retrieve_law(
            RetrieveLawArgs(query=query, scope=scope, top_k=top_k),
            retriever=retriever,
        )
        return {
            "scope": result.scope,
            "passages": [passage_to_json(p) for p in result.passages],
        }

    return mcp


def main() -> None:
    mcp = build_default_server()
    mcp.run()


if __name__ == "__main__":
    main()
