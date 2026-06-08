"""classify_risk unit tests."""

from __future__ import annotations

import json

import pytest

from backend.adapters.fake_llm import FakeLLM
from backend.agent.state import Tier
from backend.mcp_servers.classify_risk import (
    AttributeExtractionError,
    ClassifyRiskArgs,
    classify_risk,
)
from backend.prompts.loader import default_registry
from regulations.ai_act.rules import AiActRules

SYSTEM_DESCRIPTION = "An AI tool that filters job applications and ranks candidates."

_CLEAN_EXTRACTION = {
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
    "extras": {},
}


def _scripted_llm(text: str) -> FakeLLM:
    registry = default_registry()
    rendered = registry.render(
        "intake_extract_attributes",
        {"system_description": SYSTEM_DESCRIPTION},
    )
    return FakeLLM(scripted={rendered: text})


async def test_classify_risk_extracts_and_classifies_high_risk() -> None:
    llm = _scripted_llm(json.dumps(_CLEAN_EXTRACTION))
    result = await classify_risk(
        ClassifyRiskArgs(system_description=SYSTEM_DESCRIPTION),
        llm=llm,
        rules=AiActRules(),
        prompts=default_registry(),
    )
    assert result.classification.tier == Tier.HIGH_RISK_ANNEX_III
    assert result.classification.fired_rule.startswith("annex_iii_4")
    assert result.attributes.purpose.startswith("Filter")


async def test_classify_risk_handles_markdown_fenced_json() -> None:
    fenced = "```json\n" + json.dumps(_CLEAN_EXTRACTION) + "\n```"
    llm = _scripted_llm(fenced)
    result = await classify_risk(
        ClassifyRiskArgs(system_description=SYSTEM_DESCRIPTION),
        llm=llm,
        rules=AiActRules(),
        prompts=default_registry(),
    )
    assert result.classification.tier == Tier.HIGH_RISK_ANNEX_III


async def test_classify_risk_declared_attributes_override_llm() -> None:
    llm = _scripted_llm(json.dumps({**_CLEAN_EXTRACTION, "social_scoring": False}))
    result = await classify_risk(
        ClassifyRiskArgs(
            system_description=SYSTEM_DESCRIPTION,
            declared_attributes={"social_scoring": True},
        ),
        llm=llm,
        rules=AiActRules(),
        prompts=default_registry(),
    )
    assert result.classification.tier == Tier.PROHIBITED
    assert "social_scoring" in result.classification.fired_rule


async def test_classify_risk_rejects_malformed_response() -> None:
    llm = _scripted_llm("this is not json at all, sorry")
    with pytest.raises(AttributeExtractionError):
        await classify_risk(
            ClassifyRiskArgs(system_description=SYSTEM_DESCRIPTION),
            llm=llm,
            rules=AiActRules(),
            prompts=default_registry(),
        )


async def test_classify_risk_handles_prose_wrapped_json() -> None:
    wrapped = f"Sure, here is the extracted JSON: {json.dumps(_CLEAN_EXTRACTION)} hope this helps."
    llm = _scripted_llm(wrapped)
    result = await classify_risk(
        ClassifyRiskArgs(system_description=SYSTEM_DESCRIPTION),
        llm=llm,
        rules=AiActRules(),
        prompts=default_registry(),
    )
    assert result.classification.tier == Tier.HIGH_RISK_ANNEX_III
