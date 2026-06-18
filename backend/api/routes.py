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
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.responses import JSONResponse, PlainTextResponse, Response

from backend.agent.state import AgentState, SystemProfile
from backend.agent.trace import TRACE_SCHEMA_VERSION
from backend.api.assess_runner import AssessmentRunner
from backend.api.drift import DriftTracker
from backend.api.export import (
    PdfRenderingUnavailable,
    render_markdown_document,
    render_pdf_document,
)
from backend.api.extract import (
    FileTooLarge,
    UnsupportedMediaType,
    extract as extract_text_from_upload,
)
from backend.api.run_store import RunStore
from backend.api.schemas import (
    AssessRequest,
    AssessResponse,
    DriftResponse,
    ErrorResponse,
    ExtractResponse,
    HealthResponse,
    ReadyResponse,
    TraceResponse,
)
from backend.api.telemetry import Telemetry, get_telemetry

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


def get_telemetry_dep(request: Request) -> Telemetry:
    telemetry = getattr(request.app.state, "telemetry", None)
    if telemetry is None:
        return get_telemetry()
    return telemetry  # type: ignore[no-any-return]


def get_drift_tracker(request: Request) -> DriftTracker:
    drift = getattr(request.app.state, "drift", None)
    if drift is None:
        raise RuntimeError("DriftTracker not wired on app.state.drift")
    return drift  # type: ignore[no-any-return]


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
            language=payload.language,
        )
    )

    structlog.contextvars.bind_contextvars(run_id=initial_state.run_id)
    try:
        report = await runner.run(initial_state)
        # Serialization happens before contextvars are unbound so any
        # post-persist failure (Pydantic shape regression, non-JSON value
        # in AttributeSet.extras, etc.) is logged with the run_id attached.
        try:
            body = AssessResponse(report=report).model_dump(mode="json")
        except Exception as exc:
            _log.exception(
                "assess.response_serialisation_failed",
                error_type=type(exc).__name__,
                error_message=str(exc)[:500],
            )
            raise
    finally:
        structlog.contextvars.unbind_contextvars("run_id")
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


@router.post(
    "/extract",
    response_model=ExtractResponse,
    responses={
        413: {"model": ErrorResponse},
        415: {"model": ErrorResponse},
    },
    tags=["intake"],
)
async def extract_text(
    file: Annotated[UploadFile, File(description="PDF or text document to ingest.")],
) -> ExtractResponse:
    """Extract plain text from an uploaded document.

    The client uses the returned `text` to pre-fill the system description.
    The user can then edit before submitting to /assess; nothing is auto-sent.
    """
    data = await file.read()
    try:
        result = extract_text_from_upload(
            data=data,
            filename=file.filename or "upload",
            content_type=file.content_type or "",
        )
    except FileTooLarge as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={"code": "file_too_large", "message": str(exc)},
        ) from exc
    except UnsupportedMediaType as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail={"code": "unsupported_media_type", "message": str(exc)},
        ) from exc
    return ExtractResponse(
        text=result.text,
        truncated=result.truncated,
        char_count=result.char_count,
        page_count=result.page_count,
        source_filename=result.source_filename,
        source_media_type=result.source_media_type,
    )


@router.get(
    "/assess/{run_id}/export.md",
    response_class=PlainTextResponse,
    responses={404: {"model": ErrorResponse}},
    tags=["assess"],
)
async def export_markdown(
    run_id: str,
    run_store: Annotated[RunStore, Depends(get_run_store)],
) -> Response:
    """Render the persisted assessment as a Markdown document."""
    report = await run_store.get_report(run_id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "report_not_found", "message": f"no report for run_id={run_id}"},
        )
    doc = render_markdown_document(report)
    return Response(
        content=doc.body,
        media_type=doc.media_type,
        headers={"Content-Disposition": f'attachment; filename="{doc.filename}"'},
    )


@router.get(
    "/assess/{run_id}/export.pdf",
    responses={
        404: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
    tags=["assess"],
)
async def export_pdf(
    run_id: str,
    run_store: Annotated[RunStore, Depends(get_run_store)],
) -> Response:
    """Render the persisted assessment as a PDF (WeasyPrint).

    Returns HTTP 503 with a typed body when the PDF rendering stack
    (Pango/Cairo/GDK-PixBuf) is not installed on the host. Use the
    `/assess/{run_id}/export.md` endpoint as a fallback.
    """
    report = await run_store.get_report(run_id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "report_not_found", "message": f"no report for run_id={run_id}"},
        )
    try:
        doc = render_pdf_document(report)
    except PdfRenderingUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "pdf_rendering_unavailable", "message": str(exc)},
        ) from exc
    return Response(
        content=doc.body,
        media_type=doc.media_type,
        headers={"Content-Disposition": f'attachment; filename="{doc.filename}"'},
    )


@router.get(
    "/metrics",
    response_class=PlainTextResponse,
    tags=["service"],
    responses={200: {"content": {"text/plain": {"example": "# TYPE ..."}}}},
)
async def metrics(
    telemetry: Annotated[Telemetry, Depends(get_telemetry_dep)],
) -> PlainTextResponse:
    """Prometheus 0.0.4 text format. Scrape this from kube-prometheus / Grafana Cloud."""
    return PlainTextResponse(telemetry.render_prometheus(), media_type="text/plain; version=0.0.4")


@router.get(
    "/drift",
    response_model=DriftResponse,
    tags=["service"],
)
async def drift(
    tracker: Annotated[DriftTracker, Depends(get_drift_tracker)],
) -> DriftResponse:
    """
    Rolling input-domain + tier-mix distributions over a sliding window.

    Phase 10 surface for the drift dashboard. Compared against the eval gold
    set's domain / tier mix to flag distribution shifts that warrant a
    re-calibration of the rules layer or the LLM-as-judge.
    """
    snapshot = tracker.snapshot()
    return DriftResponse(
        window_size=snapshot.window_size,
        sample_count=snapshot.sample_count,
        input_domain=snapshot.input_domain,
        tier_mix=snapshot.tier_mix,
    )
