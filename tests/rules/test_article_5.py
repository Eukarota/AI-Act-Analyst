"""Table-driven Art. 5 prohibition tests."""

from __future__ import annotations

import pytest

from backend.agent.state import AttributeSet, Tier
from regulations.ai_act.rules.article_5 import evaluate


def _attrs(**kwargs: object) -> AttributeSet:
    base: dict[str, object] = {"purpose": "default test purpose"}
    base.update(kwargs)
    return AttributeSet(**base)


@pytest.mark.parametrize(
    ("attrs", "expected_rule"),
    [
        (
            _attrs(uses_subliminal_techniques=True),
            "art_5_1_a.subliminal_or_manipulative",
        ),
        (
            _attrs(purpose="System designed to exploit vulnerabilities of elderly users"),
            "art_5_1_b.exploit_vulnerabilities",
        ),
        (
            _attrs(social_scoring=True),
            "art_5_1_c.social_scoring",
        ),
        (
            _attrs(purpose="Predictive policing for repeat offenders"),
            "art_5_1_d.predictive_policing",
        ),
        (
            _attrs(
                biometric=True,
                purpose="Build a facial recognition database via untargeted scraping",
            ),
            "art_5_1_e.facial_recognition_db_scraping",
        ),
        (
            _attrs(
                emotion_recognition=True,
                purpose="Monitor workplace stress via emotion recognition",
                deployment_context="workplace",
            ),
            "art_5_1_f.emotion_recognition_workplace_or_education",
        ),
        (
            _attrs(
                biometric=True,
                purpose="Infer ethnic origin and political opinion from facial features",
            ),
            "art_5_1_g.biometric_categorisation_sensitive",
        ),
        (
            _attrs(real_time_remote_biometric_id=True),
            "art_5_1_h.real_time_remote_biometric_id",
        ),
    ],
)
def test_article_5_matches_fire_with_prohibited_tier(
    attrs: AttributeSet, expected_rule: str
) -> None:
    match = evaluate(attrs)
    assert match is not None, f"expected match for rule {expected_rule}"
    assert match.tier == Tier.PROHIBITED
    assert match.fired_rule == expected_rule
    assert match.supporting_refs, "Art. 5 matches must carry at least one citation"


def test_article_5_returns_none_for_benign_attributes() -> None:
    attrs = _attrs(purpose="Translate documents between French and English for internal use")
    assert evaluate(attrs) is None
