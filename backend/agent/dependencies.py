"""
AgentDependencies: explicit dependency injection for the graph nodes.

CLAUDE.md section 12.3: "Stateless service: per-request state lives in the
payload/DB, not process memory ⇒ horizontal scale". The graph nodes therefore
read everything they need from (a) the AgentState (per-request) and (b)
AgentDependencies (per-process). Building dependencies once at process start
makes it easy to swap in fakes for tests.

The class is intentionally not a config; it composes already-constructed
adapters and ports. Wiring (URLs, model IDs, corpus paths) belongs in
backend.api.factories, not here.
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.ports.llm_provider import LLMProvider
from backend.ports.regulation import Regulation
from backend.prompts.loader import PromptRegistry
from backend.rag.retrieve import HybridRetriever


@dataclass(frozen=True)
class AgentBudgets:
    """Bounded-execution caps, per CLAUDE.md section 12.3."""

    clarify_iterations: int = 3
    node_timeout_seconds: float = 60.0
    tool_call_budget: int = 50


@dataclass(frozen=True)
class AgentDependencies:
    """Composed dependencies the graph nodes consume."""

    regulation: Regulation
    llm: LLMProvider
    retriever: HybridRetriever
    prompts: PromptRegistry
    budgets: AgentBudgets = AgentBudgets()

    @property
    def model_id(self) -> str:
        return self.llm.model_id

    @property
    def corpus_version(self) -> str:
        return self.regulation.corpus_loader.corpus_version()
