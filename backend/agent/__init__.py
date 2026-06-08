"""
Agent core package.

Light __init__: importing this package must not pull in graph + dependencies,
because those import from backend.ports.regulation which itself imports from
backend.agent.state -- a cycle. Consumers should import the specific module
they need, e.g.:

    from backend.agent.graph import run_assessment
    from backend.agent.dependencies import AgentDependencies
    from backend.agent.errors import RetrievalEmpty
"""

from backend.agent.errors import (
    AgentError,
    ClarificationExhausted,
    LowExtractionConfidence,
    ModelError,
    NodeTimeout,
    RetrievalEmpty,
    ToolCallBudgetExceeded,
    TypedFailure,
)
from backend.agent.state import (
    AgentState,
    AttributeSet,
    Citation,
    ClassificationResult,
    Obligation,
    RetrievedPassage,
    RunManifest,
    SystemProfile,
    Tier,
)
from backend.agent.trace import TraceEmitter, TraceEvent, TraceEventKind

__all__ = [
    "AgentError",
    "AgentState",
    "AttributeSet",
    "Citation",
    "ClarificationExhausted",
    "ClassificationResult",
    "LowExtractionConfidence",
    "ModelError",
    "NodeTimeout",
    "Obligation",
    "RetrievalEmpty",
    "RetrievedPassage",
    "RunManifest",
    "SystemProfile",
    "Tier",
    "ToolCallBudgetExceeded",
    "TraceEmitter",
    "TraceEvent",
    "TraceEventKind",
    "TypedFailure",
]
