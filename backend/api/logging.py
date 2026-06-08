"""
Structured JSON logging via structlog.

CLAUDE.md section 12.3: "structured JSON logs correlated by run_id".
Every log call inside a request flow is bound to the run_id of the
in-flight assessment; the trace emitter already does the same so the
two streams correlate without any glue code.
"""

from __future__ import annotations

import logging

import structlog
from structlog.types import EventDict, WrappedLogger


def _drop_color_message(_: WrappedLogger, __: str, event_dict: EventDict) -> EventDict:
    event_dict.pop("color_message", None)
    return event_dict


def configure_logging(*, level: str = "INFO") -> None:
    """Idempotent setup. Safe to call on every app startup."""
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, level.upper(), logging.INFO),
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            _drop_color_message,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
