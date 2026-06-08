"""
Phase 1 smoke test (CLAUDE.md plan, Phase 1 checkpoint).

Asserts the foundations every later phase depends on:
  - AgentState instantiates with a SystemProfile
  - The prompt registry loads, renders a template, and pins a prompt_set_version
  - FakeLLM round-trips a deterministic completion through the LLMProvider port
  - TraceEmitter emits a TraceEvent matching the schema
  - The AI Act timeline loads with sourced dates
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from backend.adapters.fake_embedder import FakeEmbedder
from backend.adapters.fake_llm import FakeLLM
from backend.agent.state import (
    AgentState,
    RunManifest,
    SystemProfile,
)
from backend.agent.trace import TraceEmitter, TraceEvent, TraceEventKind, hash_payload
from backend.ports.llm_provider import LLMProvider
from backend.prompts.loader import PromptRegistry, default_registry
from regulations.ai_act import AiActRegulation


def test_agent_state_instantiates_with_system_profile() -> None:
    state = AgentState(system_profile=SystemProfile(description="A CV-screening tool for HR."))
    assert state.system_profile.description.startswith("A CV-screening")
    assert state.run_id
    assert state.classification is None
    assert state.confidence == 0.0
    assert state.trace_events == []


def test_run_manifest_coerces_timezone() -> None:
    manifest = RunManifest(
        run_id="abc",
        corpus_version="ai_act-2024-07-12",
        model_id="fake-llm-v0",
        embedding_model="fake-embedder-v0",
        prompt_set_version="deadbeefdeadbeef",
        rules_version="rules-v0",
        timestamp=datetime(2026, 6, 8),
    )
    assert manifest.timestamp.tzinfo is UTC


def test_prompt_registry_renders_and_pins_version() -> None:
    registry: PromptRegistry = default_registry()
    assert "intake_extract_attributes" in registry.names()
    rendered = registry.render(
        "intake_extract_attributes",
        {"system_description": "A chatbot that answers tax questions."},
    )
    assert "tax questions" in rendered
    version_a = registry.prompt_set_version()
    version_b = registry.prompt_set_version()
    assert version_a == version_b
    assert len(version_a) == 16


@pytest.mark.asyncio
async def test_fake_llm_round_trips_through_protocol() -> None:
    llm: LLMProvider = FakeLLM(scripted={"ping": "pong"})
    response = await llm.complete("ping")
    assert response.text == "pong"
    assert response.model_id == "fake-llm-v0"
    assert response.usage.tokens_out >= 0


@pytest.mark.asyncio
async def test_fake_embedder_returns_stable_vectors() -> None:
    embedder = FakeEmbedder()
    a = await embedder.embed_query("hello")
    b = await embedder.embed_query("hello")
    c = await embedder.embed_query("goodbye")
    assert a == b
    assert a != c
    assert len(a) == embedder.dimension


def test_trace_emitter_emits_events_matching_schema() -> None:
    sink: list[dict[str, object]] = []
    emitter = TraceEmitter(run_id="run-001", sink=sink)
    with emitter.node("phase1_smoke", attributes={"phase": 1}):
        emitter.emit(
            TraceEventKind.LLM_CALL,
            "fake_call",
            input_hash=hash_payload({"prompt": "ping"}),
            output_hash=hash_payload({"text": "pong"}),
            tokens_in=1,
            tokens_out=1,
            model_id="fake-llm-v0",
        )
    assert len(sink) >= 3
    parsed = [TraceEvent.model_validate(event) for event in sink]
    kinds = [event.kind for event in parsed]
    assert TraceEventKind.NODE_START in kinds
    assert TraceEventKind.LLM_CALL in kinds
    assert TraceEventKind.NODE_END in kinds
    assert all(event.run_id == "run-001" for event in parsed)


def test_ai_act_timeline_loads_sourced_dates() -> None:
    reg = AiActRegulation()
    milestones = reg.timeline.all_milestones()
    assert "general_application" in milestones
    entry = milestones["general_application"]
    assert entry["date"] == "2026-08-02"
    assert "Art. 113" in entry["source"]
    assert reg.timeline.applicable_on("prohibitions_apply") == "2025-02-02"


def test_pending_phase_components_raise_clearly() -> None:
    reg = AiActRegulation()
    with pytest.raises(Exception) as exc:
        _ = reg.document_templates
    assert "Phase 5" in str(exc.value)
