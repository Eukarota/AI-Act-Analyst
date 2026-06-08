"""
assemble_report node: build claims + enforce the grounding contract.

This is where CLAUDE.md section 6's grounding contract becomes load-bearing:
every legal claim in the assembled report must be backed by a passage in
the retrieved set, OR a citation that matches one of the rules-layer refs
on the classification itself. The same assert_grounded function used by
Phase 7's online check and Phase 9's eval runs here -- one implementation,
three callers, enforced by import.
"""

from __future__ import annotations

from typing import Any

from backend.agent.dependencies import AgentDependencies
from backend.agent.nodes._common import emitter_for
from backend.agent.state import AgentState
from backend.agent.trace import TraceEventKind
from backend.rag.grounding import (
    Claim,
    GroundingError,
    GroundingResult,
    assert_grounded,
    citation_key,
)

NODE_NAME = "assemble_report"


def _build_claims(state: AgentState) -> list[Claim]:
    """
    Build the list of claims the report makes that need grounding.

    Minimal-risk classifications produce no claim here: the report simply
    states "this is minimal-risk" which is a NEGATIVE statement (no AI Act
    obligations attach) and is therefore not subject to grounding against
    retrieved articles. Every higher tier emits the classification claim
    plus one claim per obligation.
    """
    claims: list[Claim] = []
    classification = state.classification

    if classification is not None and classification.supporting_refs:
        claims.append(
            Claim(
                text=(
                    f"This system is pre-assessed as {classification.tier.value} under "
                    f"the AI Act. Rule fired: {classification.fired_rule}. "
                    f"{classification.rationale}"
                ),
                citations=classification.supporting_refs,
                source_node="classify",
            )
        )

    for obligation in state.obligations:
        claims.append(
            Claim(
                text=(f"{obligation.article_ref}: {obligation.summary}"),
                citations=(obligation.citation,),
                source_node="enumerate_obligations",
            )
        )

    return claims


async def assemble_report_node(state: AgentState, *, deps: AgentDependencies) -> dict[str, Any]:
    emitter = emitter_for(state)
    _ = deps  # reserved; Phase 7 will pass the manifest builder through deps.

    with emitter.node(NODE_NAME):
        claims = _build_claims(state)

        # Build the union of citations that the report can rely on: every
        # retrieved passage, plus the rules-layer refs surfaced by classify
        # and lookup_obligations. The grounding key ignores corpus_version,
        # so rules-layer refs (corpus_version="ai_act-rules") match
        # retrieved passages (corpus_version=<indexed>) when article + paragraph
        # + annex_ref agree.
        from backend.agent.state import RetrievedPassage

        passages = list(state.retrieved_passages)
        rules_keys = {citation_key(p.citation) for p in passages}
        if state.classification is not None:
            for ref in state.classification.supporting_refs:
                if citation_key(ref) not in rules_keys:
                    passages.append(
                        RetrievedPassage(
                            text=f"[rules-layer reference: {ref.short()}]",
                            citation=ref,
                            score=1.0,
                            retrieval_scope="rules_layer",
                        )
                    )
                    rules_keys.add(citation_key(ref))
        for obligation in state.obligations:
            if citation_key(obligation.citation) not in rules_keys:
                passages.append(
                    RetrievedPassage(
                        text=f"[obligation reference: {obligation.article_ref}]",
                        citation=obligation.citation,
                        score=1.0,
                        retrieval_scope="rules_layer",
                    )
                )
                rules_keys.add(citation_key(obligation.citation))

        try:
            result: GroundingResult = assert_grounded(claims, passages, fail_closed=True)
            grounded = True
            emitter.emit(
                TraceEventKind.GROUNDING_CHECK,
                name="assemble_report.grounding_passed",
                attributes={"checked_claims": result.checked_claims},
            )
        except GroundingError as exc:
            grounded = False
            emitter.emit(
                TraceEventKind.GROUNDING_CHECK,
                name="assemble_report.grounding_failed",
                attributes={
                    "violation_count": exc.result.violation_count,
                    "checked_claims": exc.result.checked_claims,
                    "violations": [v.describe() for v in exc.result.violations],
                },
            )
            raise

    return {
        "trace_events": list(emitter.sink),
        # confidence carries the report-level signal forward; downstream the
        # API layer maps this to the AssessmentReport.status field.
        "confidence": 1.0 if grounded else 0.0,
    }
