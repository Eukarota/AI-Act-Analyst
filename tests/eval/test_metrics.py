"""Unit tests for eval.metrics."""

from __future__ import annotations

from eval.metrics import (
    GATES,
    CaseOutcome,
    compute_metrics,
    evaluate_gates,
)


def _outcome(**overrides: object) -> CaseOutcome:
    base: dict[str, object] = {
        "case_id": "x",
        "slice": "stratified",
        "domain": "employment",
        "expected_tier": "high_risk_annex_iii",
        "actual_tier": "high_risk_annex_iii",
        "expected_articles": ("9", "11"),
        "actual_articles": ("9", "11"),
        "obligation_article_recall": 1.0,
        "grounded": True,
        "error": None,
    }
    base.update(overrides)
    return CaseOutcome(**base)  # type: ignore[arg-type]


def test_perfect_run_passes_all_gates() -> None:
    outcomes = [_outcome() for _ in range(10)]
    metrics = compute_metrics(outcomes)
    assert metrics.tier_accuracy == 1.0
    assert metrics.groundedness == 1.0
    results = evaluate_gates(metrics)
    assert all(r.passed for r in results), [r for r in results if not r.passed]


def test_fn_high_risk_rate_counts_only_high_risk_expected() -> None:
    outcomes = [
        _outcome(expected_tier="high_risk_annex_iii", actual_tier="minimal"),
        _outcome(expected_tier="high_risk_annex_i", actual_tier="high_risk_annex_i"),
        _outcome(
            expected_tier="minimal",
            actual_tier="minimal",
            expected_articles=(),
            actual_articles=(),
        ),
    ]
    metrics = compute_metrics(outcomes)
    # 1 of 2 high-risk expected was missed -> 0.5
    assert metrics.fn_high_risk_rate == 0.5


def test_injection_resistance_only_counts_adversarial_slice() -> None:
    outcomes = [
        _outcome(slice="adversarial", expected_tier="high_risk_annex_iii", actual_tier="minimal"),
        _outcome(slice="adversarial"),
        _outcome(slice="stratified"),
    ]
    metrics = compute_metrics(outcomes)
    assert metrics.injection_resistance == 0.5


def test_minimal_tier_recall_credits_correct_classification() -> None:
    outcomes = [
        _outcome(
            expected_tier="minimal",
            actual_tier="minimal",
            expected_articles=(),
            actual_articles=(),
        )
    ]
    metrics = compute_metrics(outcomes)
    assert metrics.citation_recall == 1.0


def test_minimal_tier_recall_penalises_wrong_classification() -> None:
    outcomes = [
        _outcome(
            expected_tier="minimal",
            actual_tier="high_risk_annex_iii",
            expected_articles=(),
            actual_articles=("9",),
        )
    ]
    metrics = compute_metrics(outcomes)
    assert metrics.citation_recall == 0.0


def test_citation_precision_is_one_when_actual_subset_of_expected() -> None:
    outcomes = [_outcome(expected_articles=("9", "11", "13"), actual_articles=("9", "11"))]
    metrics = compute_metrics(outcomes)
    assert metrics.citation_precision == 1.0


def test_citation_precision_drops_when_actual_includes_extras() -> None:
    outcomes = [_outcome(expected_articles=("9",), actual_articles=("9", "99"))]
    metrics = compute_metrics(outcomes)
    assert metrics.citation_precision == 0.5


def test_tier_confusion_records_mismatches() -> None:
    outcomes = [
        _outcome(expected_tier="high_risk_annex_iii", actual_tier="minimal"),
        _outcome(expected_tier="high_risk_annex_iii", actual_tier="high_risk_annex_iii"),
    ]
    metrics = compute_metrics(outcomes)
    assert metrics.tier_confusion["high_risk_annex_iii"] == {
        "minimal": 1,
        "high_risk_annex_iii": 1,
    }


def test_groundedness_gate_is_exact_one() -> None:
    outcomes = [_outcome(grounded=False)] + [_outcome() for _ in range(9)]
    metrics = compute_metrics(outcomes)
    assert metrics.groundedness == 0.9
    results = {r.name: r.passed for r in evaluate_gates(metrics)}
    groundedness_gates = [g for g in GATES if g.metric_key == "groundedness"]
    assert results[groundedness_gates[0].name] is False
