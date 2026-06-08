"""
The /assess request runner: AgentState -> AssessmentReport, with manifest
construction, online grounding check, and run-store persistence.

The grounding check imported here is the exact same function the eval and
the assemble_report node call. CLAUDE.md section 12.4: "Eval and prod call
the identical check" -- enforced by import, never duplicated.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import structlog

from backend.agent.dependencies import AgentDependencies
from backend.agent.errors import (
    AgentError,
    ClarificationExhausted,
    TypedFailure,
)
from backend.agent.graph import run_assessment
from backend.agent.report import AssessmentReport, ReportStatus
from backend.agent.state import AgentState, RetrievedPassage, RunManifest
from backend.api.run_store import RunStore
from backend.rag.grounding import (
    Claim,
    GroundingError,
    assert_grounded,
    citation_key,
)

_log = structlog.get_logger(__name__)


class AssessmentRunner:
    """Composes graph + manifest + grounding + persistence."""

    def __init__(self, *, deps: AgentDependencies, run_store: RunStore) -> None:
        self.deps = deps
        self.run_store = run_store

    def _build_manifest(self, run_id: str) -> RunManifest:
        deps = self.deps
        return RunManifest(
            run_id=run_id,
            corpus_version=deps.regulation.corpus_loader.corpus_version(),
            model_id=deps.llm.model_id,
            embedding_model=getattr(deps.retriever.embedder, "model_id", "unknown"),
            prompt_set_version=deps.prompts.prompt_set_version(),
            rules_version=deps.regulation.classifier_rules.rules_version,
            timestamp=datetime.now(UTC),
        )

    def _build_claims(self, state: AgentState) -> list[Claim]:
        """
        Mirror assemble_report._build_claims so the online check enforces the
        same contract on the same set of claims. Kept here (not imported) to
        avoid coupling the API to a private node helper; the assertion that
        the two stay aligned is in tests/api/test_assess_route.py.
        """
        claims: list[Claim] = []
        classification = state.classification
        if classification is not None and classification.supporting_refs:
            claims.append(
                Claim(
                    text=(
                        f"This system is pre-assessed as {classification.tier.value} "
                        f"under the AI Act. Rule fired: {classification.fired_rule}. "
                        f"{classification.rationale}"
                    ),
                    citations=classification.supporting_refs,
                    source_node="classify",
                )
            )
        for obligation in state.obligations:
            claims.append(
                Claim(
                    text=f"{obligation.article_ref}: {obligation.summary}",
                    citations=(obligation.citation,),
                    source_node="enumerate_obligations",
                )
            )
        return claims

    def _augmented_passages(self, state: AgentState) -> list[RetrievedPassage]:
        """
        Build the union of retrieved passages + rules-layer refs surfaced by
        classify and lookup_obligations. Same union assemble_report uses, so
        the online check matches the in-graph check by construction.
        """
        passages = list(state.retrieved_passages)
        keys = {citation_key(p.citation) for p in passages}
        if state.classification is not None:
            for ref in state.classification.supporting_refs:
                if citation_key(ref) not in keys:
                    passages.append(
                        RetrievedPassage(
                            text=f"[rules-layer reference: {ref.short()}]",
                            citation=ref,
                            score=1.0,
                            retrieval_scope="rules_layer",
                        )
                    )
                    keys.add(citation_key(ref))
        for obligation in state.obligations:
            if citation_key(obligation.citation) not in keys:
                passages.append(
                    RetrievedPassage(
                        text=f"[obligation reference: {obligation.article_ref}]",
                        citation=obligation.citation,
                        score=1.0,
                        retrieval_scope="rules_layer",
                    )
                )
                keys.add(citation_key(obligation.citation))
        return passages

    async def run(self, initial_state: AgentState) -> AssessmentReport:
        manifest = self._build_manifest(run_id=initial_state.run_id)
        log = _log.bind(run_id=initial_state.run_id)
        log.info(
            "assess.start",
            corpus_version=manifest.corpus_version,
            model_id=manifest.model_id,
            prompt_set_version=manifest.prompt_set_version,
        )

        failures: list[TypedFailure] = []
        grounding_passed = False
        status = ReportStatus.COMPLETE
        final_state: AgentState

        try:
            final_state = await run_assessment(initial_state, deps=self.deps)
            grounding_passed = True
        except ClarificationExhausted as exc:
            log.warning("assess.clarification_exhausted", message=str(exc))
            failures.append(TypedFailure.from_exception(exc, node="clarify"))
            status = ReportStatus.INCOMPLETE_CLARIFICATION_EXHAUSTED
            final_state = initial_state
        except GroundingError as exc:
            log.error(
                "assess.grounding_failed",
                violation_count=exc.result.violation_count,
                checked_claims=exc.result.checked_claims,
            )
            failures.append(
                TypedFailure(
                    code="grounding_failed",
                    message=str(exc),
                    node="assemble_report",
                )
            )
            status = ReportStatus.FAILED
            final_state = initial_state
        except AgentError as exc:
            log.error("assess.agent_error", code=exc.code, message=str(exc))
            failures.append(TypedFailure.from_exception(exc))
            status = ReportStatus.FAILED
            final_state = initial_state

        if status == ReportStatus.COMPLETE:
            online_claims = self._build_claims(final_state)
            online_passages = self._augmented_passages(final_state)
            try:
                online_result = assert_grounded(online_claims, online_passages, fail_closed=True)
                log.info(
                    "assess.online_grounding_passed",
                    checked_claims=online_result.checked_claims,
                )
            except GroundingError as exc:
                log.error(
                    "assess.online_grounding_failed",
                    violation_count=exc.result.violation_count,
                    checked_claims=exc.result.checked_claims,
                )
                failures.append(
                    TypedFailure(
                        code="online_grounding_failed",
                        message=str(exc),
                        node="api.assess",
                    )
                )
                grounding_passed = False
                status = ReportStatus.FAILED

        report = AssessmentReport(
            run_id=initial_state.run_id,
            manifest=manifest,
            status=status,
            grounding_passed=grounding_passed,
            system_profile=final_state.system_profile,
            classification=final_state.classification,
            clarification_questions=final_state.clarification_questions,
            clarification_iterations=final_state.clarification_iterations,
            obligations=final_state.obligations,
            gaps=final_state.gaps,
            drafted_documents=final_state.drafted_documents,
            retrieved_passages=final_state.retrieved_passages,
            failures=failures,
        )

        trace_events: list[dict[str, Any]] = list(final_state.trace_events)
        await self.run_store.save(report, trace_events)
        log.info(
            "assess.persisted",
            status=status.value,
            grounding_passed=grounding_passed,
            obligation_count=len(report.obligations),
            retrieved_passage_count=len(report.retrieved_passages),
        )
        return report
