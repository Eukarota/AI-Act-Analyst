"""
intfloat/multilingual-e5-large embedder.

Self-hosted via sentence-transformers; the model weights live on local disk
once downloaded. e5-large outputs 1024-dim vectors and is multilingual
(handles FR + EN, which matches the corpus).

E5 expects "query: ..." and "passage: ..." prefixes; we add them inside the
adapter so callers do not have to remember.

The model is lazy-loaded so importing this module is cheap. Production wiring
warms it at startup; tests should prefer FakeEmbedder.
"""

from __future__ import annotations

from collections.abc import Sequence


class MultilingualE5LargeEmbedder:
    model_id: str = "intfloat/multilingual-e5-large"
    dimension: int = 1024

    def __init__(self, model_id: str | None = None) -> None:
        if model_id:
            self.model_id = model_id
        self._model: object | None = None

    def _load(self) -> object:
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_id)
        return self._model

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        model = self._load()
        prefixed = [f"passage: {t}" for t in texts]
        vectors = model.encode(prefixed, normalize_embeddings=True)  # type: ignore[attr-defined]
        return [list(map(float, v)) for v in vectors]

    async def embed_query(self, text: str) -> list[float]:
        model = self._load()
        vectors = model.encode([f"query: {text}"], normalize_embeddings=True)  # type: ignore[attr-defined]
        return [float(x) for x in vectors[0]]
