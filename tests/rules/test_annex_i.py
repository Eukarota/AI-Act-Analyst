"""Annex I high-risk product tests."""

from __future__ import annotations

from backend.agent.state import AttributeSet, Tier
from regulations.ai_act.rules.annex_i import evaluate


def _attrs(**kwargs: object) -> AttributeSet:
    base: dict[str, object] = {"purpose": "default"}
    base.update(kwargs)
    return AttributeSet(**base)


def test_annex_i_machinery_safety_component() -> None:
    attrs = _attrs(
        purpose="Vision-based emergency stop for industrial robot",
        is_safety_component=True,
        regulated_product_legislation="Machinery Regulation (EU) 2023/1230",
    )
    match = evaluate(attrs)
    assert match is not None
    assert match.tier == Tier.HIGH_RISK_ANNEX_I
    assert match.fired_rule == "annex_i.safety_component_of_regulated_product"
    assert any(ref.annex_ref == "I" for ref in match.supporting_refs)


def test_annex_i_medical_device_safety_component() -> None:
    attrs = _attrs(
        purpose="AI-assisted diagnostic flag for radiology workstation",
        is_safety_component=True,
        regulated_product_legislation="Medical Devices Regulation (EU) 2017/745",
    )
    match = evaluate(attrs)
    assert match is not None
    assert match.tier == Tier.HIGH_RISK_ANNEX_I


def test_annex_i_unknown_legislation_still_triggers_with_lower_confidence() -> None:
    attrs = _attrs(
        purpose="Some safety thing",
        is_safety_component=True,
        regulated_product_legislation="Some 2099 fictional product directive",
    )
    match = evaluate(attrs)
    assert match is not None
    assert match.tier == Tier.HIGH_RISK_ANNEX_I
    assert match.fired_rule == "annex_i.safety_component_unknown_legislation"
    assert match.confidence < 1.0


def test_annex_i_not_safety_component_does_not_trigger() -> None:
    attrs = _attrs(
        purpose="A standalone chatbot",
        is_safety_component=False,
        regulated_product_legislation="Machinery Regulation (EU) 2023/1230",
    )
    assert evaluate(attrs) is None


def test_annex_i_safety_component_without_legislation_does_not_trigger() -> None:
    attrs = _attrs(
        purpose="Something vague",
        is_safety_component=True,
    )
    assert evaluate(attrs) is None
