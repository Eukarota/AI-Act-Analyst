"""Unit tests for telemetry + drift + /metrics + /drift."""

from __future__ import annotations

from backend.api.drift import DriftTracker
from backend.api.telemetry import Telemetry
from tests.api.conftest import ApiEnv
from tests.api.test_assess_route import (
    RECRUITMENT_ATTRIBUTES,
    RECRUITMENT_DESCRIPTION,
)


def test_telemetry_render_includes_counter_after_inc() -> None:
    telemetry = Telemetry()
    telemetry.inc("boussole_assess_total", {"status": "complete"})
    rendered = telemetry.render_prometheus()
    assert "# TYPE boussole_assess_total counter" in rendered
    assert 'boussole_assess_total{status="complete"} 1' in rendered


def test_telemetry_render_histogram_after_observe() -> None:
    telemetry = Telemetry()
    telemetry.observe("boussole_assess_latency_seconds", 0.12)
    rendered = telemetry.render_prometheus()
    assert "# TYPE boussole_assess_latency_seconds histogram" in rendered
    assert "boussole_assess_latency_seconds_count 1" in rendered


def test_drift_snapshot_normalises_window() -> None:
    tracker = DriftTracker(window_size=4)
    tracker.record(domain="employment", tier="high_risk_annex_iii")
    tracker.record(domain="employment", tier="high_risk_annex_iii")
    tracker.record(domain="consumer", tier="transparency")
    snapshot = tracker.snapshot()
    assert snapshot.sample_count == 3
    assert snapshot.input_domain["employment"] == 0.6667
    assert snapshot.tier_mix["high_risk_annex_iii"] == 0.6667


def test_drift_window_caps_oldest_entries() -> None:
    tracker = DriftTracker(window_size=2)
    tracker.record(domain="a", tier="t1")
    tracker.record(domain="b", tier="t2")
    tracker.record(domain="c", tier="t3")
    snapshot = tracker.snapshot()
    assert snapshot.sample_count == 2
    assert "a" not in snapshot.input_domain


async def test_metrics_endpoint_returns_prometheus_text(api_env: ApiEnv) -> None:
    api_env.script_extraction(RECRUITMENT_DESCRIPTION, RECRUITMENT_ATTRIBUTES)
    await api_env.client.post(
        "/assess",
        json={
            "system_description": RECRUITMENT_DESCRIPTION,
            "declared_controls": [],
            "declared_actor_role": "provider",
        },
    )

    response = await api_env.client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    body = response.text
    assert "boussole_assess_total" in body
    assert 'status="complete"' in body
    assert "boussole_assess_latency_seconds_count 1" in body
    assert "boussole_tier_mix_total" in body


async def test_drift_endpoint_tracks_recent_assessments(api_env: ApiEnv) -> None:
    api_env.script_extraction(RECRUITMENT_DESCRIPTION, RECRUITMENT_ATTRIBUTES)
    await api_env.client.post(
        "/assess",
        json={
            "system_description": RECRUITMENT_DESCRIPTION,
            "declared_controls": [],
            "declared_actor_role": "provider",
        },
    )

    response = await api_env.client.get("/drift")
    assert response.status_code == 200
    body = response.json()
    assert body["sample_count"] == 1
    assert body["window_size"] >= 1
    assert body["tier_mix"].get("high_risk_annex_iii") == 1.0
