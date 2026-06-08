# 0006: Process-local Prometheus + LRU retrieval cache

Date: 2026-06-09
Status: Accepted (Phase 10)

## Context

CLAUDE.md section 12.4 requires four production hygiene properties:

1. A re-index produces a diff report and auto-triggers an eval re-run.
2. A retrieval cache keyed by `corpus_version`.
3. Per-request telemetry: latency, token cost, retrieval hit count,
   groundedness flag; plus alerts on violations, p95, and cost.
4. Drift tracking of input-domain and tier-mix distributions.

The temptation at this size is to depend on `prometheus_client`,
`redis`, and a hosted observability vendor. That trades the sovereign
posture for engineering convenience and adds three Cloud-Act-exposed
runtime dependencies.

## Decision

- The metrics surface is a process-local `Telemetry` object that
  renders Prometheus 0.0.4 text directly. Exposed at `/metrics`.
  No external library; no client-side aggregation lost when a worker
  recycles. Kube-prometheus / Grafana Cloud scrape it like any other
  Prometheus target.
- The retrieval cache is `CachingRetriever`, a `HybridRetriever`
  subclass with an `OrderedDict` LRU keyed by
  `(corpus_version, scope, sha256(query))`. A re-index changes the key
  by construction; the explicit `invalidate()` is reserved for forced
  flushes (prompt rollback, manual operator action).
- The drift tracker is a process-local sliding-window counter exposed
  at `/drift`. Sample window defaults to 500.
- The corpus diff is computed per chunk against a JSON snapshot the
  previous re-index wrote. Output is grouped by Article / Annex /
  Recital so a compliance reviewer can match it to a published
  amendment table without parsing JSON.
- The eval re-run is triggered by a separate orchestrator script
  (`scripts/reindex_and_eval.py`) so CI can stage it as a distinct
  pipeline step. Either CI runs the two stages, or the operator runs
  the orchestrator locally; the eval is never embedded in the indexer.

## Consequences

Positive:

- Zero new runtime dependencies. The sovereign posture stays clean.
- Cache and metrics state are visible per pod, which is the right
  granularity for an HPA-managed deployment: aggregation happens
  Prometheus-side, not in our code.
- The corpus diff is human-readable Markdown out of the box. Compliance
  review does not need a viewer.

Negative:

- The cache is process-local. Horizontal scaling does not share entries.
  A future iteration can add a shared L2 (Redis on the same sovereign
  cloud) without changing the call sites: `CachingRetriever` already
  isolates the cache behind one class.
- The Prometheus exporter implements only counters and one histogram.
  Adding summaries or gauges means extending `Telemetry`. The histogram
  bucket choice is opinionated; tune via env once a real LLM is hot.
- The drift tracker is not durable. A pod restart resets the window.
  Acceptable: drift is a slow signal evaluated on dashboards, not a
  paging metric.
