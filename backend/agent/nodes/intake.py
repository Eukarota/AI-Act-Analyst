"""
intake node: LLM-only attribute extraction.

Per CLAUDE.md section 12.3, the LLM is responsible for extraction at
temperature 0. The deterministic rules engine runs in the classify node,
not here. Between intake and classify, the clarify node can loop back
asking the user (or in autonomous mode, accepting defaults) for missing
attributes.

The node also sets clarification_needed when a load-bearing attribute is
underspecified for the kinds of tier decisions the regulation makes.
"""

from __future__ import annotations

import time
from typing import Any

from backend.adapters.vllm_provider import LLMProviderError
from backend.agent.dependencies import AgentDependencies
from backend.agent.errors import LowExtractionConfidence, ModelError
from backend.agent.nodes._common import (
    emit_tool_call,
    emit_tool_return,
    emitter_for,
    run_with_timeout,
)
from backend.agent.state import (
    AgentState,
    AttributeSet,
    ClarificationQuestion,
    SystemProfile,
)
from backend.agent.trace import TraceEventKind
from backend.mcp_servers.classify_risk import (
    AttributeExtractionError,
    ClassifyRiskArgs,
    extract_attributes,
)

NODE_NAME = "intake"

# Attributes the clarify loop will ask about when missing. Kept short and
# tied to the rule branches that depend on them.
_LOAD_BEARING_ATTRIBUTES: tuple[tuple[str, str], ...] = (
    ("human_oversight", "Whether and how a human reviews or overrides the system's outputs."),
    (
        "deployment_context",
        "Where the system will be used (workplace, public service, consumer product, etc.).",
    ),
    (
        "user_population",
        "Who the system makes decisions about or interacts with.",
    ),
)


def _is_unspecified(value: Any) -> bool:
    if value is None:
        return True
    return isinstance(value, str) and not value.strip()


def _detect_clarifications(attributes: AttributeSet) -> list[ClarificationQuestion]:
    questions: list[ClarificationQuestion] = []
    for attribute, why in _LOAD_BEARING_ATTRIBUTES:
        if _is_unspecified(getattr(attributes, attribute, None)):
            questions.append(
                ClarificationQuestion(
                    attribute=attribute,
                    question=(
                        f"Could you clarify the {attribute.replace('_', ' ')} of the system?"
                    ),
                    why_it_matters=why,
                )
            )
    return questions


async def intake_node(state: AgentState, *, deps: AgentDependencies) -> dict[str, Any]:
    emitter = emitter_for(state)
    started = time.perf_counter()
    with emitter.node(NODE_NAME):
        emit_tool_call(
            emitter,
            name="extract_attributes",
            inputs={"description_preview": state.system_profile.description[:200]},
            model_id=deps.llm.model_id,
        )
        try:
            attributes = await run_with_timeout(
                extract_attributes(
                    ClassifyRiskArgs(
                        system_description=state.system_profile.description,
                        declared_attributes=None,
                    ),
                    llm=deps.llm,
                    prompts=deps.prompts,
                ),
                timeout_seconds=deps.budgets.node_timeout_seconds,
                node_name=NODE_NAME,
            )
        except AttributeExtractionError as exc:
            raise LowExtractionConfidence(str(exc)) from exc
        except LLMProviderError as exc:
            # Upstream HTTP error from Mistral / vLLM (4xx, 5xx, malformed
            # body, no choices). Surface as a typed ModelError so the route
            # returns 422 with a structured failure instead of 500.
            raise ModelError(f"intake LLM call failed: {exc}") from exc
        except (TimeoutError, OSError) as exc:
            raise ModelError(f"intake LLM call failed: {exc}") from exc

        elapsed_ms = (time.perf_counter() - started) * 1000.0
        emit_tool_return(
            emitter,
            name="extract_attributes",
            outputs=attributes.model_dump(),
            latency_ms=elapsed_ms,
            model_id=deps.llm.model_id,
        )

        questions = _detect_clarifications(attributes)
        clarification_needed = bool(questions) and (
            state.clarification_iterations < deps.budgets.clarify_iterations
        )

        if questions:
            emitter.emit(
                TraceEventKind.CLARIFICATION,
                name="intake.questions_raised",
                attributes={
                    "count": len(questions),
                    "attributes": [q.attribute for q in questions],
                },
            )

    new_profile = SystemProfile(
        description=state.system_profile.description,
        declared_controls=list(state.system_profile.declared_controls),
        declared_actor_role=state.system_profile.declared_actor_role,
        attributes=attributes,
    )

    return {
        "system_profile": new_profile,
        "clarification_needed": clarification_needed,
        "clarification_questions": list(state.clarification_questions) + questions,
        "trace_events": list(emitter.sink),
    }
