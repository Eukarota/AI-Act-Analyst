"""
Shared helpers for graph nodes.

Each node is an async function that takes AgentState plus its
AgentDependencies and returns a dict of state-fields to update. The graph
runtime merges that dict into the working state.

These helpers keep the per-node files focused on their actual logic:
trace emission boilerplate, timeout wrapping, and tool-call counting all
live here.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

from backend.agent.errors import NodeTimeout
from backend.agent.state import AgentState
from backend.agent.trace import TraceEmitter, TraceEventKind, hash_payload

T = TypeVar("T")


async def run_with_timeout(
    coro: Awaitable[T],
    *,
    timeout_seconds: float,
    node_name: str,
) -> T:
    try:
        return await asyncio.wait_for(coro, timeout=timeout_seconds)
    except TimeoutError as exc:
        raise NodeTimeout(f"node {node_name!r} exceeded {timeout_seconds:.0f}s timeout") from exc


def emitter_for(state: AgentState) -> TraceEmitter:
    """Build a TraceEmitter that appends to this state's trace_events list."""
    return TraceEmitter(run_id=state.run_id, sink=list(state.trace_events))


def emit_tool_call(
    emitter: TraceEmitter,
    *,
    name: str,
    inputs: object,
    model_id: str | None = None,
) -> str:
    """Emit a TOOL_CALL event and return the input_hash for symmetry with TOOL_RETURN."""
    digest = hash_payload(inputs)
    emitter.emit(
        TraceEventKind.TOOL_CALL,
        name=name,
        input_hash=digest,
        model_id=model_id,
    )
    return digest


def emit_tool_return(
    emitter: TraceEmitter,
    *,
    name: str,
    outputs: object,
    latency_ms: float | None = None,
    model_id: str | None = None,
) -> str:
    digest = hash_payload(outputs)
    emitter.emit(
        TraceEventKind.TOOL_RETURN,
        name=name,
        output_hash=digest,
        latency_ms=latency_ms,
        model_id=model_id,
    )
    return digest


NodeFn = Callable[..., Awaitable[dict[str, object]]]
