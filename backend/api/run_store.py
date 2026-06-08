"""
Run store: persistence port for assessment reports + traces.

CLAUDE.md section 12.3 requires the service to be stateless: "per-request
state lives in the payload/DB, not process memory => horizontal scale".
This module is the DB half of that contract. Two backends ship in Phase 7:

  - PostgresRunStore: the production target (managed Postgres on OVH).
  - InMemoryRunStore: tests + local dev when the developer does not want
    to bring up the Postgres container.

The shape persisted is the same shape served by GET /trace/{run_id}: the
full AssessmentReport plus the verbatim trace event stream. We store both
as JSONB so we can evolve the report schema without writing migrations
for every additive field.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any, Protocol, runtime_checkable

import asyncpg

from backend.agent.report import AssessmentReport

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS assessment_runs (
    run_id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    grounding_passed BOOLEAN NOT NULL,
    corpus_version TEXT NOT NULL,
    model_id TEXT NOT NULL,
    prompt_set_version TEXT NOT NULL,
    rules_version TEXT NOT NULL,
    report JSONB NOT NULL,
    trace_events JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS assessment_runs_created_at_idx
    ON assessment_runs (created_at DESC);
"""


@runtime_checkable
class RunStore(Protocol):
    """Persistence port. /assess writes, /trace reads."""

    async def save(
        self,
        report: AssessmentReport,
        trace_events: Sequence[dict[str, Any]],
    ) -> None: ...

    async def get_report(self, run_id: str) -> AssessmentReport | None: ...

    async def get_trace(self, run_id: str) -> list[dict[str, Any]] | None: ...

    async def ping(self) -> bool: ...


class InMemoryRunStore:
    """Process-local store. Tests use this; production never does."""

    def __init__(self) -> None:
        self._reports: dict[str, AssessmentReport] = {}
        self._traces: dict[str, list[dict[str, Any]]] = {}

    async def save(
        self,
        report: AssessmentReport,
        trace_events: Sequence[dict[str, Any]],
    ) -> None:
        self._reports[report.run_id] = report
        self._traces[report.run_id] = list(trace_events)

    async def get_report(self, run_id: str) -> AssessmentReport | None:
        return self._reports.get(run_id)

    async def get_trace(self, run_id: str) -> list[dict[str, Any]] | None:
        events = self._traces.get(run_id)
        return list(events) if events is not None else None

    async def ping(self) -> bool:
        return True


class PostgresRunStore:
    """asyncpg-backed run store. Same JSON shape as InMemoryRunStore."""

    def __init__(self, dsn: str) -> None:
        self.dsn = dsn
        self._pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        if self._pool is None:
            self._pool = await asyncpg.create_pool(self.dsn, min_size=1, max_size=8)
            await self.ensure_schema()

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    def _pool_required(self) -> asyncpg.Pool:
        if self._pool is None:
            raise RuntimeError("PostgresRunStore.connect() must be called before use.")
        return self._pool

    async def ensure_schema(self) -> None:
        pool = self._pool_required()
        async with pool.acquire() as conn:
            await conn.execute(_SCHEMA_SQL)

    async def save(
        self,
        report: AssessmentReport,
        trace_events: Sequence[dict[str, Any]],
    ) -> None:
        pool = self._pool_required()
        report_json = report.model_dump_json()
        trace_json = json.dumps(list(trace_events), default=str)
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO assessment_runs (
                    run_id, status, grounding_passed,
                    corpus_version, model_id, prompt_set_version, rules_version,
                    report, trace_events
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb, $9::jsonb)
                ON CONFLICT (run_id) DO UPDATE SET
                    status = EXCLUDED.status,
                    grounding_passed = EXCLUDED.grounding_passed,
                    report = EXCLUDED.report,
                    trace_events = EXCLUDED.trace_events
                """,
                report.run_id,
                report.status.value,
                report.grounding_passed,
                report.manifest.corpus_version,
                report.manifest.model_id,
                report.manifest.prompt_set_version,
                report.manifest.rules_version,
                report_json,
                trace_json,
            )

    async def get_report(self, run_id: str) -> AssessmentReport | None:
        pool = self._pool_required()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT report FROM assessment_runs WHERE run_id = $1",
                run_id,
            )
        if row is None:
            return None
        raw = row["report"]
        return (
            AssessmentReport.model_validate_json(raw)
            if isinstance(raw, str)
            else (AssessmentReport.model_validate(raw))
        )

    async def get_trace(self, run_id: str) -> list[dict[str, Any]] | None:
        pool = self._pool_required()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT trace_events FROM assessment_runs WHERE run_id = $1",
                run_id,
            )
        if row is None:
            return None
        raw = row["trace_events"]
        if isinstance(raw, str):
            parsed: Any = json.loads(raw)
            return list(parsed) if isinstance(parsed, list) else None
        return list(raw) if isinstance(raw, list) else None

    async def ping(self) -> bool:
        if self._pool is None:
            return False
        async with self._pool.acquire() as conn:
            value = await conn.fetchval("SELECT 1")
            return bool(value == 1)
