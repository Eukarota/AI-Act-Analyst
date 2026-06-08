"""Adapters: concrete implementations of the ports."""

from backend.adapters.e5_embedder import MultilingualE5LargeEmbedder
from backend.adapters.fake_embedder import FakeEmbedder
from backend.adapters.fake_llm import FakeLLM
from backend.adapters.in_memory_store import InMemoryVectorStore
from backend.adapters.pgvector_store import PgVectorStore
from backend.adapters.vllm_provider import SelfHostedVLLM

__all__ = [
    "FakeEmbedder",
    "FakeLLM",
    "InMemoryVectorStore",
    "MultilingualE5LargeEmbedder",
    "PgVectorStore",
    "SelfHostedVLLM",
]
