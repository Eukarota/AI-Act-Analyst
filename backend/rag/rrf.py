"""
Reciprocal Rank Fusion.

Standard formulation: score(d) = sum over rankers r of 1 / (k + rank_r(d)),
where rank is 1-indexed and absent documents contribute zero.

Per CLAUDE.md section 12.2 hybrid retrieval is mandatory and dense+sparse are
fused via RRF before the cross-encoder reranks the top-k.

We key by citation identity (citation_key) not by text, because the same
passage may surface at slightly different scores across retrievers but should
fuse to one entry.
"""

from __future__ import annotations

from collections.abc import Sequence

from backend.agent.state import RetrievedPassage
from backend.rag.grounding import citation_key

CitationKey = tuple[str, str | None, str | None, str | None, str | None]


def reciprocal_rank_fusion(
    ranked_lists: Sequence[Sequence[RetrievedPassage]],
    *,
    k: int = 60,
    top_n: int | None = None,
) -> list[RetrievedPassage]:
    """
    Fuse multiple ranked lists into a single ranked list.

    Args:
        ranked_lists: each inner list is a retriever's ranking, best first.
        k: smoothing constant. 60 is the canonical default (Cormack et al.).
        top_n: optional truncation of the fused list.

    Returns:
        Passages ordered by fused score (descending). Citation metadata is
        preserved from the first occurrence; text from the highest-scoring
        occurrence.
    """
    scores: dict[CitationKey, float] = {}
    best_passage: dict[CitationKey, RetrievedPassage] = {}
    best_score: dict[CitationKey, float] = {}

    for ranking in ranked_lists:
        for rank, passage in enumerate(ranking, start=1):
            key = citation_key(passage.citation)
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank)
            if key not in best_passage or passage.score > best_score.get(key, float("-inf")):
                best_passage[key] = passage
                best_score[key] = passage.score

    fused = sorted(scores.items(), key=lambda item: item[1], reverse=True)

    out: list[RetrievedPassage] = []
    for key, fused_score in fused:
        passage = best_passage[key]
        out.append(
            RetrievedPassage(
                text=passage.text,
                citation=passage.citation,
                score=fused_score,
                retrieval_scope=passage.retrieval_scope,
            )
        )

    if top_n is not None:
        out = out[:top_n]

    return out
