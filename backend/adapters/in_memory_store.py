"""
In-memory VectorStore for unit tests and offline smoke runs.

Mirrors the PgVectorStore semantics:
  - dense search: cosine similarity over passage vectors
  - sparse search: BM25 over passage text
  - scope filter: matches passage.retrieval_scope exactly when provided

Used by the Phase 2 smoke test so the checkpoint criterion ("5 sample queries
return cited passages") can be verified without Docker. The PgVectorStore is
exercised behind the 'integration' marker.
"""

from __future__ import annotations

import math
import re
from collections.abc import Sequence
from dataclasses import dataclass

from rank_bm25 import BM25Okapi

from backend.agent.state import Citation, RetrievedPassage

_TOKEN_RE = re.compile(r"[A-Za-zÀ-ÿ0-9]+")


@dataclass
class _Indexed:
    text: str
    vector: list[float]
    citation: Citation
    scope: str | None


def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def _tokenize(text: str) -> list[str]:
    """Punctuation-stripping tokenizer; mirrors Postgres tsvector behaviour closely enough for tests."""
    return [m.group(0).lower() for m in _TOKEN_RE.finditer(text)]


class InMemoryVectorStore:
    """VectorStore implementation that keeps everything in process memory."""

    def __init__(self, *, corpus_version: str = "in-memory-v0") -> None:
        self._items: list[_Indexed] = []
        self._corpus_version = corpus_version
        self._bm25: BM25Okapi | None = None
        self._bm25_tokens: list[list[str]] = []

    async def upsert(
        self,
        passages: Sequence[tuple[str, list[float], Citation, str | None]],
    ) -> None:
        for text, vector, citation, scope in passages:
            self._items.append(_Indexed(text=text, vector=vector, citation=citation, scope=scope))
        self._rebuild_bm25()

    def _rebuild_bm25(self) -> None:
        self._bm25_tokens = [_tokenize(item.text) for item in self._items]
        self._bm25 = BM25Okapi(self._bm25_tokens) if self._bm25_tokens else None

    def _match_scope(self, item: _Indexed, scope: str | None) -> bool:
        if scope is None:
            return True
        if item.scope is None:
            return False
        return item.scope == scope

    async def search_dense(
        self,
        query_vector: list[float],
        *,
        scope: str | None = None,
        k: int = 20,
    ) -> list[RetrievedPassage]:
        candidates = [item for item in self._items if self._match_scope(item, scope)]
        scored = [(item, _cosine(query_vector, item.vector)) for item in candidates]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [
            RetrievedPassage(
                text=item.text, citation=item.citation, score=score, retrieval_scope=item.scope
            )
            for item, score in scored[:k]
        ]

    async def search_sparse(
        self,
        query_text: str,
        *,
        scope: str | None = None,
        k: int = 20,
    ) -> list[RetrievedPassage]:
        if self._bm25 is None or not self._items:
            return []
        tokens = _tokenize(query_text)
        if not tokens:
            return []
        scores = self._bm25.get_scores(tokens)
        order = sorted(range(len(self._items)), key=lambda i: scores[i], reverse=True)
        out: list[RetrievedPassage] = []
        for idx in order:
            score = float(scores[idx])
            # Mirror Postgres `text_search @@ plainto_tsquery(...)`: a row
            # without any matching term is not a hit, even if BM25 would
            # arithmetically still rank it. RRF assumes rank carries signal.
            if score <= 0.0:
                break
            item = self._items[idx]
            if not self._match_scope(item, scope):
                continue
            out.append(
                RetrievedPassage(
                    text=item.text,
                    citation=item.citation,
                    score=score,
                    retrieval_scope=item.scope,
                )
            )
            if len(out) >= k:
                break
        return out

    async def corpus_version(self) -> str:
        return self._corpus_version
