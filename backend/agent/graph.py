"""
LangGraph wiring for the Boussole assessment agent.

Topology (CLAUDE.md section 4):

  intake --> clarify? --(loop, bounded)--> intake
         \\
          \\--> classify
                 |
                 v
            retrieve_context
                 |
                 v
        enumerate_obligations
                 |
                 v
             gap_analysis
                 |
                 v
              draft_docs
                 |
                 v
           assemble_report
                 |
                 v
                END

Each node returns a dict of fields to merge into AgentState. Per CLAUDE.md
section 12.3 the agent runs through a Pydantic AgentState, bounded by
AgentBudgets, with OTel spans emitted per node and per tool call.
"""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph

from backend.agent.dependencies import AgentDependencies
from backend.agent.nodes import (
    assemble_report_node,
    clarify_node,
    classify_node,
    draft_docs_node,
    enumerate_obligations_node,
    gap_analysis_node,
    intake_node,
    retrieve_context_node,
)
from backend.agent.state import AgentState


def _route_after_intake(state: AgentState) -> str:
    """If intake raised clarifications and we are under the budget, loop via clarify."""
    return "clarify" if state.clarification_needed else "classify"


def _route_after_clarify(state: AgentState) -> str:
    """After clarify increments the counter, either go back to intake or proceed."""
    return "intake" if state.clarification_needed else "classify"


def build_graph(deps: AgentDependencies) -> Any:
    """
    Compile the StateGraph with `deps` closed over by each node.

    LangGraph wants nodes to be `state -> partial_state` callables; we adapt
    by capturing `deps` in a closure rather than threading it through state
    (deps are per-process, not per-request).
    """

    builder = StateGraph(AgentState)

    async def _intake(state: AgentState) -> dict[str, Any]:
        return await intake_node(state, deps=deps)

    async def _clarify(state: AgentState) -> dict[str, Any]:
        return await clarify_node(state, deps=deps)

    async def _classify(state: AgentState) -> dict[str, Any]:
        return await classify_node(state, deps=deps)

    async def _retrieve(state: AgentState) -> dict[str, Any]:
        return await retrieve_context_node(state, deps=deps)

    async def _enumerate(state: AgentState) -> dict[str, Any]:
        return await enumerate_obligations_node(state, deps=deps)

    async def _gaps(state: AgentState) -> dict[str, Any]:
        return await gap_analysis_node(state, deps=deps)

    async def _draft(state: AgentState) -> dict[str, Any]:
        return await draft_docs_node(state, deps=deps)

    async def _assemble(state: AgentState) -> dict[str, Any]:
        return await assemble_report_node(state, deps=deps)

    builder.add_node("intake", _intake)
    builder.add_node("clarify", _clarify)
    builder.add_node("classify", _classify)
    builder.add_node("retrieve_context", _retrieve)
    builder.add_node("enumerate_obligations", _enumerate)
    builder.add_node("gap_analysis", _gaps)
    builder.add_node("draft_docs", _draft)
    builder.add_node("assemble_report", _assemble)

    builder.set_entry_point("intake")
    builder.add_conditional_edges(
        "intake",
        _route_after_intake,
        {"clarify": "clarify", "classify": "classify"},
    )
    builder.add_conditional_edges(
        "clarify",
        _route_after_clarify,
        {"intake": "intake", "classify": "classify"},
    )
    builder.add_edge("classify", "retrieve_context")
    builder.add_edge("retrieve_context", "enumerate_obligations")
    builder.add_edge("enumerate_obligations", "gap_analysis")
    builder.add_edge("gap_analysis", "draft_docs")
    builder.add_edge("draft_docs", "assemble_report")
    builder.add_edge("assemble_report", END)

    return builder.compile()


async def run_assessment(
    initial_state: AgentState,
    *,
    deps: AgentDependencies,
) -> AgentState:
    """
    Drive the graph end-to-end. Returns the finalised AgentState.

    The state's trace_events carry the OTel-equivalent event stream that
    the Phase 8 UI renders as a glass-box panel.
    """
    graph = build_graph(deps)
    final_dict = await graph.ainvoke(initial_state)
    # LangGraph returns either a dict or a state object depending on version;
    # normalise to AgentState.
    if isinstance(final_dict, AgentState):
        return final_dict
    return AgentState.model_validate(final_dict)
