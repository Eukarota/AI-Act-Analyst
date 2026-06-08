"""
Trace event schema and OpenTelemetry emitter.

Defined in Phase 1 because every later phase emits trace events using these
exact types. The trace is the product (glass-box) so the schema is an API:
additive changes only without a version bump (CLAUDE.md section 9).
"""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

import structlog
from opentelemetry import trace as otel_trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)
from pydantic import BaseModel, ConfigDict, Field

TRACE_SCHEMA_VERSION = "1.0.0"

_log = structlog.get_logger(__name__)


class TraceEventKind(StrEnum):
    NODE_START = "node_start"
    NODE_END = "node_end"
    TOOL_CALL = "tool_call"
    TOOL_RETURN = "tool_return"
    LLM_CALL = "llm_call"
    RETRIEVAL = "retrieval"
    CLASSIFICATION = "classification"
    GROUNDING_CHECK = "grounding_check"
    CLARIFICATION = "clarification"
    ERROR = "error"


class TraceEvent(BaseModel):
    """
    A single trace event. Same shape feeds the UI panel and prod observability.

    Do not add required fields; new optional fields only.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: str = TRACE_SCHEMA_VERSION
    event_id: str = Field(default_factory=lambda: uuid4().hex)
    run_id: str
    span_id: str
    parent_span_id: str | None = None
    kind: TraceEventKind
    name: str
    timestamp: datetime
    latency_ms: float | None = None
    input_hash: str | None = None
    output_hash: str | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None
    model_id: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)


def hash_payload(payload: Any) -> str:
    """Stable hash of an arbitrary JSON-serialisable payload."""
    blob = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:16]


def _install_tracer_provider() -> otel_trace.Tracer:
    provider = otel_trace.get_tracer_provider()
    if not isinstance(provider, TracerProvider):
        provider = TracerProvider()
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
        otel_trace.set_tracer_provider(provider)
    return otel_trace.get_tracer("boussole.agent")


_tracer = _install_tracer_provider()


class TraceEmitter:
    """
    Per-run collector. Appends to AgentState.trace_events and emits OTel spans.

    Two outputs from one source: the in-memory list powers the UI panel; the
    OTel spans go to whatever exporter is configured in prod.
    """

    def __init__(self, run_id: str, sink: list[dict[str, Any]] | None = None) -> None:
        self.run_id = run_id
        self.sink: list[dict[str, Any]] = sink if sink is not None else []
        self._current_span_id: str | None = None

    def emit(
        self,
        kind: TraceEventKind,
        name: str,
        attributes: dict[str, Any] | None = None,
        *,
        latency_ms: float | None = None,
        input_hash: str | None = None,
        output_hash: str | None = None,
        tokens_in: int | None = None,
        tokens_out: int | None = None,
        model_id: str | None = None,
        span_id: str | None = None,
        parent_span_id: str | None = None,
    ) -> TraceEvent:
        event = TraceEvent(
            run_id=self.run_id,
            span_id=span_id or uuid4().hex,
            parent_span_id=parent_span_id or self._current_span_id,
            kind=kind,
            name=name,
            timestamp=datetime.now(UTC),
            latency_ms=latency_ms,
            input_hash=input_hash,
            output_hash=output_hash,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            model_id=model_id,
            attributes=attributes or {},
        )
        self.sink.append(event.model_dump(mode="json"))
        _log.info("trace_event", **event.model_dump(mode="json"))
        return event

    @contextmanager
    def node(
        self,
        name: str,
        attributes: dict[str, Any] | None = None,
    ) -> Iterator[str]:
        """Context manager that brackets a node's execution with start/end events."""
        span_id = uuid4().hex
        outer_parent = self._current_span_id
        self._current_span_id = span_id
        started = time.perf_counter()
        self.emit(
            TraceEventKind.NODE_START,
            name=name,
            attributes=attributes,
            span_id=span_id,
            parent_span_id=outer_parent,
        )
        with _tracer.start_as_current_span(name):
            try:
                yield span_id
            except Exception as exc:
                self.emit(
                    TraceEventKind.ERROR,
                    name=f"{name}.error",
                    attributes={"error_type": type(exc).__name__, "message": str(exc)},
                    parent_span_id=span_id,
                )
                raise
            finally:
                latency_ms = (time.perf_counter() - started) * 1000.0
                self.emit(
                    TraceEventKind.NODE_END,
                    name=name,
                    span_id=span_id,
                    parent_span_id=outer_parent,
                    latency_ms=latency_ms,
                )
                self._current_span_id = outer_parent
