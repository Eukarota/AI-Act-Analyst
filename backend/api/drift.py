"""
Rolling distribution tracker for drift telemetry.

CLAUDE.md section 12.4: "Track input-domain and tier-mix distributions for
drift." We keep a sliding window of recent assessments and expose two
distributions (input-domain, tier-mix) plus the sample count. Compared
against the gold-set distribution from `eval/gold_set.jsonl`, this is the
operator's signal that the production traffic has moved away from what
the rules layer was calibrated against.

Implementation is a deque + counter pair. Thread-safe via a single lock;
async runners call from the event loop's thread, so contention is moot
for the production load profile (single-digit RPS per worker).
"""

from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass
from threading import Lock


@dataclass(frozen=True)
class DriftSnapshot:
    """Distribution snapshot at the moment /drift is read."""

    window_size: int
    sample_count: int
    input_domain: dict[str, float]
    tier_mix: dict[str, float]


class DriftTracker:
    """Sliding-window counters over (input_domain, tier) pairs."""

    def __init__(self, *, window_size: int = 500) -> None:
        self._window_size = window_size
        self._domain_window: deque[str] = deque(maxlen=window_size)
        self._tier_window: deque[str] = deque(maxlen=window_size)
        self._lock = Lock()

    @property
    def window_size(self) -> int:
        return self._window_size

    def record(self, *, domain: str | None, tier: str | None) -> None:
        with self._lock:
            self._domain_window.append(domain or "unknown")
            self._tier_window.append(tier or "unknown")

    def snapshot(self) -> DriftSnapshot:
        with self._lock:
            domain_counter = Counter(self._domain_window)
            tier_counter = Counter(self._tier_window)
            total = sum(domain_counter.values())
        return DriftSnapshot(
            window_size=self._window_size,
            sample_count=total,
            input_domain=_normalise(domain_counter, total),
            tier_mix=_normalise(tier_counter, total),
        )


def _normalise(counter: Counter[str], total: int) -> dict[str, float]:
    if total == 0:
        return {}
    return {k: round(v / total, 4) for k, v in counter.most_common()}
