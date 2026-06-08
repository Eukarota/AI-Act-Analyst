"""
Process-local Prometheus-text telemetry.

CLAUDE.md section 12.4: "per-request latency, token cost, retrieval hit
count, groundedness flag; alerts on any groundedness violation, p95
latency, and cost/assessment. Track input-domain and tier-mix distributions
for drift."

We implement the bare minimum here so the Prometheus surface is real
without dragging in the `prometheus_client` package. The exporter writes
the Prometheus 0.0.4 text format, which Grafana Cloud, kube-prometheus,
and prom-scrape all read. The metric set:

  boussole_assess_total{status}        counter, terminal status per assessment
  boussole_grounding_violations_total  counter, online grounding failures
  boussole_assess_latency_seconds      histogram, end-to-end runner latency
  boussole_llm_tokens_total{kind}      counter, tokens in / out across runs
  boussole_retrieval_cache_hits_total  counter
  boussole_retrieval_cache_misses_total counter
  boussole_input_domain_total{domain}  counter, drift signal on inputs
  boussole_tier_mix_total{tier}        counter, drift signal on outputs

The histogram buckets target the latency budget (sub-second p50,
~5 s p95 for the FakeLLM smoke; real LLMs widen p95 quickly which is
exactly why the budget needs eyes).
"""

from __future__ import annotations

from bisect import bisect_left
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from threading import Lock

DEFAULT_LATENCY_BUCKETS: tuple[float, ...] = (
    0.05,
    0.1,
    0.25,
    0.5,
    1.0,
    2.5,
    5.0,
    10.0,
    30.0,
    60.0,
)


@dataclass
class _Histogram:
    """Cumulative histogram in the Prometheus convention."""

    buckets: tuple[float, ...]
    counts: list[int] = field(default_factory=list)
    sum: float = 0.0
    count: int = 0

    def __post_init__(self) -> None:
        self.counts = [0] * len(self.buckets)

    def observe(self, value: float) -> None:
        idx = bisect_left(self.buckets, value)
        if idx < len(self.counts):
            self.counts[idx] += 1
        self.sum += value
        self.count += 1


class Telemetry:
    """Singleton-ish container. Hold one per process."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._counters: dict[str, dict[tuple[tuple[str, str], ...], int]] = defaultdict(
            lambda: defaultdict(int)
        )
        self._histograms: dict[str, _Histogram] = {
            "boussole_assess_latency_seconds": _Histogram(DEFAULT_LATENCY_BUCKETS),
        }

    def inc(self, name: str, labels: dict[str, str] | None = None, *, value: int = 1) -> None:
        key = tuple(sorted((labels or {}).items()))
        with self._lock:
            self._counters[name][key] += value

    def observe(self, name: str, value: float) -> None:
        with self._lock:
            histogram = self._histograms.get(name)
            if histogram is not None:
                histogram.observe(value)

    def record_assessment(
        self,
        *,
        status: str,
        grounding_passed: bool,
        latency_seconds: float,
        tokens_in: int,
        tokens_out: int,
        retrieval_cache_hits: int,
        retrieval_cache_misses: int,
        input_domain: str | None,
        tier: str | None,
    ) -> None:
        """Single entry point Phase 7's AssessmentRunner can call once per run."""
        self.inc("boussole_assess_total", {"status": status})
        if not grounding_passed:
            self.inc("boussole_grounding_violations_total")
        self.observe("boussole_assess_latency_seconds", latency_seconds)
        if tokens_in:
            self.inc("boussole_llm_tokens_total", {"kind": "in"}, value=tokens_in)
        if tokens_out:
            self.inc("boussole_llm_tokens_total", {"kind": "out"}, value=tokens_out)
        if retrieval_cache_hits:
            self.inc("boussole_retrieval_cache_hits_total", value=retrieval_cache_hits)
        if retrieval_cache_misses:
            self.inc("boussole_retrieval_cache_misses_total", value=retrieval_cache_misses)
        if input_domain:
            self.inc("boussole_input_domain_total", {"domain": input_domain})
        if tier:
            self.inc("boussole_tier_mix_total", {"tier": tier})

    def render_prometheus(self) -> str:
        """Render the Prometheus 0.0.4 text format."""
        lines: list[str] = []
        with self._lock:
            for name in sorted(self._counters):
                lines.append(f"# TYPE {name} counter")
                for label_tuple, value in sorted(self._counters[name].items()):
                    lines.append(f"{name}{_render_labels(label_tuple)} {value}")
            for name, histogram in sorted(self._histograms.items()):
                lines.append(f"# TYPE {name} histogram")
                cumulative = 0
                for upper, count in zip(histogram.buckets, histogram.counts, strict=True):
                    cumulative += count
                    lines.append(f'{name}_bucket{{le="{_fmt_bucket(upper)}"}} {cumulative}')
                lines.append(f'{name}_bucket{{le="+Inf"}} {histogram.count}')
                lines.append(f"{name}_sum {histogram.sum:.6f}")
                lines.append(f"{name}_count {histogram.count}")
        return "\n".join(lines) + ("\n" if lines else "")


def _render_labels(label_tuple: Iterable[tuple[str, str]]) -> str:
    items = list(label_tuple)
    if not items:
        return ""
    body = ",".join(f'{k}="{_escape(v)}"' for k, v in items)
    return "{" + body + "}"


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _fmt_bucket(value: float) -> str:
    if value == int(value):
        return f"{int(value)}"
    return f"{value:g}"


_TELEMETRY: Telemetry | None = None


def get_telemetry() -> Telemetry:
    """Process-level singleton. Tests build their own."""
    global _TELEMETRY
    if _TELEMETRY is None:
        _TELEMETRY = Telemetry()
    return _TELEMETRY


def reset_telemetry() -> None:
    """Tests call this between cases."""
    global _TELEMETRY
    _TELEMETRY = None
