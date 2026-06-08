"""
End-to-end agent runs.

CLAUDE.md plan, Phase 6 checkpoint:
  "one fixture system flows intake -> assemble_report with a grounded,
   cited output".
"""

from __future__ import annotations

import pytest

from backend.agent.errors import LowExtractionConfidence
from backend.agent.graph import run_assessment
from backend.agent.state import ActorRole, SystemProfile, Tier
from backend.agent.trace import TraceEventKind
from tests.agent.conftest import AgentEnv, initial_state

RECRUITMENT_SYSTEM_DESCRIPTION = (
    "An AI tool that filters job applications and ranks candidates for our "
    "internal recruitment pipeline. The model runs in-house. A human recruiter "
    "reviews the top three candidates per opening before any contact."
)

_RECRUITMENT_ATTRIBUTES = {
    "purpose": "Filter job applications and rank candidates for recruitment.",
    "domain": "employment",
    "deployment_context": "internal HR pipeline",
    "user_population": "job applicants",
    "autonomy_level": "human in the loop",
    "human_oversight": "human recruiter reviews top three",
    "data_types": ["resume", "application data"],
    "geography": "France",
    "is_gpai_model": False,
    "built_on_gpai": False,
    "is_safety_component": False,
    "regulated_product_legislation": None,
    "biometric": False,
    "affects_fundamental_rights": True,
    "uses_subliminal_techniques": False,
    "social_scoring": False,
    "real_time_remote_biometric_id": False,
    "emotion_recognition": False,
    "interacts_with_humans": False,
    "generates_synthetic_content": False,
    "extras": {"system_name": "Recruitment Assistant"},
}


async def test_recruitment_system_flows_intake_to_assemble_report(
    agent_env: AgentEnv,
) -> None:
    agent_env.script_extraction(RECRUITMENT_SYSTEM_DESCRIPTION, _RECRUITMENT_ATTRIBUTES)
    state = initial_state(
        RECRUITMENT_SYSTEM_DESCRIPTION,
        declared_controls=(
            "Risk management system reviewed quarterly with engineering and HR.",
            "Every model output is logged with candidate ID and timestamp.",
            "Human recruiter reviews top three before any candidate contact.",
        ),
    )
    state = state.model_copy(
        update={
            "system_profile": SystemProfile(
                description=state.system_profile.description,
                declared_controls=state.system_profile.declared_controls,
                declared_actor_role=ActorRole.PROVIDER,
                attributes=None,
            )
        }
    )

    final = await run_assessment(state, deps=agent_env.deps)

    assert final.classification is not None
    assert final.classification.tier == Tier.HIGH_RISK_ANNEX_III
    assert final.classification.fired_rule.startswith("annex_iii_4")
    assert final.confidence == 1.0  # grounding passed

    # Obligations enumerated (provider-scoped: Art. 26 is deployer-only and
    # is correctly excluded by the actor-role filter here).
    assert any(o.article_ref == "Art. 9" for o in final.obligations)
    assert any(o.article_ref == "Art. 11" for o in final.obligations)

    # Gap analysis produced findings
    assert final.gaps, "gap_analysis must produce findings"

    # Documentation drafted
    assert final.drafted_documents
    assert any(d.kind == "annex_iv" for d in final.drafted_documents)

    # Retrieved passages carry citations
    assert final.retrieved_passages
    for passage in final.retrieved_passages:
        assert passage.citation.celex_id == "32024R1689"

    # Trace events cover the whole pipeline
    event_names = {event["name"] for event in final.trace_events}
    for required in {
        "intake",
        "classify",
        "retrieve_context",
        "enumerate_obligations",
        "gap_analysis",
        "draft_docs",
        "assemble_report",
        "classification.decided",
    }:
        assert required in event_names, f"missing trace event {required!r}"

    # Grounding check fired and passed
    grounding_events = [
        e for e in final.trace_events if e["kind"] == TraceEventKind.GROUNDING_CHECK.value
    ]
    assert grounding_events
    assert any(e["name"].endswith("grounding_passed") for e in grounding_events)


_BENIGN_ATTRIBUTES = {
    **_RECRUITMENT_ATTRIBUTES,
    "purpose": "Translate technical documents between French and English for internal use.",
    "domain": "internal tooling",
    "affects_fundamental_rights": False,
}


async def test_minimal_risk_run_completes_without_retrieving_passages(
    agent_env: AgentEnv,
) -> None:
    description = (
        "Internal AI translator that converts technical documents between French "
        "and English for engineering teams. Outputs are reviewed by the original "
        "author before being shared."
    )
    agent_env.script_extraction(description, _BENIGN_ATTRIBUTES)
    final = await run_assessment(initial_state(description), deps=agent_env.deps)

    assert final.classification is not None
    assert final.classification.tier == Tier.MINIMAL
    # Minimal-risk path skips retrieval and produces no obligations or drafts
    assert final.retrieved_passages == []
    assert final.obligations == []
    assert final.drafted_documents == []


async def test_intake_low_confidence_raises_typed_failure(agent_env: AgentEnv) -> None:
    """Malformed LLM output bubbles up as LowExtractionConfidence."""
    description = "Some opaque description that the LLM will mishandle."
    rendered = agent_env.prompts.render(
        "intake_extract_attributes",
        {"system_description": description},
    )
    agent_env.fake_llm.script(rendered, "this is not json")

    with pytest.raises(LowExtractionConfidence):
        await run_assessment(initial_state(description), deps=agent_env.deps)
