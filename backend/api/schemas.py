"""
HTTP request / response shapes for the /assess and /trace routes.

Kept distinct from AgentState so the API surface can evolve without
forcing schema changes inside the agent core, and vice versa.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.agent.report import AssessmentReport
from backend.agent.state import ActorRole


class AssessRequest(BaseModel):
    """POST /assess body."""

    model_config = ConfigDict(extra="forbid")

    system_description: str = Field(
        ..., min_length=10, description="Natural-language description of the AI system."
    )
    declared_controls: list[str] = Field(
        default_factory=list,
        description="Controls the client already has in place (used by gap_analysis).",
    )
    declared_actor_role: ActorRole | None = Field(
        default=None,
        description="Provider, deployer, etc. Filters obligations in enumerate_obligations.",
    )
    language: Literal["EN", "FR"] = Field(
        default="EN",
        description=(
            "Output language for backend-generated text (obligation summaries, "
            "classification rationale, drafted documents)."
        ),
    )


class AssessResponse(BaseModel):
    """POST /assess response: the full AssessmentReport, status echoed in HTTP code."""

    model_config = ConfigDict(extra="forbid")

    report: AssessmentReport


class TraceResponse(BaseModel):
    """GET /trace/{run_id} response."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    schema_version: str
    events: list[dict]  # type: ignore[type-arg]


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str = "ok"


class ReadyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    checks: dict[str, bool]


class ErrorResponse(BaseModel):
    """Typed error body. Mirrors the TypedFailure shape on the report."""

    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    run_id: str | None = None


class ExtractResponse(BaseModel):
    """POST /extract response: plain text extracted from an uploaded file."""

    model_config = ConfigDict(extra="forbid")

    text: str
    truncated: bool
    char_count: int
    page_count: int | None = None
    source_filename: str
    source_media_type: str


class DriftResponse(BaseModel):
    """GET /drift response. Rolling input-domain + tier-mix distributions."""

    model_config = ConfigDict(extra="forbid")

    window_size: int
    sample_count: int
    input_domain: dict[str, float]
    tier_mix: dict[str, float]
