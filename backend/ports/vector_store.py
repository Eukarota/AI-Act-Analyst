"""
Vector store port.

Default: pgvector (Phase 2). Alt adapter: Qdrant. Both implement this Protocol.
Hybrid retrieval combines a dense call to this port with a sparse call against
the same backing store (tsvector in Postgres or Qdrant payload index).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from backend.agent.state import Citation, RetrievedPassage


@runtime_checkable
class VectorStore(Protocol):
    """
    Storage + retrieval port.

    Every passage written carries a Citation. Every passage returned carries
    that same Citation. There is no path that loses citation metadata.
    """

    async def upsert(
        self,
        passages: Sequence[tuple[str, list[float], Citation, str | None]],
    ) -> None:
        """
        Index passages. Each tuple is (text, vector, citation, retrieval_scope).

        retrieval_scope is the per-regulation scope tag the agent nodes filter
        by ('art_5', 'annex_iii', 'art_50', ...). May be None for chunks that
        should be searchable across all scopes.
        """
        ...

    async def search_dense(
        self,
        query_vector: list[float],
        *,
        scope: str | None = None,
        k: int = 20,
    ) -> list[RetrievedPassage]:
        """Dense vector search, optionally scoped (e.g. 'art_5' or 'annex_iii')."""
        ...

    async def search_sparse(
        self,
        query_text: str,
        *,
        scope: str | None = None,
        k: int = 20,
    ) -> list[RetrievedPassage]:
        """Sparse (BM25 / tsvector) search over the same indexed corpus."""
        ...

    async def corpus_version(self) -> str:
        """Returns the corpus_version stamp the store was indexed under."""
        ...
