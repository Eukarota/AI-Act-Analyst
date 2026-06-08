"""Embedder port. Default adapter: multilingual-e5-large self-hosted (Phase 2)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable


@runtime_checkable
class Embedder(Protocol):
    """
    Embedding port.

    Implementations must declare model_id, the embedding dimensionality, and
    whether they pool sentence vectors at index time or query time.
    """

    model_id: str
    dimension: int

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]: ...

    async def embed_query(self, text: str) -> list[float]: ...
