"""
run_eval.py -- Boussole evaluation harness.

Phase 9: full CLAUDE.md section 12.1 gates. The smoke set still ships
(--smoke) for fast CI sanity checks, but the default mode is now the
gold set with the published metric gates and the LLM-as-judge for
drafted-document quality.

Modes:

  python eval/run_eval.py --regulation ai_act --smoke
      Lightweight 5-case sanity check (kept for fast CI on every push).

  python eval/run_eval.py --regulation ai_act --gold
      Full gold set; computes all §12.1 metrics; writes report.json + .md.

  python eval/run_eval.py --regulation ai_act --gold \
      --baseline eval/baselines/<corpus_version>.json
      Same as above, plus regression check against the frozen baseline.
      Exit 1 if any gate fails OR any metric regresses vs baseline.

  python eval/run_eval.py --regulation ai_act --gold --freeze-baseline
      Writes the produced metrics to eval/baselines/<corpus_version>.json.
      Use deliberately, after a manual review of the report.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from backend.adapters.fake_embedder import FakeEmbedder
from backend.adapters.fake_llm import FakeLLM
from backend.adapters.in_memory_store import InMemoryVectorStore
from backend.agent.dependencies import AgentBudgets, AgentDependencies
from backend.agent.graph import run_assessment
from backend.agent.state import AgentState, Citation, DraftedDocument, SystemProfile
from backend.prompts.loader import default_registry
from backend.rag.retrieve import HybridRetriever
from eval.judge import judge_documents
from eval.metrics import (
    CaseOutcome,
    GateResult,
    Metrics,
    compute_metrics,
    evaluate_gates,
)
from regulations.ai_act import AiActRegulation
from regulations.ai_act.corpus.loader import AiActChunkerConfig, AiActCorpusLoader

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = REPO_ROOT / "regulations" / "ai_act" / "corpus" / "fixture_excerpt.txt"
SMOKE_PATH = REPO_ROOT / "eval" / "smoke_set.jsonl"
GOLD_PATH = REPO_ROOT / "eval" / "gold_set.jsonl"
REPORT_DIR = REPO_ROOT / "eval" / "reports"
BASELINE_DIR = REPO_ROOT / "eval" / "baselines"

SMOKE_TIER_ACCURACY_MIN = 1.0
SMOKE_ARTICLE_RECALL_MIN = 1.0

# A regression tolerance: when comparing to a frozen baseline, we let a
# metric drift by epsilon to absorb floating-point noise. Real regressions
# (a tier flipping, a citation disappearing) move metrics by >> epsilon.
BASELINE_EPSILON = 1e-4


@dataclass(frozen=True)
class EvalCase:
    id: str
    draft: bool
    slice: str
    difficulty: str
    domain: str
    system_description: str
    scripted_extraction: dict[str, Any]
    expected_tier: str
    expected_articles: list[str]
    rationale: str

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> EvalCase:
        return cls(
            id=raw["id"],
            draft=bool(raw.get("draft", False)),
            slice=raw.get("slice", "stratified"),
            difficulty=raw.get("difficulty", "medium"),
            domain=raw.get("domain", "unspecified"),
            system_description=raw["system_description"],
            scripted_extraction=raw["scripted_extraction"],
            expected_tier=raw["expected_tier"],
            expected_articles=[str(a) for a in raw.get("expected_articles", [])],
            rationale=str(raw.get("rationale", "")),
        )


@dataclass
class CaseRunResult:
    case: EvalCase
    actual_tier: str
    actual_articles: list[str]
    obligation_articles: list[str]
    tier_match: bool
    grounded: bool
    drafted_count: int
    error: str | None


def load_cases(path: Path) -> list[EvalCase]:
    cases: list[EvalCase] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        cases.append(EvalCase.from_dict(json.loads(line)))
    return cases


def _full_attributes(extraction: dict[str, Any]) -> dict[str, Any]:
    defaults: dict[str, Any] = {
        "purpose": extraction.get("purpose") or "system",
        "domain": None,
        "deployment_context": None,
        "user_population": None,
        "autonomy_level": None,
        "human_oversight": None,
        "data_types": [],
        "geography": None,
        "is_gpai_model": False,
        "built_on_gpai": False,
        "is_safety_component": False,
        "regulated_product_legislation": None,
        "biometric": False,
        "affects_fundamental_rights": False,
        "uses_subliminal_techniques": False,
        "social_scoring": False,
        "real_time_remote_biometric_id": False,
        "emotion_recognition": False,
        "interacts_with_humans": False,
        "generates_synthetic_content": False,
        "extras": {},
    }
    defaults.update(extraction)
    return defaults


async def _build_deps() -> AgentDependencies:
    text = FIXTURE_PATH.read_text(encoding="utf-8")
    loader = AiActCorpusLoader.from_text(text)
    triples = list(loader.iter_chunks_with_scope(chunker=AiActChunkerConfig()))
    embedder = FakeEmbedder()
    store = InMemoryVectorStore(corpus_version=loader.corpus_version())
    vectors = await embedder.embed_documents([t[0] for t in triples])
    rows: list[tuple[str, list[float], Citation, str | None]] = [
        (chunk_text, vector, citation, scope)
        for (chunk_text, citation, scope), vector in zip(triples, vectors, strict=True)
    ]
    await store.upsert(rows)
    retriever = HybridRetriever(store=store, embedder=embedder)

    regulation = AiActRegulation(corpus_loader=loader)
    fake_llm = FakeLLM()
    prompts = default_registry()
    return AgentDependencies(
        regulation=regulation,
        llm=fake_llm,
        retriever=retriever,
        prompts=prompts,
        budgets=AgentBudgets(clarify_iterations=3, node_timeout_seconds=20.0),
    )


async def _run_case(case: EvalCase, deps: AgentDependencies) -> CaseRunResult:
    fake_llm: FakeLLM = deps.llm  # type: ignore[assignment]
    prompts = deps.prompts
    rendered = prompts.render(
        "intake_extract_attributes",
        {"system_description": case.system_description},
    )
    fake_llm.script(rendered, json.dumps(_full_attributes(case.scripted_extraction)))

    state = AgentState(system_profile=SystemProfile(description=case.system_description))

    try:
        final = await run_assessment(state, deps=deps)
    except Exception as exc:
        return CaseRunResult(
            case=case,
            actual_tier="error",
            actual_articles=[],
            obligation_articles=[],
            tier_match=False,
            grounded=False,
            drafted_count=0,
            error=f"{type(exc).__name__}: {exc}",
        )

    actual_tier = final.classification.tier.value if final.classification else "unknown"
    tier_match = actual_tier == case.expected_tier

    article_sources: set[str] = set()
    obligation_articles: set[str] = set()
    if final.classification:
        for ref in final.classification.supporting_refs:
            if ref.article:
                article_sources.add(str(ref.article))
    for obligation in final.obligations:
        if obligation.citation.article:
            article_sources.add(str(obligation.citation.article))
            obligation_articles.add(str(obligation.citation.article))

    grounded = any(
        e["kind"] == "grounding_check" and e["name"].endswith("grounding_passed")
        for e in final.trace_events
    )

    return CaseRunResult(
        case=case,
        actual_tier=actual_tier,
        actual_articles=sorted(article_sources),
        obligation_articles=sorted(obligation_articles),
        tier_match=tier_match,
        grounded=grounded,
        drafted_count=len(final.drafted_documents),
        error=None,
    )


def _outcome(run: CaseRunResult) -> CaseOutcome:
    expected_obligations = {
        a for a in run.case.expected_articles if a not in {"5", "51", "53", "55"}
    }
    actual_obligations = set(run.obligation_articles)
    if expected_obligations:
        recall = len(expected_obligations & actual_obligations) / len(expected_obligations)
    else:
        recall = 1.0
    return CaseOutcome(
        case_id=run.case.id,
        slice=run.case.slice,
        domain=run.case.domain,
        expected_tier=run.case.expected_tier,
        actual_tier=run.actual_tier,
        expected_articles=tuple(run.case.expected_articles),
        actual_articles=tuple(run.actual_articles),
        obligation_article_recall=recall,
        grounded=run.grounded,
        error=run.error,
    )


def _summarise_smoke(results: Iterable[CaseRunResult]) -> dict[str, Any]:
    results_list = list(results)
    total = len(results_list)
    tier_correct = sum(1 for r in results_list if r.tier_match)
    article_recalls: list[float] = []
    for r in results_list:
        expected = set(r.case.expected_articles)
        if expected:
            article_recalls.append(len(expected & set(r.actual_articles)) / len(expected))
        else:
            article_recalls.append(1.0)
    avg_recall = sum(article_recalls) / total if total else 0.0
    return {
        "case_count": total,
        "tier_accuracy": tier_correct / total if total else 0.0,
        "avg_article_recall": avg_recall,
        "failures": [
            {
                "id": r.case.id,
                "actual_tier": r.actual_tier,
                "expected_tier": r.case.expected_tier,
                "error": r.error,
            }
            for r in results_list
            if not r.tier_match
            or r.error
            or (set(r.case.expected_articles) - set(r.actual_articles))
        ],
    }


def _smoke_status(summary: dict[str, Any]) -> int:
    if summary["tier_accuracy"] < SMOKE_TIER_ACCURACY_MIN:
        return 1
    if summary["avg_article_recall"] < SMOKE_ARTICLE_RECALL_MIN:
        return 1
    if summary["failures"]:
        return 1
    return 0


def _baseline_regressions(metrics: Metrics, baseline: dict[str, Any]) -> list[str]:
    """Return descriptions of metrics that regressed vs the baseline."""
    regressions: list[str] = []
    higher_is_better = {
        "tier_accuracy",
        "citation_precision",
        "citation_recall",
        "groundedness",
        "obligation_recall",
        "injection_resistance",
    }
    lower_is_better = {"fn_high_risk_rate"}
    current = metrics.to_json()
    for key in higher_is_better:
        if key in baseline and current[key] + BASELINE_EPSILON < baseline[key]:
            regressions.append(f"{key}: {current[key]:.4f} < baseline {baseline[key]:.4f}")
    for key in lower_is_better:
        if key in baseline and current[key] > baseline[key] + BASELINE_EPSILON:
            regressions.append(f"{key}: {current[key]:.4f} > baseline {baseline[key]:.4f}")
    return regressions


def _write_gold_reports(
    metrics: Metrics,
    runs: list[CaseRunResult],
    judge: dict[str, Any],
    gates: list[GateResult],
    corpus_version: str,
    baseline_regressions: list[str],
) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = REPORT_DIR / "gold_report.json"
    md_path = REPORT_DIR / "gold_report.md"
    payload = {
        "corpus_version": corpus_version,
        "metrics": metrics.to_json(),
        "gates": [{"name": g.name, "passed": g.passed, "value": round(g.value, 4)} for g in gates],
        "judge": judge,
        "baseline_regressions": baseline_regressions,
        "cases": [
            {
                "id": r.case.id,
                "slice": r.case.slice,
                "domain": r.case.domain,
                "expected_tier": r.case.expected_tier,
                "actual_tier": r.actual_tier,
                "expected_articles": r.case.expected_articles,
                "actual_articles": r.actual_articles,
                "grounded": r.grounded,
                "drafted_documents": r.drafted_count,
                "error": r.error,
            }
            for r in runs
        ],
    }
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines: list[str] = []
    lines.append("# Boussole eval gold report")
    lines.append("")
    lines.append(f"- Corpus version: `{corpus_version}`")
    lines.append(f"- Cases: {metrics.case_count}")
    lines.append("")
    lines.append("## Section 12.1 gates")
    lines.append("")
    lines.append("| Gate | Value | Status |")
    lines.append("| --- | ---: | --- |")
    for g in gates:
        lines.append(f"| {g.name} | {g.value:.4f} | {'OK' if g.passed else 'FAIL'} |")
    lines.append("")
    lines.append("## Per-slice tier accuracy")
    for k, v in sorted(metrics.per_slice_tier_accuracy.items()):
        lines.append(f"- {k}: {v:.2%}")
    lines.append("")
    lines.append("## Per-domain tier accuracy")
    for k, v in sorted(metrics.per_domain_tier_accuracy.items()):
        lines.append(f"- {k}: {v:.2%}")
    lines.append("")
    lines.append("## Tier confusion matrix")
    lines.append("")
    if metrics.tier_confusion:
        all_actual: set[str] = set()
        for row in metrics.tier_confusion.values():
            all_actual.update(row.keys())
        actuals_sorted = sorted(all_actual)
        header = "| expected \\ actual | " + " | ".join(actuals_sorted) + " |"
        sep = "| --- | " + " | ".join("---" for _ in actuals_sorted) + " |"
        lines.append(header)
        lines.append(sep)
        for exp in sorted(metrics.tier_confusion):
            row = metrics.tier_confusion[exp]
            cells = [str(row.get(a, 0)) for a in actuals_sorted]
            lines.append(f"| {exp} | " + " | ".join(cells) + " |")
        lines.append("")
    lines.append("## Drafted-doc judge")
    lines.append("")
    lines.append(f"- Judged documents: {judge.get('judged_documents', 0)}")
    lines.append(f"- Mean score (1-4): {judge.get('mean_score', 0):.2f}")
    if judge.get("calibrated_kappa") is not None:
        lines.append(f"- Calibrated kappa: {judge['calibrated_kappa']:.2f}")
    else:
        lines.append(
            f"- Calibration: insufficient samples "
            f"({judge.get('calibration_sample_size', 0)} of 20 required)."
        )
    if baseline_regressions:
        lines.append("")
        lines.append("## Baseline regressions")
        for r in baseline_regressions:
            lines.append(f"- {r}")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _baseline_path(corpus_version: str) -> Path:
    return BASELINE_DIR / f"{corpus_version}.json"


async def amain() -> int:
    parser = argparse.ArgumentParser(description="Boussole eval harness")
    parser.add_argument("--regulation", required=True, choices=["ai_act"])
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--smoke", action="store_true", help="5-case smoke set (Phase 6 default)")
    group.add_argument("--gold", action="store_true", help="Full gold set (Phase 9 §12.1 gates)")
    parser.add_argument("--report", action="store_true", help="Write report files")
    parser.add_argument(
        "--baseline",
        type=Path,
        default=None,
        help="Frozen baseline JSON to compare against (gold mode only)",
    )
    parser.add_argument(
        "--freeze-baseline",
        action="store_true",
        help="Write current metrics as the new baseline keyed on corpus_version.",
    )
    args = parser.parse_args()

    if args.regulation != "ai_act":
        print(f"unsupported regulation: {args.regulation}", file=sys.stderr)
        return 2

    if not args.smoke and not args.gold:
        # Default to smoke for backwards compatibility with existing CI.
        args.smoke = True

    deps = await _build_deps()
    path = SMOKE_PATH if args.smoke else GOLD_PATH
    cases = load_cases(path)
    runs: list[CaseRunResult] = []
    for case in cases:
        runs.append(await _run_case(case, deps))

    if args.smoke:
        summary = _summarise_smoke(runs)
        print(json.dumps(summary, indent=2))
        if args.report:
            REPORT_DIR.mkdir(parents=True, exist_ok=True)
            (REPORT_DIR / "smoke_report.json").write_text(
                json.dumps(summary, indent=2), encoding="utf-8"
            )
        return _smoke_status(summary)

    # Gold path
    outcomes = [_outcome(r) for r in runs]
    metrics = compute_metrics(outcomes)
    gates = evaluate_gates(metrics)

    # The judge runs against the drafted documents produced by the graph.
    # We re-run the cases in a tight second pass so the runs list above stays
    # the source of truth for the per-case metrics; the graph is deterministic
    # at temperature 0 with scripted extractions, so the second pass produces
    # the same documents the first pass already saw.
    judge_payload: dict[str, Any] = {
        "judged_documents": 0,
        "mean_score": 0.0,
        "per_criterion": {},
        "calibrated_kappa": None,
        "calibration_sample_size": 0,
        "judge_above_calibration_threshold": False,
    }
    try:
        drafted_docs = await _collect_drafted_docs(cases, deps)
        if drafted_docs:
            judge_aggregate = await judge_documents(drafted_docs, llm=deps.llm)
            judge_payload = judge_aggregate.to_json()
    except Exception as exc:  # judge failure is non-fatal: reported but doesn't gate
        judge_payload["error"] = f"{type(exc).__name__}: {exc}"

    corpus_version = deps.regulation.corpus_loader.corpus_version()
    baseline_data: dict[str, Any] = {}
    if args.baseline and args.baseline.exists():
        baseline_data = json.loads(args.baseline.read_text(encoding="utf-8")).get("metrics", {})
    regressions = _baseline_regressions(metrics, baseline_data) if baseline_data else []

    if args.report:
        _write_gold_reports(metrics, runs, judge_payload, gates, corpus_version, regressions)

    if args.freeze_baseline:
        BASELINE_DIR.mkdir(parents=True, exist_ok=True)
        path_out = _baseline_path(corpus_version)
        path_out.write_text(
            json.dumps(
                {
                    "corpus_version": corpus_version,
                    "metrics": metrics.to_json(),
                    "judge": judge_payload,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"baseline frozen at {path_out}")

    print(json.dumps({"metrics": metrics.to_json(), "judge": judge_payload}, indent=2))
    for g in gates:
        print(("OK  " if g.passed else "FAIL") + f"  {g.name}  (value={g.value:.4f})")
    if regressions:
        print("BASELINE REGRESSIONS:")
        for r in regressions:
            print(f"  - {r}")

    failed_gates = [g for g in gates if not g.passed]
    if failed_gates or regressions:
        return 1
    return 0


async def _collect_drafted_docs(
    cases: list[EvalCase], deps: AgentDependencies
) -> list[DraftedDocument]:
    """Second pass that yields the drafted documents per case for the judge."""
    fake_llm: FakeLLM = deps.llm  # type: ignore[assignment]
    prompts = deps.prompts
    docs: list[DraftedDocument] = []
    for case in cases:
        rendered = prompts.render(
            "intake_extract_attributes",
            {"system_description": case.system_description},
        )
        fake_llm.script(rendered, json.dumps(_full_attributes(case.scripted_extraction)))
        state = AgentState(system_profile=SystemProfile(description=case.system_description))
        try:
            final = await run_assessment(state, deps=deps)
        except Exception:
            continue
        docs.extend(final.drafted_documents)
    return docs


def main() -> int:
    return asyncio.run(amain())


if __name__ == "__main__":
    sys.exit(main())
