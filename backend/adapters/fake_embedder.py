"""Deterministic hash-based embedder for tests. Returns stable vectors."""

from __future__ import annotations

import hashlib
from collections.abc import Sequence


class FakeEmbedder:
    model_id: str = "fake-embedder-v0"
    dimension: int = 64

    @staticmethod
    def _vec(text: str, dim: int) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        # Stretch digest deterministically to dim floats in [-1, 1].
        out: list[float] = []
        i = 0
        while len(out) < dim:
            b = digest[i % len(digest)]
            out.append((b / 127.5) - 1.0)
            i += 1
        return out

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._vec(t, self.dimension) for t in texts]

    async def embed_query(self, text: str) -> list[float]:
        return self._vec(text, self.dimension)
