"""
Hybrid retrieval orchestrator.

Pipeline per CLAUDE.md section 12.2:

  query
    -> dense (Embedder + VectorStore.search_dense)
    -> sparse (VectorStore.search_sparse)  (RRF-fused with dense)
    -> reranker (cross-encoder, top_k <= 8)
    -> Art. 3 defined-terms injection (caller's responsibility, not here)

Scope is mandatory: each agent node passes the scope ('art_5', 'annex_iii',
'art_50', etc.) so retrieval is bounded. There is no global pass.

The fully-assembled context that the caller will feed to the LLM is the
return value; the trace captures it verbatim (the call site is responsible
for emitting the RETRIEVAL event with that context).
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.agent.state import RetrievedPassage
from backend.ports.embedder import Embedder
from backend.ports.vector_store import VectorStore
from backend.rag.reranker import NoOpReranker, Reranker
from backend.rag.rrf import reciprocal_rank_fusion


@dataclass(frozen=True)
class RetrievalConfig:
    """Per-call retrieval knobs. Sensible defaults; tune from the agent node."""

    candidates_per_retriever: int = 20
    rrf_k: int = 60
    fused_top_n: int = 40
    rerank_top_k: int = 8


class HybridRetriever:
    """
    Dense + sparse + RRF + cross-encoder rerank.

    Reranker defaults to NoOpReranker so unit tests do not download a model;
    production wiring should pass CrossEncoderReranker explicitly.
    """

    def __init__(
        self,
        *,
        store: VectorStore,
        embedder: Embedder,
        reranker: Reranker | None = None,
    ) -> None:
        self.store = store
        self.embedder = embedder
        self.reranker: Reranker = reranker or NoOpReranker()

    async def retrieve(
        self,
        query: str,
        *,
        scope: str | None,
        config: RetrievalConfig | None = None,
    ) -> list[RetrievedPassage]:
        cfg = config or RetrievalConfig()

        query_vector = await self.embedder.embed_query(query)
        dense = await self.store.search_dense(
            query_vector, scope=scope, k=cfg.candidates_per_retriever
        )
        sparse = await self.store.search_sparse(query, scope=scope, k=cfg.candidates_per_retriever)

        fused = reciprocal_rank_fusion([dense, sparse], k=cfg.rrf_k, top_n=cfg.fused_top_n)
        return await self.reranker.rerank(query, fused, top_k=cfg.rerank_top_k)
