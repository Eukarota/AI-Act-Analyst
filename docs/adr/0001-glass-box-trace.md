# 0001: The trace is the product

Date: 2026-06-09
Status: Accepted

## Context

CLAUDE.md section 2 puts a hard constraint on the project: a skeptical
compliance officer must trust the system after five minutes. The
inference is that a clean answer panel is not enough. The buyer reads
the path to the answer.

Most agent frameworks (CrewAI, AutoGen, opaque LangChain chains) hide
the path behind a clean final string. That posture is the opposite of
what this buyer needs.

## Decision

Every node in the LangGraph state machine emits a typed `TraceEvent`
through a single emitter (`backend/agent/trace.py`). Every tool call
emits a tool_call + tool_return pair with input + output hashes,
latency, and token counts. Every grounding check emits a
grounding_check event. The trace event schema is a public API: additive
changes only, version bump otherwise.

The same event stream is:

1. Stored in `agent_state.trace_events` for the API response.
2. Persisted in Postgres by `PostgresRunStore.save` so `/trace/{run_id}`
   serves the historical view.
3. Surfaced verbatim in the Next.js UI as the glass-box timeline.
4. Exported through OpenTelemetry spans for production observability.

One source of truth, four consumers. Demo logging and prod logging do
not diverge.

## Consequences

Positive:

- The UI does not "demo well in a happy path and fall over in
  production": the trace IS the product, and it works on a single
  representative run.
- A wrong classification is debuggable from the trace alone: which
  attributes were extracted, which rule fired, which retrieval calls
  ran, which passages came back, which grounding check failed.
- The eval can compare any production trace against any gold trace
  without instrumentation work.

Negative:

- The trace schema must be versioned and treated as a contract. Field
  renames are breaking changes.
- Storing the full trace per assessment grows the run-manifest table.
  Acceptable: per-row size is small (JSONB compresses well) and the
  retention policy is operator-controlled.
