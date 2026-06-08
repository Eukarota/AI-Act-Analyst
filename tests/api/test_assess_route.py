"""
/assess end-to-end via httpx ASGI: same recruitment scenario as the agent
e2e test, plus the trace round-trip.
"""

from __future__ import annotations

from tests.api.conftest import ApiEnv

RECRUITMENT_DESCRIPTION = (
    "An AI tool that filters job applications and ranks candidates for our "
    "internal recruitment pipeline. The model runs in-house. A human recruiter "
    "reviews the top three candidates per opening before any contact."
)

RECRUITMENT_ATTRIBUTES = {
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


async def test_assess_recruitment_returns_complete_report(api_env: ApiEnv) -> None:
    api_env.script_extraction(RECRUITMENT_DESCRIPTION, RECRUITMENT_ATTRIBUTES)

    response = await api_env.client.post(
        "/assess",
        json={
            "system_description": RECRUITMENT_DESCRIPTION,
            "declared_controls": [
                "Risk management system reviewed quarterly.",
                "Human recruiter reviews top three.",
            ],
            "declared_actor_role": "provider",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    report = body["report"]
    assert report["status"] == "complete"
    assert report["grounding_passed"] is True
    assert report["classification"]["tier"] == "high_risk_annex_iii"
    assert report["manifest"]["run_id"] == report["run_id"]
    assert report["manifest"]["corpus_version"].startswith("ai_act-")
    assert report["manifest"]["model_id"] == api_env.wired.deps.llm.model_id
    assert report["manifest"]["prompt_set_version"], "prompt_set_version is mandatory"
    assert report["manifest"]["rules_version"], "rules_version is mandatory"


async def test_assess_persists_trace_retrievable_via_get_trace(api_env: ApiEnv) -> None:
    api_env.script_extraction(RECRUITMENT_DESCRIPTION, RECRUITMENT_ATTRIBUTES)
    response = await api_env.client.post(
        "/assess",
        json={
            "system_description": RECRUITMENT_DESCRIPTION,
            "declared_controls": [],
            "declared_actor_role": "provider",
        },
    )
    assert response.status_code == 200
    run_id = response.json()["report"]["run_id"]

    trace_response = await api_env.client.get(f"/trace/{run_id}")
    assert trace_response.status_code == 200
    trace_body = trace_response.json()
    assert trace_body["run_id"] == run_id
    assert trace_body["schema_version"] == "1.0.0"
    event_names = {e["name"] for e in trace_body["events"]}
    for required in {
        "intake",
        "classify",
        "retrieve_context",
        "enumerate_obligations",
        "gap_analysis",
        "draft_docs",
        "assemble_report",
    }:
        assert required in event_names, f"missing trace event {required!r}"


async def test_trace_unknown_run_id_returns_404(api_env: ApiEnv) -> None:
    response = await api_env.client.get("/trace/does-not-exist")
    assert response.status_code == 404
    body = response.json()
    assert body["detail"]["code"] == "trace_not_found"


async def test_assess_short_description_rejected(api_env: ApiEnv) -> None:
    response = await api_env.client.post(
        "/assess",
        json={"system_description": "too short", "declared_controls": []},
    )
    assert response.status_code == 422  # pydantic validation


async def test_assess_low_extraction_confidence_returns_422(api_env: ApiEnv) -> None:
    """Malformed extraction surfaces as a typed failure response."""
    description = (
        "Some opaque description that the LLM will mishandle and fail to extract "
        "structured attributes from cleanly."
    )
    rendered = api_env.prompts.render(
        "intake_extract_attributes",
        {"system_description": description},
    )
    api_env.fake_llm.script(rendered, "this is not json")

    response = await api_env.client.post(
        "/assess",
        json={"system_description": description, "declared_controls": []},
    )
    assert response.status_code == 422
    body = response.json()
    report = body["report"]
    assert report["status"] == "failed"
    assert any(f["code"] == "low_extraction_confidence" for f in report["failures"]), report[
        "failures"
    ]
