"""
API test fixtures.

We build a WiredApp with InMemoryRunStore + FakeLLM + InMemoryVectorStore so
no Postgres, no LLM, no Docker. ASGITransport in httpx 0.28 does not drive
the lifespan automatically, so we open it explicitly via
`app.router.lifespan_context(app)` before issuing requests.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from backend.adapters.fake_embedder import FakeEmbedder
from backend.adapters.fake_llm import FakeLLM
from backend.adapters.in_memory_store import InMemoryVectorStore
from backend.agent.dependencies import AgentBudgets, AgentDependencies
from backend.agent.state import Citation
from backend.api.app import create_app
from backend.api.factories import WiredApp
from backend.api.run_store import InMemoryRunStore
from backend.api.settings import ApiSettings
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


@dataclass
class ApiEnv:
    app: FastAPI
    wired: WiredApp
    fake_llm: FakeLLM
    prompts: PromptRegistry
    client: httpx.AsyncClient

    def script_extraction(self, system_description: str, attributes: dict[str, Any]) -> None:
        rendered = self.prompts.render(
            "intake_extract_attributes",
            {"system_description": system_description},
        )
        self.fake_llm.script(rendered, json.dumps(attributes))


async def _build_wired() -> tuple[FastAPI, WiredApp, FakeLLM, PromptRegistry]:
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
    run_store = InMemoryRunStore()
    settings = ApiSettings(use_in_memory_store=True, log_level="WARNING")
    wired = WiredApp(settings=settings, deps=deps, run_store=run_store)

    app = create_app(wired=wired)
    return app, wired, fake_llm, prompts


@pytest.fixture()
async def api_env() -> AsyncIterator[ApiEnv]:
    app, wired, fake_llm, prompts = await _build_wired()
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as client,
    ):
        yield ApiEnv(app=app, wired=wired, fake_llm=fake_llm, prompts=prompts, client=client)
