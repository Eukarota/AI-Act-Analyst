"""Unit tests for eval.judge (rubric parsing + Cohen's kappa)."""

from __future__ import annotations

from eval.judge import _parse_scores, cohen_kappa


def test_parse_scores_extracts_json_block() -> None:
    text = 'Preamble {"scores": {"structure": 4, "citations": 3}} trailing'
    assert _parse_scores(text, ["structure", "citations"]) == {
        "structure": 4,
        "citations": 3,
    }


def test_parse_scores_defaults_to_worst_for_missing_keys() -> None:
    text = '{"scores": {"structure": 3}}'
    assert _parse_scores(text, ["structure", "citations"]) == {
        "structure": 3,
        "citations": 1,
    }


def test_parse_scores_clamps_out_of_range() -> None:
    text = '{"scores": {"structure": 99, "citations": -2}}'
    assert _parse_scores(text, ["structure", "citations"]) == {
        "structure": 4,
        "citations": 1,
    }


def test_parse_scores_handles_garbage_response() -> None:
    assert _parse_scores("not json at all", ["structure"]) == {"structure": 1}


def test_cohen_kappa_perfect_agreement() -> None:
    pairs = [(1, 1), (2, 2), (3, 3), (4, 4)]
    assert cohen_kappa(pairs) == 1.0


def test_cohen_kappa_no_better_than_chance_is_zero() -> None:
    # Symmetric: half agree, half disagree, marginals balanced. p_obs = p_exp.
    pairs = [(1, 1)] * 5 + [(2, 2)] * 5 + [(1, 2)] * 5 + [(2, 1)] * 5
    assert abs(cohen_kappa(pairs)) < 1e-9


def test_cohen_kappa_partial_agreement_in_range() -> None:
    pairs = [(1, 1), (1, 1), (2, 2), (2, 2), (1, 2), (2, 1)]
    kappa = cohen_kappa(pairs)
    assert 0.0 < kappa < 1.0
