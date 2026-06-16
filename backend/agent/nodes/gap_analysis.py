"""gap_analysis node: diff declared controls against required obligations."""

from __future__ import annotations

import time
from typing import Any

from backend.agent.dependencies import AgentDependencies
from backend.agent.nodes._common import emit_tool_call, emit_tool_return, emitter_for
from backend.agent.state import AgentState
from backend.mcp_servers.analyze_gaps import AnalyzeGapsArgs, analyze_gaps

NODE_NAME = "gap_analysis"


async def gap_analysis_node(state: AgentState, *, deps: AgentDependencies) -> dict[str, Any]:
    emitter = emitter_for(state)

    if not state.obligations:
        return {"gaps": [], "trace_events": list(emitter.sink)}

    declared = tuple(state.system_profile.declared_controls)
    actor_role = state.system_profile.declared_actor_role

    with emitter.node(NODE_NAME):
        emit_tool_call(
            emitter,
            name="analyze_gaps",
            inputs={
                "obligation_count": len(state.obligations),
                "declared_count": len(declared),
                "actor_role": actor_role.value if actor_role else None,
            },
        )
        started = time.perf_counter()
        result = await analyze_gaps(
            AnalyzeGapsArgs(
                required=tuple(state.obligations),
                declared_controls=declared,
                actor_role=actor_role,
                language=state.system_profile.language,
            )
        )
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        emit_tool_return(
            emitter,
            name="analyze_gaps",
            outputs={
                "coverage_ratio": round(result.coverage_ratio, 4),
                "findings_count": len(result.findings),
                "status_counts": {
                    status: sum(1 for f in result.findings if f.status == status)
                    for status in {f.status for f in result.findings}
                },
            },
            latency_ms=elapsed_ms,
        )

    # Tip: deps unused for now; reserved for Phase 9's per-domain matchers.
    _ = deps

    return {
        "gaps": result.findings,
        "trace_events": list(emitter.sink),
    }
