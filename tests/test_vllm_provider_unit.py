"""
Unit tests for SelfHostedVLLM.

Verifies the adapter's HTTP contract (request shape, response parsing,
temperature plumbing, deterministic seeding) without a live LLM server.
The live-server integration test lives under tests/integration/.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from backend.adapters.vllm_provider import LLMProviderError, SelfHostedVLLM
from backend.ports.llm_provider import LLMProvider


def _make_handler(
    response_body: dict[str, Any] | None = None,
    *,
    status: int = 200,
    capture: list[dict[str, Any]] | None = None,
) -> httpx.MockTransport:
    body = response_body or _ok_response("hello")

    def handler(request: httpx.Request) -> httpx.Response:
        if capture is not None:
            capture.append(
                {
                    "method": request.method,
                    "url": str(request.url),
                    "json": json.loads(request.content.decode("utf-8")) if request.content else {},
                }
            )
        return httpx.Response(status_code=status, json=body)

    return httpx.MockTransport(handler)


def _ok_response(text: str, *, model: str = "test-model") -> dict[str, Any]:
    return {
        "id": "cmpl-1",
        "object": "chat.completion",
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": text},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 3, "completion_tokens": 5, "total_tokens": 8},
    }


@pytest.fixture()
def captured() -> list[dict[str, Any]]:
    return []


def _client_with(transport: httpx.MockTransport) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url="http://test.local",
        transport=transport,
        headers={"Content-Type": "application/json"},
    )


async def test_complete_posts_chat_completions_with_temperature_zero(
    captured: list[dict[str, Any]],
) -> None:
    transport = _make_handler(_ok_response("pong"), capture=captured)
    async with SelfHostedVLLM(
        "http://test.local", model_id="test-model", client=_client_with(transport)
    ) as llm:
        response = await llm.complete("ping")

    assert response.text == "pong"
    assert response.model_id == "test-model"
    assert response.usage.tokens_in == 3
    assert response.usage.tokens_out == 5
    assert response.finish_reason == "stop"

    assert len(captured) == 1
    payload = captured[0]["json"]
    assert payload["temperature"] == 0.0
    assert payload["stream"] is False
    assert payload["messages"] == [{"role": "user", "content": "ping"}]
    assert payload["seed"] == 7
    assert captured[0]["url"].endswith("/v1/chat/completions")


async def test_creative_complete_uses_supplied_temperature_and_drops_seed(
    captured: list[dict[str, Any]],
) -> None:
    transport = _make_handler(_ok_response("drafted"), capture=captured)
    async with SelfHostedVLLM(
        "http://test.local", model_id="test-model", client=_client_with(transport)
    ) as llm:
        response = await llm.creative_complete("draft", temperature=0.7)

    assert response.text == "drafted"
    payload = captured[0]["json"]
    assert payload["temperature"] == 0.7
    assert "seed" not in payload, "seed should only be sent at temperature=0"


async def test_stop_sequences_are_forwarded(captured: list[dict[str, Any]]) -> None:
    transport = _make_handler(_ok_response("x"), capture=captured)
    async with SelfHostedVLLM(
        "http://test.local", model_id="test-model", client=_client_with(transport)
    ) as llm:
        await llm.complete("ping", max_tokens=32, stop=["</done>"])

    payload = captured[0]["json"]
    assert payload["stop"] == ["</done>"]
    assert payload["max_tokens"] == 32


async def test_determinism_two_calls_at_temperature_zero_send_identical_payloads(
    captured: list[dict[str, Any]],
) -> None:
    transport = _make_handler(_ok_response("same"), capture=captured)
    async with SelfHostedVLLM(
        "http://test.local", model_id="test-model", client=_client_with(transport)
    ) as llm:
        a = await llm.complete("identical")
        b = await llm.complete("identical")

    assert a == b
    assert len(captured) == 2
    assert captured[0]["json"] == captured[1]["json"], (
        "two complete() calls with the same prompt must produce identical requests"
    )


async def test_http_error_raises_provider_error() -> None:
    transport = _make_handler({"error": "internal"}, status=500)
    async with SelfHostedVLLM(
        "http://test.local", model_id="test-model", client=_client_with(transport)
    ) as llm:
        with pytest.raises(LLMProviderError) as exc:
            await llm.complete("ping")
    assert "HTTP 500" in str(exc.value)


async def test_empty_choices_raises_provider_error() -> None:
    transport = _make_handler({"choices": []})
    async with SelfHostedVLLM(
        "http://test.local", model_id="test-model", client=_client_with(transport)
    ) as llm:
        with pytest.raises(LLMProviderError):
            await llm.complete("ping")


async def test_adapter_satisfies_llm_provider_protocol() -> None:
    transport = _make_handler(_ok_response("ok"))
    async with SelfHostedVLLM(
        "http://test.local", model_id="test-model", client=_client_with(transport)
    ) as llm:
        assert isinstance(llm, LLMProvider)
