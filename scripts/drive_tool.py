"""
drive_tool.py: in-process smoke-driver for the five MCP tools.

CLAUDE.md plan, Phase 5 checkpoint:
  "scripts/drive_tool.py exercises all five tools; every tool response
   carries citation metadata."

Runs each tool with a fixture system description ("recruitment chatbot
that filters job applications") and prints a compact report. Asserts
that citations are attached to every output where the contract demands
them. Exits non-zero on any assertion failure.

Usage:
    python scripts/drive_tool.py
    python scripts/drive_tool.py --verbose
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from backend.adapters.fake_embedder import FakeEmbedder
from backend.adapters.fake_llm import FakeLLM
from backend.adapters.in_memory_store import InMemoryVectorStore
from backend.agent.state import ActorRole, Citation
from backend.mcp_servers.analyze_gaps import AnalyzeGapsArgs, analyze_gaps
from backend.mcp_servers.classify_risk import ClassifyRiskArgs, classify_risk
from backend.mcp_servers.draft_documentation import (
    DraftDocumentationArgs,
    draft_documentation,
)
from backend.mcp_servers.lookup_obligations import LookupObligationsArgs, lookup_obligations
from backend.mcp_servers.retrieve_law import RetrieveLawArgs, retrieve_law
from backend.prompts.loader import default_registry
from backend.rag.retrieve import HybridRetriever
from regulations.ai_act import AiActRegulation
from regulations.ai_act.corpus.loader import AiActChunkerConfig, AiActCorpusLoader

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = REPO_ROOT / "regulations" / "ai_act" / "corpus" / "fixture_excerpt.txt"

SYSTEM_DESCRIPTION = (
    "We deploy an AI tool that filters job applications and ranks candidates "
    "for our recruitment pipeline. The model is hosted in-house. Final hiring "
    "decisions are made by a human recruiter who reviews the top three "
    "candidates per opening."
)

DECLARED_CONTROLS = (
    "We log every model decision with the candidate ID and timestamp for auditability.",
    "Risk management system reviewed quarterly with engineering and HR.",
    "Each shortlisted candidate is reviewed by a human recruiter before any contact.",
    "Internal model evaluation runs against a balanced demographic test set.",
)

# Scripted FakeLLM response: simulates a clean attribute extraction. Matches
# the prompt rendered by intake_extract_attributes_v1.j2 so the same key is
# used in both the script and the test fixture.
SCRIPTED_ATTRIBUTES = {
    "purpose": "Filter job applications and rank candidates for recruitment.",
    "domain": "employment",
    "deployment_context": "internal HR pipeline",
    "user_population": "job applicants",
    "autonomy_level": "human in the loop",
    "human_oversight": "human recruiter reviews top three",
    "data_types": ["resume", "application data"],
    "geography": "France",
    "is_gpai_model": False,
    "built_on_gpai": False,
    "is_safety_component": False,
    "regulated_product_legislation": None,
    "biometric": False,
    "affects_fundamental_rights": True,
    "uses_subliminal_techniques": False,
    "social_scoring": False,
    "real_time_remote_biometric_id": False,
    "emotion_recognition": False,
    "interacts_with_humans": False,
    "generates_synthetic_content": False,
    "extras": {},
}


async def _index_corpus(store: InMemoryVectorStore, embedder: FakeEmbedder) -> None:
    loader = AiActCorpusLoader.from_text(FIXTURE_PATH.read_text(encoding="utf-8"))
    triples = list(loader.iter_chunks_with_scope(chunker=AiActChunkerConfig()))
    vectors = await embedder.embed_documents([t[0] for t in triples])
    rows: list[tuple[str, list[float], Citation, str | None]] = [
        (text, vector, citation, scope)
        for (text, citation, scope), vector in zip(triples, vectors, strict=True)
    ]
    await store.upsert(rows)


async def run(*, verbose: bool) -> int:
    reg = AiActRegulation()
    embedder = FakeEmbedder()
    store = InMemoryVectorStore(corpus_version=reg.corpus_loader.corpus_version())
    await _index_corpus(store, embedder)
    retriever = HybridRetriever(store=store, embedder=embedder)

    fake_llm = FakeLLM()
    prompts = default_registry()
    intake_prompt = prompts.render(
        "intake_extract_attributes",
        {"system_description": SYSTEM_DESCRIPTION},
    )
    fake_llm.script(intake_prompt, json.dumps(SCRIPTED_ATTRIBUTES))

    report: dict[str, object] = {}
    failures: list[str] = []

    # 1. retrieve_law
    rl = await retrieve_law(
        RetrieveLawArgs(query="recruitment selection of natural persons", top_k=4),
        retriever=retriever,
    )
    report["retrieve_law"] = {
        "passage_count": len(rl.passages),
        "first_citation": rl.passages[0].citation.short() if rl.passages else None,
    }
    if not rl.passages:
        failures.append("retrieve_law returned no passages")
    for p in rl.passages:
        if not p.citation.celex_id:
            failures.append("retrieve_law returned a passage without celex_id")
            break

    # 2. classify_risk
    cr = await classify_risk(
        ClassifyRiskArgs(system_description=SYSTEM_DESCRIPTION),
        llm=fake_llm,
        rules=reg.classifier_rules,
        prompts=prompts,
    )
    report["classify_risk"] = {
        "tier": cr.classification.tier.value,
        "fired_rule": cr.classification.fired_rule,
        "rules_version": cr.classification.rules_version,
        "supporting_refs": [r.short() for r in cr.classification.supporting_refs],
    }
    if not cr.classification.supporting_refs:
        failures.append("classify_risk returned no supporting refs")

    # 3. lookup_obligations
    lo = await lookup_obligations(
        LookupObligationsArgs(classification=cr.classification, actor_role=ActorRole.PROVIDER),
        obligations_map=reg.obligations_map,
    )
    report["lookup_obligations"] = {
        "tier": lo.tier,
        "count": len(lo.obligations),
        "first_obligation": lo.obligations[0].article_ref if lo.obligations else None,
    }
    for o in lo.obligations:
        if not o.citation.celex_id:
            failures.append("lookup_obligations returned an obligation without celex_id")
            break

    # 4. analyze_gaps
    ag = await analyze_gaps(
        AnalyzeGapsArgs(
            required=tuple(lo.obligations),
            declared_controls=DECLARED_CONTROLS,
            actor_role=ActorRole.PROVIDER,
        )
    )
    statuses = {f.status for f in ag.findings}
    report["analyze_gaps"] = {
        "coverage_ratio": round(ag.coverage_ratio, 3),
        "statuses": sorted(statuses),
        "findings_count": len(ag.findings),
    }
    if not ag.findings:
        failures.append("analyze_gaps returned no findings")

    # 5. draft_documentation
    dd = await draft_documentation(
        DraftDocumentationArgs(
            system_name="Recruitment Assistant",
            classification=cr.classification,
            attributes=cr.attributes,
            retrieved_passages=tuple(rl.passages),
            documents_to_draft=(),
            language="fr",
        ),
        templates=reg.document_templates,
    )
    report["draft_documentation"] = {
        "documents": [
            {
                "kind": d.kind,
                "citations": [c.short() for c in d.citations],
                "body_chars": len(d.body),
            }
            for d in dd.documents
        ],
    }
    for d in dd.documents:
        if not d.citations:
            failures.append(f"draft_documentation document {d.kind!r} returned no citations")

    if verbose:
        print(json.dumps(report, indent=2, default=str))
    else:
        print(json.dumps(report, default=str))

    if failures:
        print("\nFAILED:", file=sys.stderr)
        for failure in failures:
            print(f"  - {failure}", file=sys.stderr)
        return 1

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    return asyncio.run(run(verbose=args.verbose))


if __name__ == "__main__":
    sys.exit(main())
