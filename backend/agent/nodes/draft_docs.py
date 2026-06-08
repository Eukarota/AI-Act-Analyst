"""draft_docs node: render Annex IV + Art. 50 templates."""

from __future__ import annotations

import time
from typing import Any

from backend.agent.dependencies import AgentDependencies
from backend.agent.nodes._common import emit_tool_call, emit_tool_return, emitter_for
from backend.agent.state import AgentState, AttributeSet
from backend.mcp_servers.draft_documentation import (
    DraftDocumentationArgs,
    draft_documentation,
)

NODE_NAME = "draft_docs"


async def draft_docs_node(state: AgentState, *, deps: AgentDependencies) -> dict[str, Any]:
    emitter = emitter_for(state)
    classification = state.classification
    if classification is None:
        return {"drafted_documents": [], "trace_events": list(emitter.sink)}

    attributes = state.system_profile.attributes or AttributeSet(
        purpose=state.system_profile.description[:200] or "system"
    )

    system_name = (
        attributes.extras.get("system_name", "System under assessment")
        if attributes.extras
        else "System under assessment"
    )

    with emitter.node(NODE_NAME):
        emit_tool_call(
            emitter,
            name="draft_documentation",
            inputs={
                "tier": classification.tier.value,
                "passage_count": len(state.retrieved_passages),
            },
        )
        started = time.perf_counter()
        result = await draft_documentation(
            DraftDocumentationArgs(
                system_name=str(system_name),
                classification=classification,
                attributes=attributes,
                retrieved_passages=tuple(state.retrieved_passages),
                documents_to_draft=(),
                language="fr",
            ),
            templates=deps.regulation.document_templates,
            llm=deps.llm,
        )
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        emit_tool_return(
            emitter,
            name="draft_documentation",
            outputs={
                "document_kinds": [d.kind for d in result.documents],
            },
            latency_ms=elapsed_ms,
        )

    return {
        "drafted_documents": result.documents,
        "trace_events": list(emitter.sink),
    }
