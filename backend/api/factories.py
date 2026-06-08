"""
Wire ApiSettings into concrete AgentDependencies + RunStore.

Lives here, not in agent.dependencies, so the agent core stays free of
config concerns (CLAUDE.md section 12.5 adaptability: the same agent runs
unmodified under different sovereignty postures).
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.adapters.fake_embedder import FakeEmbedder
from backend.adapters.in_memory_store import InMemoryVectorStore
from backend.adapters.vllm_provider import SelfHostedVLLM
from backend.agent.dependencies import AgentBudgets, AgentDependencies
from backend.agent.state import Citation
from backend.api.run_store import InMemoryRunStore, PostgresRunStore, RunStore
from backend.api.settings import ApiSettings
from backend.prompts.loader import default_registry
from backend.rag.retrieval_cache import CachingRetriever
from backend.rag.retrieve import HybridRetriever
from regulations.ai_act import AiActRegulation
from regulations.ai_act.corpus.loader import AiActChunkerConfig, AiActCorpusLoader


@dataclass
class WiredApp:
    """Everything the routes need. Built once at app startup."""

    settings: ApiSettings
    deps: AgentDependencies
    run_store: RunStore

    async def aclose(self) -> None:
        llm = self.deps.llm
        aclose = getattr(llm, "aclose", None)
        if callable(aclose):
            await aclose()
        store_close = getattr(self.run_store, "close", None)
        if callable(store_close):
            await store_close()


async def build_wired_app(settings: ApiSettings | None = None) -> WiredApp:
    """Compose deps + run store from env. Heavy work happens here, not in routes."""
    cfg = settings or ApiSettings()

    text = cfg.fixture_path.read_text(encoding="utf-8")
    loader = AiActCorpusLoader.from_text(text)

    embedder = FakeEmbedder()
    store = InMemoryVectorStore(corpus_version=loader.corpus_version())
    triples = list(loader.iter_chunks_with_scope(chunker=AiActChunkerConfig()))
    vectors = await embedder.embed_documents([t[0] for t in triples])
    rows: list[tuple[str, list[float], Citation, str | None]] = [
        (chunk_text, vector, citation, scope)
        for (chunk_text, citation, scope), vector in zip(triples, vectors, strict=True)
    ]
    await store.upsert(rows)
    base_retriever = HybridRetriever(store=store, embedder=embedder)
    retriever = CachingRetriever(
        inner=base_retriever,
        corpus_version=loader.corpus_version(),
        max_entries=512,
    )

    llm = SelfHostedVLLM(
        base_url=cfg.llm_url,
        model_id=cfg.llm_model,
        api_key=cfg.llm_api_key,
        timeout_seconds=cfg.llm_timeout_seconds,
    )

    regulation = AiActRegulation(corpus_loader=loader)
    prompts = default_registry()
    deps = AgentDependencies(
        regulation=regulation,
        llm=llm,
        retriever=retriever,
        prompts=prompts,
        budgets=AgentBudgets(),
    )

    run_store: RunStore
    if cfg.use_in_memory_store:
        run_store = InMemoryRunStore()
    else:
        pg = PostgresRunStore(cfg.database_url)
        await pg.connect()
        run_store = pg

    return WiredApp(settings=cfg, deps=deps, run_store=run_store)
