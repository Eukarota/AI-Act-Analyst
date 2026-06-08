"""
Process-local LRU cache for retrieval results.

CLAUDE.md section 12.4: "retrieval cache keyed by corpus_version; semantic
cache for repeated sub-queries". This module gives both a key (so a corpus
re-index invalidates everything by design) and an observation point for the
cache-hit counter the Phase 10 telemetry surface exposes.

The cache is a plain OrderedDict LRU. It is intentionally process-local:
when the API horizontally scales, each worker keeps its own cache. A shared
Redis layer is a later optimisation; the worker-local cache already cuts
re-retrieval inside a single assessment (the agent retrieves several scoped
queries against the same corpus) and dominates the steady-state cost.
"""

from __future__ import annotations

import hashlib
from collections import OrderedDict
from dataclasses import dataclass

from backend.agent.state import RetrievedPassage
from backend.rag.retrieve import HybridRetriever, RetrievalConfig


def _query_hash(query: str) -> str:
    return hashlib.sha256(query.strip().lower().encode("utf-8")).hexdigest()[:16]


@dataclass
class CacheStats:
    """Counters the Prometheus surface scrapes."""

    hits: int = 0
    misses: int = 0
    evictions: int = 0
    invalidations: int = 0

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return (self.hits / total) if total else 0.0


class CachingRetriever(HybridRetriever):
    """
    Drop-in HybridRetriever that wraps another retriever with an LRU cache.

    Cache key is (corpus_version, scope, sha256(query)). corpus_version in
    the key means a re-index invalidates everything by construction; the
    explicit invalidate() is reserved for forced flushes (a prompt rollback
    or a manual operator action).

    Inherits from HybridRetriever so existing call sites that are typed
    against the concrete class accept it without changes; the inner store
    and embedder are reused via the parent constructor.
    """

    def __init__(
        self,
        *,
        inner: HybridRetriever,
        corpus_version: str,
        max_entries: int = 512,
    ) -> None:
        super().__init__(store=inner.store, embedder=inner.embedder, reranker=inner.reranker)
        self._inner = inner
        self._corpus_version = corpus_version
        self._max_entries = max_entries
        self._entries: OrderedDict[tuple[str, str | None, str], list[RetrievedPassage]] = (
            OrderedDict()
        )
        self.stats = CacheStats()

    @property
    def corpus_version(self) -> str:
        return self._corpus_version

    def invalidate(self, *, corpus_version: str | None = None) -> None:
        """Drop the cache. Optionally rebind to a new corpus_version."""
        if corpus_version is not None:
            self._corpus_version = corpus_version
        self._entries.clear()
        self.stats.invalidations += 1

    async def retrieve(
        self,
        query: str,
        *,
        scope: str | None,
        config: RetrievalConfig | None = None,
    ) -> list[RetrievedPassage]:
        key = (self._corpus_version, scope, _query_hash(query))
        cached = self._entries.get(key)
        if cached is not None:
            self._entries.move_to_end(key)
            self.stats.hits += 1
            return list(cached)

        self.stats.misses += 1
        passages = await self._inner.retrieve(query, scope=scope, config=config)
        self._entries[key] = list(passages)
        if len(self._entries) > self._max_entries:
            self._entries.popitem(last=False)
            self.stats.evictions += 1
        return passages
