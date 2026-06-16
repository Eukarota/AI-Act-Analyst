"""enumerate_obligations node: tier -> obligations via the obligations map."""

from __future__ import annotations

import time
from typing import Any

from backend.agent.dependencies import AgentDependencies
from backend.agent.nodes._common import emit_tool_call, emit_tool_return, emitter_for
from backend.agent.state import AgentState
from backend.mcp_servers.lookup_obligations import (
    LookupObligationsArgs,
    lookup_obligations,
)
from regulations.ai_act.obligations.loader import localize_obligations

NODE_NAME = "enumerate_obligations"


async def enumerate_obligations_node(
    state: AgentState, *, deps: AgentDependencies
) -> dict[str, Any]:
    emitter = emitter_for(state)
    classification = state.classification
    if classification is None:
        return {"obligations": [], "trace_events": list(emitter.sink)}

    actor_role = state.system_profile.declared_actor_role

    with emitter.node(NODE_NAME):
        emit_tool_call(
            emitter,
            name="lookup_obligations",
            inputs={
                "tier": classification.tier.value,
                "actor_role": actor_role.value if actor_role else None,
            },
        )
        started = time.perf_counter()
        result = await lookup_obligations(
            LookupObligationsArgs(classification=classification, actor_role=actor_role),
            obligations_map=deps.regulation.obligations_map,
        )
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        emit_tool_return(
            emitter,
            name="lookup_obligations",
            outputs={
                "tier": result.tier,
                "count": len(result.obligations),
                "articles": [o.article_ref for o in result.obligations],
            },
            latency_ms=elapsed_ms,
        )

    obligations = localize_obligations(
        list(result.obligations), state.system_profile.language
    )
    return {
        "obligations": obligations,
        "trace_events": list(emitter.sink),
    }
