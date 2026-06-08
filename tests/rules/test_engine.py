"""
AiActRules engine tests.

Covers ordered precedence and the deterministic-output requirement.
The per-rule modules are tested independently; this file checks the engine
glues them together correctly.
"""

from __future__ import annotations

from backend.agent.state import AttributeSet, Tier
from regulations.ai_act.rules.engine import RULES_VERSION, AiActRules


def _attrs(**kwargs: object) -> AttributeSet:
    base: dict[str, object] = {"purpose": "default"}
    base.update(kwargs)
    return AttributeSet(**base)


def test_gpai_track_short_circuits_system_track() -> None:
    """A GPAI model in a high-risk-looking domain still classifies as GPAI."""
    engine = AiActRules()
    attrs = _attrs(
        purpose="A general-purpose model used in recruitment workflows",
        is_gpai_model=True,
    )
    result = engine.classify(attrs)
    assert result.tier == Tier.GPAI
    assert "chapter_v" in result.fired_rule


def test_article_5_outranks_annex_iii() -> None:
    """Social scoring used in an essential-services context must be PROHIBITED, not HIGH_RISK."""
    engine = AiActRules()
    attrs = _attrs(
        purpose="System for social scoring deciding access to credit",
        social_scoring=True,
    )
    result = engine.classify(attrs)
    assert result.tier == Tier.PROHIBITED


def test_annex_i_outranks_annex_iii() -> None:
    """A safety-component recruitment tool is Annex I (the regulated-product path wins)."""
    engine = AiActRules()
    attrs = _attrs(
        purpose="Safety component for industrial robot used in recruitment workflow",
        is_safety_component=True,
        regulated_product_legislation="Machinery Regulation (EU) 2023/1230",
    )
    result = engine.classify(attrs)
    assert result.tier == Tier.HIGH_RISK_ANNEX_I


def test_annex_iii_outranks_article_50() -> None:
    """A chatbot that also screens job candidates is HIGH_RISK, not just transparent."""
    engine = AiActRules()
    attrs = _attrs(
        purpose="Recruitment chatbot that filters job applications",
        interacts_with_humans=True,
    )
    result = engine.classify(attrs)
    assert result.tier == Tier.HIGH_RISK_ANNEX_III


def test_default_minimal_when_no_rule_fires() -> None:
    engine = AiActRules()
    attrs = _attrs(purpose="Internal batch summariser for archive documents")
    result = engine.classify(attrs)
    assert result.tier == Tier.MINIMAL
    assert result.fired_rule == "default.minimal"
    assert result.supporting_refs == ()


def test_classify_is_deterministic() -> None:
    """Same AttributeSet, same rules_version => identical ClassificationResult."""
    engine = AiActRules()
    attrs = _attrs(
        purpose="Filter job applications and rank candidates for recruitment",
    )
    a = engine.classify(attrs)
    b = engine.classify(attrs)
    assert a == b


def test_classify_carries_rules_version() -> None:
    engine = AiActRules()
    attrs = _attrs(purpose="anything")
    result = engine.classify(attrs)
    assert result.rules_version == RULES_VERSION


def test_classify_with_custom_rules_version_propagates_to_result() -> None:
    engine = AiActRules(rules_version="custom-v9")
    attrs = _attrs(purpose="anything")
    result = engine.classify(attrs)
    assert result.rules_version == "custom-v9"
