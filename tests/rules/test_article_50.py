"""Art. 50 transparency trigger tests."""

from __future__ import annotations

from backend.agent.state import AttributeSet, Tier
from regulations.ai_act.rules.article_50 import evaluate


def _attrs(**kwargs: object) -> AttributeSet:
    base: dict[str, object] = {"purpose": ""}
    base.update(kwargs)
    return AttributeSet(**base)


def test_interaction_with_humans_triggers_paragraph_1() -> None:
    attrs = _attrs(
        purpose="Customer support chatbot for telecom subscribers",
        interacts_with_humans=True,
    )
    match = evaluate(attrs)
    assert match is not None
    assert match.tier == Tier.TRANSPARENCY
    assert any(ref.paragraph == "1" for ref in match.supporting_refs)


def test_generates_synthetic_content_triggers_paragraph_2() -> None:
    attrs = _attrs(
        purpose="Image generation tool for marketing teams",
        generates_synthetic_content=True,
    )
    match = evaluate(attrs)
    assert match is not None
    assert any(ref.paragraph == "2" for ref in match.supporting_refs)


def test_emotion_recognition_outside_workplace_triggers_paragraph_3() -> None:
    attrs = _attrs(
        purpose="Emotion-aware in-car assistant for personal vehicles",
        emotion_recognition=True,
    )
    match = evaluate(attrs)
    assert match is not None
    assert any(ref.paragraph == "3" for ref in match.supporting_refs)


def test_deepfake_keyword_triggers_paragraph_4() -> None:
    attrs = _attrs(
        purpose="Studio tool for voice cloning in marketing videos",
    )
    match = evaluate(attrs)
    assert match is not None
    assert any(ref.paragraph == "4" for ref in match.supporting_refs)


def test_multiple_triggers_aggregate_supporting_refs() -> None:
    attrs = _attrs(
        purpose="Chatbot that also generates synthetic images",
        interacts_with_humans=True,
        generates_synthetic_content=True,
    )
    match = evaluate(attrs)
    assert match is not None
    paragraphs = {ref.paragraph for ref in match.supporting_refs}
    assert "1" in paragraphs
    assert "2" in paragraphs


def test_no_trigger_returns_none() -> None:
    attrs = _attrs(purpose="Internal report summariser for batch jobs")
    assert evaluate(attrs) is None
