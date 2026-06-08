"""Annex III standalone high-risk use case tests."""

from __future__ import annotations

import pytest

from backend.agent.state import AttributeSet, Tier
from regulations.ai_act.rules.annex_iii import evaluate


def _attrs(**kwargs: object) -> AttributeSet:
    base: dict[str, object] = {"purpose": ""}
    base.update(kwargs)
    return AttributeSet(**base)


@pytest.mark.parametrize(
    ("attrs", "expected_rule"),
    [
        (
            _attrs(biometric=True, purpose="Biometric categorisation of customers in store"),
            "annex_iii_1.biometrics_flag",
        ),
        (
            _attrs(purpose="Manage road traffic signals across the city"),
            "annex_iii_2.critical_infrastructure",
        ),
        (
            _attrs(purpose="Score student exam performance for school admission"),
            "annex_iii_3.education",
        ),
        (
            _attrs(purpose="Filter job applications and rank candidates for recruitment"),
            "annex_iii_4.employment",
        ),
        (
            _attrs(purpose="Determine creditworthiness for personal loan approval"),
            "annex_iii_5.essential_services",
        ),
        (
            _attrs(purpose="Polygraph-style lie detection for criminal investigation"),
            "annex_iii_6.law_enforcement",
        ),
        (
            _attrs(purpose="Process asylum applications at border control"),
            "annex_iii_7.migration_border",
        ),
        (
            _attrs(purpose="Support judges with court decision recommendations"),
            "annex_iii_8.justice_and_democracy",
        ),
    ],
)
def test_annex_iii_areas_each_trigger_high_risk(attrs: AttributeSet, expected_rule: str) -> None:
    match = evaluate(attrs)
    assert match is not None
    assert match.tier == Tier.HIGH_RISK_ANNEX_III
    assert match.fired_rule == expected_rule


def test_annex_iii_does_not_fire_for_real_time_remote_biometric_id() -> None:
    # That case is prohibited under Art. 5 and would have been caught upstream;
    # the biometric short-circuit here must explicitly avoid double-classifying.
    attrs = _attrs(biometric=True, real_time_remote_biometric_id=True)
    assert evaluate(attrs) is None


def test_annex_iii_does_not_fire_for_minimal_chatbot() -> None:
    attrs = _attrs(purpose="A consumer-facing weather chatbot")
    assert evaluate(attrs) is None
