"""
Shared fixtures for agent end-to-end tests.

Each test indexes the committed AI Act fixture into an InMemoryVectorStore
via the same code path the production indexer uses, then wires the agent
dependencies with FakeLLM scripted for the test's scenario.
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from backend.adapters.fake_embedder import FakeEmbedder
from backend.adapters.fake_llm import FakeLLM
from backend.adapters.in_memory_store import InMemoryVectorStore
from backend.agent.dependencies import AgentBudgets, AgentDependencies
from backend.agent.state import AgentState, Citation, SystemProfile
from backend.prompts.loader import PromptRegistry, default_registry
from backend.rag.retrieve import HybridRetriever
from regulations.ai_act import AiActRegulation
from regulations.ai_act.corpus.loader import AiActChunkerConfig, AiActCorpusLoader

FIXTURE_PATH = (
    Path(__file__).resolve().parents[2]
    / "regulations"
    / "ai_act"
    / "corpus"
    / "fixture_excerpt.txt"
)


@dataclass(frozen=True)
class AgentEnv:
    deps: AgentDependencies
    fake_llm: FakeLLM
    prompts: PromptRegistry

    def script_extraction(self, system_description: str, attributes: dict[str, Any]) -> None:
        """Pre-script the intake LLM call for `system_description`."""
        rendered = self.prompts.render(
            "intake_extract_attributes",
            {"system_description": system_description},
        )
        self.fake_llm.script(rendered, json.dumps(attributes))


@pytest.fixture()
async def agent_env() -> AgentEnv:
    text = FIXTURE_PATH.read_text(encoding="utf-8")
    loader = AiActCorpusLoader.from_text(text)
    triples = list(loader.iter_chunks_with_scope(chunker=AiActChunkerConfig()))
    embedder = FakeEmbedder()
    store = InMemoryVectorStore(corpus_version=loader.corpus_version())
    vectors = await embedder.embed_documents([t[0] for t in triples])
    rows: list[tuple[str, list[float], Citation, str | None]] = [
        (chunk_text, vector, citation, scope)
        for (chunk_text, citation, scope), vector in zip(triples, vectors, strict=True)
    ]
    await store.upsert(rows)
    retriever = HybridRetriever(store=store, embedder=embedder)

    regulation = AiActRegulation(corpus_loader=loader)
    fake_llm = FakeLLM()
    prompts = default_registry()
    deps = AgentDependencies(
        regulation=regulation,
        llm=fake_llm,
        retriever=retriever,
        prompts=prompts,
        budgets=AgentBudgets(clarify_iterations=3, node_timeout_seconds=10.0),
    )
    return AgentEnv(deps=deps, fake_llm=fake_llm, prompts=prompts)


def initial_state(description: str, declared_controls: tuple[str, ...] = ()) -> AgentState:
    return AgentState(
        system_profile=SystemProfile(
            description=description, declared_controls=list(declared_controls)
        )
    )


# Convenience helper used across tests
RunAssessment = Callable[[AgentState, AgentDependencies], Awaitable[AgentState]]
