"""
Live LLM integration test.

Skipped unless BOUSSOLE_LLM_URL is set. Two ways to run:

  Linux/GPU: docker compose --profile llm up vllm
             BOUSSOLE_LLM_URL=http://localhost:8001 \
               BOUSSOLE_LLM_MODEL=mistralai/Mistral-7B-Instruct-v0.3 \
               make integration-test

  Mac (Apple Silicon): ollama serve (in another shell), then
             ollama pull mistral:7b-instruct
             BOUSSOLE_LLM_URL=http://localhost:11434 \
               BOUSSOLE_LLM_MODEL=mistral:7b-instruct \
               make integration-test

Asserts (CLAUDE.md plan, Phase 3 checkpoint):
  - the adapter completes a real call through the LLMProvider port
  - the same prompt produces identical output across two runs at temperature 0
"""

from __future__ import annotations

import os

import pytest

from backend.adapters.vllm_provider import SelfHostedVLLM

pytestmark = pytest.mark.integration


def _env_url() -> str | None:
    return os.environ.get("BOUSSOLE_LLM_URL")


def _env_model() -> str:
    return os.environ.get("BOUSSOLE_LLM_MODEL", "mistralai/Mistral-7B-Instruct-v0.3")


@pytest.fixture()
def live_llm() -> SelfHostedVLLM:
    url = _env_url()
    if not url:
        pytest.skip("BOUSSOLE_LLM_URL not set; live LLM integration test skipped")
    api_key = os.environ.get("BOUSSOLE_LLM_API_KEY")
    return SelfHostedVLLM(url, model_id=_env_model(), api_key=api_key, timeout_seconds=120.0)


async def test_live_complete_returns_text(live_llm: SelfHostedVLLM) -> None:
    async with live_llm as llm:
        response = await llm.complete(
            "Answer in one word. What is the capital of France?",
            max_tokens=8,
        )
    assert response.text.strip()
    assert response.usage.tokens_out >= 1


async def test_live_temperature_zero_is_deterministic(live_llm: SelfHostedVLLM) -> None:
    """Two identical calls at temperature 0 must produce the same text."""
    prompt = (
        "You are a precise classifier. Respond with exactly one token: HIGH or LOW. "
        "Is this system high-risk under the AI Act: 'AI used to recruit candidates'? "
        "Answer:"
    )
    async with live_llm as llm:
        first = await llm.complete(prompt, max_tokens=4)
        second = await llm.complete(prompt, max_tokens=4)
    assert first.text == second.text, (
        f"temperature=0 calls disagreed: {first.text!r} vs {second.text!r}"
    )
