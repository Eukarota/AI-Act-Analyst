"""
retrieve_context node: pull the passages the report will cite.

CLAUDE.md section 12.2: scoped retrieval per node, not a global pass.
We choose scopes based on the classified tier and run separate scoped
retrievals so the downstream assemble_report's grounding check sees a
focused set with high precision.
"""

from __future__ import annotations

import time
from typing import Any

from backend.agent.dependencies import AgentDependencies
from backend.agent.errors import RetrievalEmpty
from backend.agent.nodes._common import emit_tool_call, emit_tool_return, emitter_for
from backend.agent.state import AgentState, RetrievedPassage, Tier
from backend.agent.trace import TraceEventKind
from backend.mcp_servers.retrieve_law import RetrieveLawArgs, retrieve_law

NODE_NAME = "retrieve_context"

_SCOPES_BY_TIER: dict[Tier, tuple[str, ...]] = {
    Tier.PROHIBITED: ("art_5_prohibited",),
    Tier.HIGH_RISK_ANNEX_I: (
        "annex_i_high_risk_products",
        "high_risk_definition",
        "high_risk_obligations",
        "deployer_obligations",
        "conformity_assessment",
    ),
    Tier.HIGH_RISK_ANNEX_III: (
        "annex_iii_high_risk_uses",
        "high_risk_definition",
        "high_risk_obligations",
        "deployer_obligations",
        "conformity_assessment",
    ),
    Tier.TRANSPARENCY: ("art_50_transparency",),
    Tier.GPAI: ("gpai",),
    Tier.GPAI_SYSTEMIC: ("gpai", "gpai_systemic"),
    Tier.MINIMAL: (),
    Tier.UNDETERMINED: (),
}


def _query_for_scope(scope: str, purpose: str) -> str:
    """Compose a scoped query: purpose plus a scope-flavoured keyword."""
    flavour = scope.replace("_", " ")
    return f"{flavour} {purpose}"


async def retrieve_context_node(state: AgentState, *, deps: AgentDependencies) -> dict[str, Any]:
    emitter = emitter_for(state)
    classification = state.classification
    if classification is None:
        raise RetrievalEmpty(
            "retrieve_context entered without a classification; classify did not run"
        )

    scopes = _SCOPES_BY_TIER.get(classification.tier, ())
    if not scopes:
        # Minimal-risk and undetermined tiers retrieve nothing; the report
        # makes no high-risk claims and therefore needs no passages.
        emitter.emit(
            TraceEventKind.RETRIEVAL,
            name="retrieve_context.skipped",
            attributes={"tier": classification.tier.value},
        )
        return {"retrieved_passages": [], "trace_events": list(emitter.sink)}

    purpose = ""
    if state.system_profile.attributes is not None:
        purpose = state.system_profile.attributes.purpose
    if not purpose:
        purpose = state.system_profile.description[:200]

    collected: list[RetrievedPassage] = []
    seen_keys: set[tuple[object, ...]] = set()

    with emitter.node(NODE_NAME):
        for scope in scopes:
            query = _query_for_scope(scope, purpose)
            inputs = {"scope": scope, "query_preview": query[:120]}
            emit_tool_call(emitter, name="retrieve_law", inputs=inputs)
            started = time.perf_counter()
            result = await retrieve_law(
                RetrieveLawArgs(query=query, scope=scope, top_k=4),
                retriever=deps.retriever,
            )
            elapsed_ms = (time.perf_counter() - started) * 1000.0
            emit_tool_return(
                emitter,
                name="retrieve_law",
                outputs={
                    "scope": scope,
                    "passage_count": len(result.passages),
                    "citations": [p.citation.short() for p in result.passages],
                },
                latency_ms=elapsed_ms,
            )

            for passage in result.passages:
                key = (
                    passage.citation.celex_id,
                    passage.citation.article,
                    passage.citation.paragraph,
                    passage.citation.annex_ref,
                    passage.citation.recital_ref,
                )
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                collected.append(passage)

    # An empty set after every scope means retrieval is unable to ground any
    # claim; downstream nodes cannot proceed safely.
    if scopes and not collected:
        raise RetrievalEmpty(
            f"no passages retrieved for tier {classification.tier.value} across scopes {scopes}"
        )

    return {
        "retrieved_passages": collected,
        "trace_events": list(emitter.sink),
    }
