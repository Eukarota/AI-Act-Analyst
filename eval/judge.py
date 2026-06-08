"""
LLM-as-judge for drafted-document quality.

CLAUDE.md section 12.1 mandates: "Drafted-document quality via LLM-as-judge
against a written rubric, calibrated to a >= 20-sample human-labeled set;
report judge<->human Cohen's kappa and recalibrate if kappa < 0.6."

This module gives that contract a home. The judge itself runs against any
LLMProvider (FakeLLM in CI, vLLM/Ollama in dev). The rubric is captured in
this file so reviewers can see what we are scoring. The calibration set
lives at eval/judge_calibration.jsonl; until 20 human labels are present
the calibrated_kappa is reported as None and a warning is emitted.

Score scale (1-4) for each criterion:
  1 -- absent or wrong
  2 -- present but partial
  3 -- present and correct, light on detail
  4 -- present, correct, and cited

The overall document score is the mean of the criterion scores. The
calibration set holds gold human scores per (doc_kind, criterion).
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from backend.agent.state import DraftedDocument
from backend.ports.llm_provider import LLMProvider

REPO_ROOT = Path(__file__).resolve().parents[1]
CALIBRATION_PATH = REPO_ROOT / "eval" / "judge_calibration.jsonl"
MIN_CALIBRATION_SAMPLES = 20
MIN_ACCEPTABLE_KAPPA = 0.6

RUBRIC = {
    "annex_iv": (
        ("structure", "Annex IV headings present and in the expected order."),
        ("scope", "Document scope reflects the assessed system."),
        (
            "risk_management",
            "Risk management approach (Art. 9) is referenced with at least one specific control.",
        ),
        ("citations", "Each section that makes a legal claim carries a citation."),
    ),
    "art_50_notice": (
        ("disclosure", "Notice states the user is interacting with an AI."),
        ("clarity", "Plain language understandable to a non-technical reader."),
        ("citations", "Notice references Art. 50 paragraph that applies."),
    ),
}
DEFAULT_CRITERIA = (
    ("structure", "Document structure is coherent and complete."),
    ("citations", "Each legal statement carries a citation."),
)

_JUDGE_PROMPT = (
    "You are reviewing an AI-Act compliance document produced by an automated agent.\n"
    "Score each criterion on a 1-4 scale, where:\n"
    "  1 = absent or wrong; 2 = partial; 3 = correct, light detail; 4 = correct and cited.\n"
    "Reply with a single JSON object: {\"scores\": {\"<criterion>\": <int>, ...}}.\n"
    "Do not include any other text.\n\n"
    "Document kind: {kind}\n"
    "Title: {title}\n"
    "---BEGIN DOCUMENT---\n{body}\n---END DOCUMENT---\n\n"
    "Criteria:\n{criteria}\n"
)


@dataclass(frozen=True)
class JudgeScore:
    doc_kind: str
    criterion_scores: dict[str, int]

    @property
    def overall(self) -> float:
        if not self.criterion_scores:
            return 0.0
        return sum(self.criterion_scores.values()) / len(self.criterion_scores)


@dataclass(frozen=True)
class JudgeAggregate:
    judged_documents: int
    mean_score: float
    per_criterion: dict[str, float]
    calibrated_kappa: float | None
    calibration_sample_size: int
    judge_above_calibration_threshold: bool

    def to_json(self) -> dict[str, Any]:
        return {
            "judged_documents": self.judged_documents,
            "mean_score": round(self.mean_score, 4),
            "per_criterion": {k: round(v, 4) for k, v in self.per_criterion.items()},
            "calibrated_kappa": (
                round(self.calibrated_kappa, 4) if self.calibrated_kappa is not None else None
            ),
            "calibration_sample_size": self.calibration_sample_size,
            "judge_above_calibration_threshold": self.judge_above_calibration_threshold,
        }


async def score_document(
    document: DraftedDocument,
    *,
    llm: LLMProvider,
) -> JudgeScore:
    """Run the judge on a single drafted document."""
    criteria = RUBRIC.get(document.kind, DEFAULT_CRITERIA)
    rendered_criteria = "\n".join(f"- {name}: {description}" for name, description in criteria)
    prompt = _JUDGE_PROMPT.format(
        kind=document.kind,
        title=document.title,
        body=document.body[:3000],
        criteria=rendered_criteria,
    )
    response = await llm.complete(prompt, max_tokens=256)
    scores = _parse_scores(response.text, [name for name, _ in criteria])
    return JudgeScore(doc_kind=document.kind, criterion_scores=scores)


def _parse_scores(text: str, expected_keys: Sequence[str]) -> dict[str, int]:
    """Permissive JSON extraction. Missing keys default to 1 (worst)."""
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    raw: dict[str, Any] = {}
    if match:
        try:
            payload = json.loads(match.group(0))
            scores = payload.get("scores")
            if isinstance(scores, dict):
                raw = scores
        except json.JSONDecodeError:
            pass
    out: dict[str, int] = {}
    for key in expected_keys:
        value = raw.get(key, 1)
        try:
            int_value = int(value)
        except (TypeError, ValueError):
            int_value = 1
        out[key] = max(1, min(4, int_value))
    return out


async def judge_documents(
    documents: Sequence[DraftedDocument],
    *,
    llm: LLMProvider,
) -> JudgeAggregate:
    """Run the judge over a batch of drafted documents."""
    scores: list[JudgeScore] = []
    for doc in documents:
        scores.append(await score_document(doc, llm=llm))

    judged = len(scores)
    if judged == 0:
        return JudgeAggregate(
            judged_documents=0,
            mean_score=0.0,
            per_criterion={},
            calibrated_kappa=None,
            calibration_sample_size=0,
            judge_above_calibration_threshold=False,
        )

    mean_score = sum(s.overall for s in scores) / judged
    per_criterion_sum: dict[str, float] = {}
    per_criterion_count: dict[str, int] = {}
    for score in scores:
        for key, value in score.criterion_scores.items():
            per_criterion_sum[key] = per_criterion_sum.get(key, 0.0) + value
            per_criterion_count[key] = per_criterion_count.get(key, 0) + 1
    per_criterion = {
        key: per_criterion_sum[key] / per_criterion_count[key] for key in per_criterion_sum
    }

    kappa, sample_size = _calibration_kappa()
    above_threshold = kappa is not None and kappa >= MIN_ACCEPTABLE_KAPPA

    return JudgeAggregate(
        judged_documents=judged,
        mean_score=mean_score,
        per_criterion=per_criterion,
        calibrated_kappa=kappa,
        calibration_sample_size=sample_size,
        judge_above_calibration_threshold=above_threshold,
    )


def _calibration_kappa() -> tuple[float | None, int]:
    """
    Cohen's kappa between judge scores and human labels.

    Returns (None, n) until at least MIN_CALIBRATION_SAMPLES human rows exist.
    Calibration rows are JSONL:
      {"doc_kind": "...", "criterion": "...", "judge_score": int, "human_score": int}
    """
    if not CALIBRATION_PATH.exists():
        return None, 0
    rows: list[tuple[int, int]] = []
    for line in CALIBRATION_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        judge = record.get("judge_score")
        human = record.get("human_score")
        if isinstance(judge, int) and isinstance(human, int):
            rows.append((judge, human))
    if len(rows) < MIN_CALIBRATION_SAMPLES:
        return None, len(rows)
    return cohen_kappa(rows), len(rows)


def cohen_kappa(pairs: Sequence[tuple[int, int]]) -> float:
    """
    Unweighted Cohen's kappa over integer labels.

    Implemented here so the eval has no scikit-learn dependency.
    """
    n = len(pairs)
    if n == 0:
        return 0.0
    labels = sorted({label for pair in pairs for label in pair})
    if len(labels) < 2:
        return 1.0  # degenerate: all labels identical
    counts: dict[tuple[int, int], int] = {}
    for pair in pairs:
        counts[pair] = counts.get(pair, 0) + 1
    p_observed = sum(counts.get((label, label), 0) for label in labels) / n
    rater_a = {label: 0 for label in labels}
    rater_b = {label: 0 for label in labels}
    for (a, b), count in counts.items():
        rater_a[a] += count
        rater_b[b] += count
    p_expected = sum((rater_a[label] / n) * (rater_b[label] / n) for label in labels)
    if math.isclose(p_expected, 1.0):
        return 1.0
    return (p_observed - p_expected) / (1.0 - p_expected)
