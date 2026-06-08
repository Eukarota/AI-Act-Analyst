"""
Agent error taxonomy.

CLAUDE.md section 12.3: typed errors, fail closed -- "The system never
degrades to a fabricated answer; failure is explicit and visible."

Each error here represents a different cause of an aborted assessment.
The agent surfaces them through the trace and the AssessmentReport's
status field; the FastAPI layer (Phase 7) translates them into typed
HTTP responses without leaking internal details.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class AgentError(Exception):
    """Base class for all agent-internal failures."""

    code: str = "agent_error"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        if code is not None:
            self.code = code


class RetrievalEmpty(AgentError):
    """The retrieval layer returned no passages for a required scope."""

    code = "retrieval_empty"


class LowExtractionConfidence(AgentError):
    """The LLM extracted attributes but they fail validation or are too sparse."""

    code = "low_extraction_confidence"


class ModelError(AgentError):
    """The upstream LLM call failed (network, server error, malformed output)."""

    code = "model_error"


class NodeTimeout(AgentError):
    """A graph node exceeded its per-node timeout."""

    code = "node_timeout"


class ToolCallBudgetExceeded(AgentError):
    """The per-run cumulative tool-call budget was exhausted."""

    code = "tool_call_budget_exceeded"


class ClarificationExhausted(AgentError):
    """The clarify loop reached its iteration cap; assessment proceeds with uncertainty flag."""

    code = "clarification_exhausted"


class TypedFailure(BaseModel):
    """A serialisable record of a failure, for the AssessmentReport."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    code: str
    message: str
    node: str | None = None

    @classmethod
    def from_exception(cls, exc: AgentError, *, node: str | None = None) -> TypedFailure:
        return cls(code=exc.code, message=str(exc), node=node)
