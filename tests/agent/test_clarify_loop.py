"""Bounded clarify loop tests."""

from __future__ import annotations

from typing import Any

from backend.agent.graph import run_assessment
from backend.agent.state import Tier
from tests.agent.conftest import AgentEnv, initial_state

_SPARSE_ATTRIBUTES: dict[str, Any] = {
    "purpose": "Filter job applications and rank candidates for recruitment.",
    "domain": "employment",
    "deployment_context": None,  # missing -> clarify trigger
    "user_population": None,  # missing -> clarify trigger
    "autonomy_level": None,
    "human_oversight": None,  # missing -> clarify trigger
    "data_types": [],
    "geography": None,
    "is_gpai_model": False,
    "built_on_gpai": False,
    "is_safety_component": False,
    "regulated_product_legislation": None,
    "biometric": False,
    "affects_fundamental_rights": False,
    "uses_subliminal_techniques": False,
    "social_scoring": False,
    "real_time_remote_biometric_id": False,
    "emotion_recognition": False,
    "interacts_with_humans": False,
    "generates_synthetic_content": False,
    "extras": {},
}


async def test_clarify_loop_is_bounded_by_budget(agent_env: AgentEnv) -> None:
    """
    A description producing sparse attributes triggers clarify; the loop
    re-enters intake up to budget.clarify_iterations and then proceeds.
    """
    description = "An AI tool that filters job applications and ranks candidates."
    agent_env.script_extraction(description, _SPARSE_ATTRIBUTES)

    final = await run_assessment(initial_state(description), deps=agent_env.deps)

    # clarify increments to the budget cap; afterwards proceeds with what we have.
    assert final.clarification_iterations == agent_env.deps.budgets.clarify_iterations
    # The classification still ran (we proceed despite incomplete clarification).
    assert final.classification is not None
    assert final.classification.tier == Tier.HIGH_RISK_ANNEX_III
    # Pending clarification questions are recorded for the UI to surface.
    assert final.clarification_questions, "questions accumulated through clarify loop"
