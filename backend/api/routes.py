"""
FastAPI routes: /assess, /trace/{run_id}, /health, /ready.

CLAUDE.md section 12.3 + 12.4:
  - Stateless: per-request state lives in the payload/DB, not process memory.
  - Online groundedness on every response (delegated to AssessmentRunner).
  - Structured JSON logs correlated by run_id (bound in the contextvar here).
"""

from __future__ import annotations

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse

from backend.agent.state import AgentState, SystemProfile
from backend.agent.trace import TRACE_SCHEMA_VERSION
from backend.api.assess_runner import AssessmentRunner
from backend.api.run_store import RunStore
from backend.api.schemas import (
    AssessRequest,
    AssessResponse,
    ErrorResponse,
    HealthResponse,
    ReadyResponse,
    TraceResponse,
)

_log = structlog.get_logger(__name__)

router = APIRouter()


def get_runner(request: Request) -> AssessmentRunner:
    runner = getattr(request.app.state, "runner", None)
    if runner is None:
        raise RuntimeError("AssessmentRunner not wired on app.state.runner")
    return runner  # type: ignore[no-any-return]


def get_run_store(request: Request) -> RunStore:
    run_store = getattr(request.app.state, "run_store", None)
    if run_store is None:
        raise RuntimeError("RunStore not wired on app.state.run_store")
    return run_store  # type: ignore[no-any-return]


@router.get("/health", response_model=HealthResponse, tags=["service"])
async def health() -> HealthResponse:
    """Liveness. Process is up, event loop is responsive."""
    return HealthResponse()


@router.get("/ready", response_model=ReadyResponse, tags=["service"])
async def ready(
    run_store: Annotated[RunStore, Depends(get_run_store)],
) -> ReadyResponse:
    """Readiness. DB reachable; the rest of the pipeline is wired in startup."""
    checks: dict[str, bool] = {}
    try:
        checks["run_store"] = await run_store.ping()
    except Exception:  # pragma: no cover -- defensive
        checks["run_store"] = False
    all_ok = all(checks.values())
    return ReadyResponse(status="ok" if all_ok else "degraded", checks=checks)


@router.post(
    "/assess",
    response_model=AssessResponse,
    responses={502: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    tags=["assess"],
)
async def assess(
    payload: AssessRequest,
    runner: Annotated[AssessmentRunner, Depends(get_runner)],
) -> JSONResponse:
    """Run a full assessment. Returns the AssessmentReport.

    Status mapping:
      complete                            -> 200
      incomplete_clarification_exhausted  -> 200 (report carries the questions)
      failed (grounding violation)        -> 502 (blocked by the online check)
      failed (other agent error)          -> 422 (typed failure surfaced to caller)
    """
    initial_state = AgentState(
        system_profile=SystemProfile(
            description=payload.system_description,
            declared_controls=list(payload.declared_controls),
            declared_actor_role=payload.declared_actor_role,
        )
    )

    structlog.contextvars.bind_contextvars(run_id=initial_state.run_id)
    try:
        report = await runner.run(initial_state)
    finally:
        structlog.contextvars.unbind_contextvars("run_id")

    body = AssessResponse(report=report).model_dump(mode="json")
    if report.status.value == "complete":
        return JSONResponse(status_code=status.HTTP_200_OK, content=body)
    if report.status.value == "incomplete_clarification_exhausted":
        return JSONResponse(status_code=status.HTTP_200_OK, content=body)

    grounding_failure = next(
        (f for f in report.failures if f.code in {"grounding_failed", "online_grounding_failed"}),
        None,
    )
    if grounding_failure is not None:
        return JSONResponse(status_code=status.HTTP_502_BAD_GATEWAY, content=body)
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=body)


@router.get(
    "/trace/{run_id}",
    response_model=TraceResponse,
    responses={404: {"model": ErrorResponse}},
    tags=["trace"],
)
async def get_trace(
    run_id: str,
    run_store: Annotated[RunStore, Depends(get_run_store)],
) -> TraceResponse:
    """Return the persisted trace event stream for a run_id."""
    events = await run_store.get_trace(run_id)
    if events is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "trace_not_found", "message": f"no trace for run_id={run_id}"},
        )
    return TraceResponse(run_id=run_id, schema_version=TRACE_SCHEMA_VERSION, events=events)
