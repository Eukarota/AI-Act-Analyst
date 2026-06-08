"""
clarify node: bounded loop, surfaces a targeted question.

CLAUDE.md section 12.3: "≤ 3 clarify iterations → then proceed with an
explicit uncertainty flag". In Phase 6 we surface the question into state
without blocking the run -- the Phase 7 API layer is what stops the run
and waits for the user. For autonomous test runs, the clarify node simply
increments the counter so the bounded-loop test can verify termination.

When clarification_iterations reaches budgets.clarify_iterations, we flip
clarification_needed=False so the graph routes to classify with the best
understanding we have.
"""

from __future__ import annotations

from typing import Any

from backend.agent.dependencies import AgentDependencies
from backend.agent.nodes._common import emitter_for
from backend.agent.state import AgentState
from backend.agent.trace import TraceEventKind

NODE_NAME = "clarify"


async def clarify_node(state: AgentState, *, deps: AgentDependencies) -> dict[str, Any]:
    emitter = emitter_for(state)
    with emitter.node(NODE_NAME):
        next_iteration = state.clarification_iterations + 1
        exhausted = next_iteration >= deps.budgets.clarify_iterations

        emitter.emit(
            TraceEventKind.CLARIFICATION,
            name="clarify.iteration",
            attributes={
                "iteration": next_iteration,
                "exhausted": exhausted,
                "pending_attributes": [q.attribute for q in state.clarification_questions],
            },
        )

        if exhausted:
            emitter.emit(
                TraceEventKind.CLARIFICATION,
                name="clarify.exhausted",
                attributes={"max_iterations": deps.budgets.clarify_iterations},
            )

    return {
        "clarification_iterations": next_iteration,
        # When exhausted, hand control back without further clarification.
        "clarification_needed": not exhausted,
        "trace_events": list(emitter.sink),
    }
