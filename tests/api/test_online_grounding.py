"""
Online grounding contract: a planted ungrounded claim must be blocked.

The grounding contract is the single most load-bearing invariant in this
project (CLAUDE.md section 3). The eval and the prod /assess route call the
identical assert_grounded function; if either path stops blocking, this test
fails. The check fires inside run_assessment (assemble_report node) AND in
the API layer as a second line of defense.

We exercise the API layer by reaching into the assess runner, replacing the
classification's supporting_refs with an unsupported citation. The assemble
node catches it first; the response is HTTP 502 with the failed report.
"""

from __future__ import annotations

from unittest.mock import patch

from backend.agent.state import (
    AgentState,
    Citation,
    ClassificationResult,
    Tier,
)
from backend.api.assess_runner import AssessmentRunner
from tests.api.conftest import ApiEnv
from tests.api.test_assess_route import (
    RECRUITMENT_ATTRIBUTES,
    RECRUITMENT_DESCRIPTION,
)


def _planted_classification() -> ClassificationResult:
    fake_citation = Citation(
        celex_id="32024R1689",
        article="999",
        paragraph="z",
        lang="en",
        corpus_version="ai_act-rules",
    )
    return ClassificationResult(
        tier=Tier.HIGH_RISK_ANNEX_III,
        fired_rule="planted_ungrounded",
        supporting_refs=(fake_citation,),
        rationale="Planted by the grounding test to force a violation.",
        rules_version="ai_act-rules-v1.0.0",
    )


async def test_planted_ungrounded_claim_is_blocked(api_env: ApiEnv) -> None:
    """
    Patch AssessmentRunner.run to short-circuit after classification with a
    forged supporting_ref, then call the route. The online grounding check
    in the runner should mark the report as failed and return 502.
    """
    real_build_claims = AssessmentRunner._build_claims

    def planted_build_claims(self: AssessmentRunner, state: AgentState) -> list:  # type: ignore[type-arg]
        # Inject a planted classification into the state copy used for claims.
        if state.classification is None:
            state = state.model_copy(update={"classification": _planted_classification()})
        else:
            state = state.model_copy(
                update={
                    "classification": state.classification.model_copy(
                        update={"supporting_refs": _planted_classification().supporting_refs}
                    )
                }
            )
        return real_build_claims(self, state)

    api_env.script_extraction(RECRUITMENT_DESCRIPTION, RECRUITMENT_ATTRIBUTES)

    with patch.object(AssessmentRunner, "_build_claims", planted_build_claims):
        response = await api_env.client.post(
            "/assess",
            json={
                "system_description": RECRUITMENT_DESCRIPTION,
                "declared_controls": [],
                "declared_actor_role": "provider",
            },
        )

    assert response.status_code == 502, response.text
    body = response.json()
    report = body["report"]
    assert report["status"] == "failed"
    assert report["grounding_passed"] is False
    assert any(
        f["code"] in {"grounding_failed", "online_grounding_failed"} for f in report["failures"]
    ), report["failures"]
