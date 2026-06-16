"""
classify node: deterministic tier decision.

CLAUDE.md section 6: "attribute extraction is the LLM's job; the verdict is
the rules layer's job". This node calls the rules engine on the
AttributeSet that intake produced (and that clarify may have refined).
"""

from __future__ import annotations

import time
from typing import Any

from backend.agent.dependencies import AgentDependencies
from backend.agent.errors import LowExtractionConfidence
from backend.agent.nodes._common import emit_tool_call, emit_tool_return, emitter_for
from backend.agent.state import AgentState
from backend.agent.trace import TraceEventKind
from regulations.ai_act.rules._rationale_fr import localize_classification

NODE_NAME = "classify"


async def classify_node(state: AgentState, *, deps: AgentDependencies) -> dict[str, Any]:
    emitter = emitter_for(state)
    attributes = state.system_profile.attributes
    if attributes is None:
        raise LowExtractionConfidence(
            "classify node entered with no extracted attributes; intake did not run"
        )

    started = time.perf_counter()
    with emitter.node(NODE_NAME):
        emit_tool_call(
            emitter,
            name="rules.classify",
            inputs={
                "purpose_preview": attributes.purpose[:120],
                "is_gpai_model": attributes.is_gpai_model,
            },
        )
        classification = deps.regulation.classifier_rules.classify(attributes)
        classification = localize_classification(
            classification, state.system_profile.language
        )
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        emit_tool_return(
            emitter,
            name="rules.classify",
            outputs={
                "tier": classification.tier.value,
                "fired_rule": classification.fired_rule,
                "rules_version": classification.rules_version,
            },
            latency_ms=elapsed_ms,
        )

        emitter.emit(
            TraceEventKind.CLASSIFICATION,
            name="classification.decided",
            attributes={
                "tier": classification.tier.value,
                "fired_rule": classification.fired_rule,
                "rules_version": classification.rules_version,
                "supporting_articles": [ref.short() for ref in classification.supporting_refs],
            },
        )

    return {
        "classification": classification,
        "trace_events": list(emitter.sink),
    }
