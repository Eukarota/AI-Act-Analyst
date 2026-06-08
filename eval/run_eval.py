"""
run_eval.py -- Boussole evaluation harness.

Phase 6 ships the --smoke mode: a tiny 5-case sanity check wired into CI as
a required gate so prompt changes in subsequent phases cannot merge without
running the agent end-to-end. Phase 9 ships the full §12.1 gates (tier
accuracy, citation precision/recall, FN-high-risk rate, etc.) and replaces
this harness's exit criteria with frozen baselines.

Each case is a JSONL record with:

  id                  (str)   identifier
  draft               (bool)  true while the case is unreviewed by the operator
  system_description  (str)   input to the agent
  scripted_extraction (dict)  pre-canned attribute extraction (FakeLLM input)
  expected_tier       (str)   Tier value the rules engine must return
  expected_articles   (list)  article numbers expected to appear in the
                              union of supporting_refs and obligations
  domain              (str)   slice label (used by Phase 9 per-domain stats)

Usage:

    python eval/run_eval.py --regulation ai_act --smoke
    python eval/run_eval.py --regulation ai_act --report
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
from backend.agent.state import AgentState, Citation, SystemProfile
from backend.prompts.loader import default_registry
from backend.rag.retrieve import HybridRetriever
from regulations.ai_act import AiActRegulation
from regulations.ai_act.corpus.loader import AiActChunkerConfig, AiActCorpusLoader

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = REPO_ROOT / "regulations" / "ai_act" / "corpus" / "fixture_excerpt.txt"
SMOKE_PATH = REPO_ROOT / "eval" / "smoke_set.jsonl"
REPORT_DIR = REPO_ROOT / "eval" / "reports"

# Smoke thresholds. The smoke gate's job is "did the agent run end-to-end
# correctly" -- tier accuracy plus expected-article recall. The
# precision-style metric is a Phase 9 concern (full §12.1 gates against
# frozen baselines), not a smoke concern.
SMOKE_TIER_ACCURACY_MIN = 1.0  # smoke set is scripted, expect 100%
SMOKE_ARTICLE_RECALL_MIN = 1.0  # every expected article must surface


@dataclass(frozen=True)
class EvalCase:
    id: str
    draft: bool
    system_description: str
    scripted_extraction: dict[str, Any]
    expected_tier: str
    expected_articles: list[str]
    domain: str

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> EvalCase:
        return cls(
            id=raw["id"],
            draft=bool(raw.get("draft", False)),
            system_description=raw["system_description"],
            scripted_extraction=raw["scripted_extraction"],
            expected_tier=raw["expected_tier"],
            expected_articles=[str(a) for a in raw.get("expected_articles", [])],
            domain=raw.get("domain", "unspecified"),
        )


@dataclass
class CaseResult:
    case: EvalCase
    actual_tier: str
    actual_articles: list[str]
    tier_match: bool
    article_recall: float
    article_precision: float
    fail_reasons: list[str]


def load_cases(path: Path) -> list[EvalCase]:
    cases: list[EvalCase] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        cases.append(EvalCase.from_dict(json.loads(line)))
    return cases


def _full_attributes(extraction: dict[str, Any]) -> dict[str, Any]:
    """Pad the scripted extraction with default fields so AttributeSet validates."""
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


async def _run_case(case: EvalCase, deps: AgentDependencies) -> CaseResult:
    fake_llm: FakeLLM = deps.llm  # type: ignore[assignment]
    prompts = deps.prompts
    rendered = prompts.render(
        "intake_extract_attributes",
        {"system_description": case.system_description},
    )
    fake_llm.script(rendered, json.dumps(_full_attributes(case.scripted_extraction)))

    state = AgentState(system_profile=SystemProfile(description=case.system_description))
    fail_reasons: list[str] = []

    try:
        final = await run_assessment(state, deps=deps)
    except Exception as exc:
        return CaseResult(
            case=case,
            actual_tier="error",
            actual_articles=[],
            tier_match=False,
            article_recall=0.0,
            article_precision=0.0,
            fail_reasons=[f"agent raised {type(exc).__name__}: {exc}"],
        )

    actual_tier = final.classification.tier.value if final.classification else "unknown"
    tier_match = actual_tier == case.expected_tier

    article_sources: set[str] = set()
    if final.classification:
        for ref in final.classification.supporting_refs:
            if ref.article:
                article_sources.add(str(ref.article))
    for obligation in final.obligations:
        if obligation.citation.article:
            article_sources.add(str(obligation.citation.article))

    expected = set(case.expected_articles)
    overlap = expected & article_sources
    recall = (len(overlap) / len(expected)) if expected else 1.0
    precision = (
        (len(overlap) / len(article_sources)) if article_sources else (1.0 if not expected else 0.0)
    )

    if not tier_match:
        fail_reasons.append(f"expected tier {case.expected_tier!r}, got {actual_tier!r}")
    if expected and recall < 1.0:
        missing = sorted(expected - article_sources)
        fail_reasons.append(f"missing expected articles: {missing}")

    return CaseResult(
        case=case,
        actual_tier=actual_tier,
        actual_articles=sorted(article_sources),
        tier_match=tier_match,
        article_recall=recall,
        article_precision=precision,
        fail_reasons=fail_reasons,
    )


def _summarise(results: Iterable[CaseResult]) -> dict[str, Any]:
    results_list = list(results)
    total = len(results_list)
    tier_correct = sum(1 for r in results_list if r.tier_match)
    avg_recall = sum(r.article_recall for r in results_list) / total if total else 0.0
    avg_precision = sum(r.article_precision for r in results_list) / total if total else 0.0
    per_domain: dict[str, dict[str, float]] = {}
    for r in results_list:
        bucket = per_domain.setdefault(r.case.domain, {"count": 0.0, "tier_correct": 0.0})
        bucket["count"] += 1.0
        bucket["tier_correct"] += 1.0 if r.tier_match else 0.0
    return {
        "case_count": total,
        "tier_accuracy": tier_correct / total if total else 0.0,
        "avg_article_recall": avg_recall,
        "avg_article_precision": avg_precision,
        "per_domain": per_domain,
        "failures": [
            {"id": r.case.id, "reasons": r.fail_reasons} for r in results_list if r.fail_reasons
        ],
    }


def _write_report(summary: dict[str, Any], results: list[CaseResult]) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = REPORT_DIR / "smoke_report.json"
    md_path = REPORT_DIR / "smoke_report.md"
    json_path.write_text(
        json.dumps(
            {
                "summary": summary,
                "results": [
                    {
                        "id": r.case.id,
                        "expected_tier": r.case.expected_tier,
                        "actual_tier": r.actual_tier,
                        "expected_articles": r.case.expected_articles,
                        "actual_articles": r.actual_articles,
                        "tier_match": r.tier_match,
                        "article_recall": r.article_recall,
                        "article_precision": r.article_precision,
                        "fail_reasons": r.fail_reasons,
                    }
                    for r in results
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    lines = [
        "# Boussole eval smoke report",
        "",
        f"- Case count: {summary['case_count']}",
        f"- Tier accuracy: {summary['tier_accuracy']:.2%}",
        f"- Avg article recall: {summary['avg_article_recall']:.2%}",
        f"- Avg article precision: {summary['avg_article_precision']:.2%}",
        "",
        "| id | expected | actual | tier? | articles? |",
        "| --- | --- | --- | --- | --- |",
    ]
    for r in results:
        ok_tier = "OK" if r.tier_match else "FAIL"
        ok_articles = (
            "OK"
            if not r.fail_reasons or all("missing" not in reason for reason in r.fail_reasons)
            else "FAIL"
        )
        lines.append(
            f"| {r.case.id} | {r.case.expected_tier} | {r.actual_tier} | "
            f"{ok_tier} | {ok_articles} |"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _exit_status(summary: dict[str, Any], *, smoke: bool) -> int:
    if not smoke:
        return 0
    if summary["tier_accuracy"] < SMOKE_TIER_ACCURACY_MIN:
        return 1
    if summary["avg_article_recall"] < SMOKE_ARTICLE_RECALL_MIN:
        return 1
    if summary["failures"]:
        return 1
    return 0


async def amain() -> int:
    parser = argparse.ArgumentParser(description="Boussole eval harness")
    parser.add_argument("--regulation", required=True, choices=["ai_act"])
    parser.add_argument("--smoke", action="store_true", help="Run the 5-case smoke set")
    parser.add_argument("--report", action="store_true", help="Write report files")
    parser.add_argument("--baseline", type=Path, default=None, help="(Phase 9) baseline JSON")
    args = parser.parse_args()

    if args.regulation != "ai_act":
        print(f"unsupported regulation: {args.regulation}", file=sys.stderr)
        return 2

    # Default behaviour is --smoke until Phase 9 wires the full gates.
    smoke = args.smoke or args.baseline is None

    deps = await _build_deps()
    # Phase 6 only ships the smoke set; the full gold_set lands in Phase 9.
    cases = load_cases(SMOKE_PATH)
    _ = smoke  # reserved for Phase 9's gold-set path
    results: list[CaseResult] = []
    for case in cases:
        results.append(await _run_case(case, deps))

    summary = _summarise(results)
    print(json.dumps(summary, indent=2))
    if args.report:
        _write_report(summary, results)
    return _exit_status(summary, smoke=smoke)


def main() -> int:
    return asyncio.run(amain())


if __name__ == "__main__":
    sys.exit(main())
