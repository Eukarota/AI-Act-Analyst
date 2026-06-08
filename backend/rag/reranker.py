"""
Cross-encoder reranker.

Default model: BAAI/bge-reranker-v2-m3 (multilingual, FR/EN). Sentence-Transformers
loads it on first use; this module wraps that call behind a Protocol so tests
can swap in NoOpReranker without the 500 MB model download.

CLAUDE.md section 12.2: the fully assembled context for every LLM call is
captured in the trace, so we keep top-k modest (default 8 after rerank) and
preserve scores for observability.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from backend.agent.state import RetrievedPassage


@runtime_checkable
class Reranker(Protocol):
    model_id: str

    async def rerank(
        self,
        query: str,
        candidates: Sequence[RetrievedPassage],
        *,
        top_k: int,
    ) -> list[RetrievedPassage]: ...


class NoOpReranker:
    """Identity reranker. Used in unit tests; does not require a model download."""

    model_id: str = "noop-reranker-v0"

    async def rerank(
        self,
        query: str,
        candidates: Sequence[RetrievedPassage],
        *,
        top_k: int,
    ) -> list[RetrievedPassage]:
        return list(candidates[:top_k])


class CrossEncoderReranker:
    """
    BGE cross-encoder reranker.

    Loads sentence-transformers lazily so importing this module is free; the
    model is only fetched when rerank() is called for the first time.
    """

    def __init__(self, model_id: str = "BAAI/bge-reranker-v2-m3") -> None:
        self.model_id = model_id
        self._model: object | None = None

    def _load(self) -> object:
        if self._model is None:
            from sentence_transformers import CrossEncoder  # local import to keep startup cheap

            self._model = CrossEncoder(self.model_id)
        return self._model

    async def rerank(
        self,
        query: str,
        candidates: Sequence[RetrievedPassage],
        *,
        top_k: int,
    ) -> list[RetrievedPassage]:
        if not candidates:
            return []
        model = self._load()
        pairs = [(query, p.text) for p in candidates]
        # sentence-transformers' CrossEncoder.predict is synchronous; the call
        # is short enough at top_k <= 50 that we accept the blocking call.
        scores = model.predict(pairs)  # type: ignore[attr-defined]
        scored = sorted(zip(candidates, scores, strict=True), key=lambda x: x[1], reverse=True)
        out: list[RetrievedPassage] = []
        for passage, score in scored[:top_k]:
            out.append(
                RetrievedPassage(
                    text=passage.text,
                    citation=passage.citation,
                    score=float(score),
                    retrieval_scope=passage.retrieval_scope,
                )
            )
        return out
