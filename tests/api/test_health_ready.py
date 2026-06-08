"""/health and /ready return their expected shapes."""

from __future__ import annotations

from tests.api.conftest import ApiEnv


async def test_health_ok(api_env: ApiEnv) -> None:
    response = await api_env.client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_ready_reports_run_store_check(api_env: ApiEnv) -> None:
    response = await api_env.client.get("/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["checks"] == {"run_store": True}
