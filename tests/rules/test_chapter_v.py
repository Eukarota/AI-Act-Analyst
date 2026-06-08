"""Chapter V GPAI rule tests, including the systemic-risk threshold."""

from __future__ import annotations

from backend.agent.state import AttributeSet, Tier
from regulations.ai_act.rules.chapter_v import evaluate


def _attrs(**kwargs: object) -> AttributeSet:
    base: dict[str, object] = {"purpose": "A general-purpose AI model"}
    base.update(kwargs)
    return AttributeSet(**base)


def test_gpai_model_without_systemic_signal_returns_gpai() -> None:
    attrs = _attrs(is_gpai_model=True)
    match = evaluate(attrs)
    assert match is not None
    assert match.tier == Tier.GPAI
    assert match.fired_rule == "chapter_v.gpai"


def test_gpai_model_with_compute_above_threshold_is_systemic() -> None:
    attrs = _attrs(is_gpai_model=True, extras={"compute_flops": 5e25})
    match = evaluate(attrs)
    assert match is not None
    assert match.tier == Tier.GPAI_SYSTEMIC
    assert any(ref.article == "55" for ref in match.supporting_refs)


def test_gpai_model_at_threshold_is_not_systemic() -> None:
    """The Art. 51(2) presumption is *exceeds* the threshold; equal does not trigger."""
    attrs = _attrs(is_gpai_model=True, extras={"compute_flops": 1e25})
    match = evaluate(attrs)
    assert match is not None
    assert match.tier == Tier.GPAI


def test_gpai_model_with_explicit_designation_is_systemic_regardless_of_compute() -> None:
    attrs = _attrs(is_gpai_model=True, extras={"designated_systemic": True})
    match = evaluate(attrs)
    assert match is not None
    assert match.tier == Tier.GPAI_SYSTEMIC


def test_system_built_on_gpai_does_not_fall_into_chapter_v() -> None:
    # built_on_gpai=True but is_gpai_model=False -> Ch. V does not apply at the
    # system level; the upstream model provider has separate Ch. V obligations.
    attrs = _attrs(is_gpai_model=False, built_on_gpai=True)
    assert evaluate(attrs) is None


def test_compute_flops_as_string_still_parses() -> None:
    attrs = _attrs(is_gpai_model=True, extras={"compute_flops": "5e25"})
    match = evaluate(attrs)
    assert match is not None
    assert match.tier == Tier.GPAI_SYSTEMIC
