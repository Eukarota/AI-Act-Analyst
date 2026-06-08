"""
retrieve_law: hybrid retrieval over a regulation's corpus.

Inputs:
  query  (str)              the natural-language query
  scope  (str | None)       the regulation-specific scope tag, or None for
                            cross-scope retrieval (see scope_for_citation)
  top_k  (int)              max passages to return after rerank

Output:
  RetrieveLawResult         list of RetrievedPassage objects. Every passage
                            carries a Citation; nothing returned by this tool
                            is ungrounded by construction.

Citation guarantee:
  The HybridRetriever returns RetrievedPassage objects whose .citation is
  populated at index time. The grounding contract on the consumer side
  (Phase 7 report assembler) will match these citations against the claims
  in the final report.
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.agent.state import RetrievedPassage
from backend.rag.retrieve import HybridRetriever, RetrievalConfig


@dataclass(frozen=True)
class RetrieveLawArgs:
    query: str
    scope: str | None = None
    top_k: int = 8


@dataclass(frozen=True)
class RetrieveLawResult:
    passages: list[RetrievedPassage]
    scope: str | None


async def retrieve_law(
    args: RetrieveLawArgs,
    *,
    retriever: HybridRetriever,
    config: RetrievalConfig | None = None,
) -> RetrieveLawResult:
    cfg = config or RetrievalConfig(
        candidates_per_retriever=20,
        rrf_k=60,
        fused_top_n=20,
        rerank_top_k=args.top_k,
    )
    passages = await retriever.retrieve(args.query, scope=args.scope, config=cfg)
    # Citation invariant: every passage carries a non-empty celex_id by
    # virtue of the VectorStore contract (Phase 2). We assert it here to
    # catch any future adapter regression at the tool boundary.
    for passage in passages:
        if not passage.citation.celex_id:
            raise AssertionError("retrieve_law: VectorStore returned an uncited passage")
    return RetrieveLawResult(passages=passages, scope=args.scope)
