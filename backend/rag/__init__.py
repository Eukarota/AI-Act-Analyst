"""RAG layer: chunking, hybrid retrieval, RRF, reranking, grounding contract."""

from backend.rag.chunking import RawSection, split_into_chunks, to_retrieved
from backend.rag.grounding import (
    Claim,
    GroundingError,
    GroundingResult,
    GroundingViolation,
    assert_grounded,
    citation_key,
)
from backend.rag.reranker import CrossEncoderReranker, NoOpReranker, Reranker
from backend.rag.retrieve import HybridRetriever, RetrievalConfig
from backend.rag.rrf import reciprocal_rank_fusion

__all__ = [
    "Claim",
    "CrossEncoderReranker",
    "GroundingError",
    "GroundingResult",
    "GroundingViolation",
    "HybridRetriever",
    "NoOpReranker",
    "RawSection",
    "Reranker",
    "RetrievalConfig",
    "assert_grounded",
    "citation_key",
    "reciprocal_rank_fusion",
    "split_into_chunks",
    "to_retrieved",
]
