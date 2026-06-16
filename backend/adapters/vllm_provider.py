"""
Self-hosted OpenAI-compatible LLM adapter (Phase 3).

CLAUDE.md section 12.3: "extraction/classification LLM calls at temperature 0".
This adapter defaults temperature to 0 for complete() and exposes a separate
creative_complete() path that only draft_documentation is permitted to call.

Server compatibility:
  Production: vLLM serving an open Mistral weight (see docker-compose.dev.yml,
              profile 'llm', exposes :8001 -> /v1/...).
  Mac dev:    Apple Silicon cannot run the vLLM CUDA image. Run Ollama
              (https://ollama.com) locally: `ollama serve` exposes :11434
              with a /v1/chat/completions OpenAI-compatible endpoint. Point
              BOUSSOLE_LLM_URL at it.

The class name remains SelfHostedVLLM because that is the production target;
the protocol it speaks is /v1/chat/completions, which vLLM, Ollama, and
text-generation-inference all implement identically.

Determinism:
  At temperature=0 vLLM does greedy decoding -> deterministic output for the
  same (prompt, model_id, server build). vLLM and Ollama additionally accept
  a `seed` field; Mistral La Plateforme rejects it with a 422 (strict
  schema). Because of that, `send_seed` defaults to False: temperature=0 is
  enough for determinism, and the request is portable across all three
  servers. Callers running against vLLM or Ollama can opt back in by
  constructing with `send_seed=True` (or by setting
  BOUSSOLE_LLM_SEND_SEED=true in the environment).
"""

from __future__ import annotations

from typing import Any

import httpx

from backend.ports.llm_provider import LLMResponse, LLMUsage

DEFAULT_TIMEOUT_SECONDS = 60.0
DEFAULT_DETERMINISM_SEED = 7
DEFAULT_SEND_SEED = False


class LLMProviderError(RuntimeError):
    """Raised when the upstream server returns an error or unexpected payload."""


class SelfHostedVLLM:
    """OpenAI-compatible /v1/chat/completions client for self-hosted LLM servers."""

    def __init__(
        self,
        base_url: str,
        *,
        model_id: str,
        api_key: str | None = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        seed: int | None = DEFAULT_DETERMINISM_SEED,
        send_seed: bool = DEFAULT_SEND_SEED,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model_id = model_id
        self.timeout_seconds = timeout_seconds
        self.seed = seed
        self.send_seed = send_seed
        self._api_key = api_key
        self._client = client
        self._owns_client = client is None

    async def __aenter__(self) -> SelfHostedVLLM:
        await self._ensure_client()
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            headers: dict[str, str] = {"Content-Type": "application/json"}
            if self._api_key:
                headers["Authorization"] = f"Bearer {self._api_key}"
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout_seconds,
                headers=headers,
            )
            self._owns_client = True
        return self._client

    async def complete(
        self,
        prompt: str,
        *,
        max_tokens: int = 1024,
        stop: list[str] | None = None,
    ) -> LLMResponse:
        return await self._chat_completion(
            prompt=prompt, max_tokens=max_tokens, temperature=0.0, stop=stop
        )

    async def creative_complete(
        self,
        prompt: str,
        *,
        max_tokens: int = 1024,
        temperature: float = 0.4,
        stop: list[str] | None = None,
    ) -> LLMResponse:
        return await self._chat_completion(
            prompt=prompt, max_tokens=max_tokens, temperature=temperature, stop=stop
        )

    async def _chat_completion(
        self,
        *,
        prompt: str,
        max_tokens: int,
        temperature: float,
        stop: list[str] | None,
    ) -> LLMResponse:
        client = await self._ensure_client()
        payload: dict[str, Any] = {
            "model": self.model_id,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        if stop:
            payload["stop"] = stop
        if self.send_seed and self.seed is not None and temperature == 0.0:
            payload["seed"] = self.seed

        try:
            response = await client.post("/v1/chat/completions", json=payload)
        except httpx.HTTPError as exc:
            raise LLMProviderError(f"LLM request failed: {exc}") from exc

        if response.status_code >= 400:
            raise LLMProviderError(
                f"LLM server returned HTTP {response.status_code}: {response.text[:200]}"
            )

        try:
            body = response.json()
        except ValueError as exc:
            raise LLMProviderError(f"LLM server returned non-JSON body: {exc}") from exc

        return _parse_chat_response(body, requested_model=self.model_id)


def _parse_chat_response(body: dict[str, Any], *, requested_model: str) -> LLMResponse:
    choices = body.get("choices") or []
    if not choices:
        raise LLMProviderError("LLM response had no choices")
    first = choices[0]
    message = first.get("message") or {}
    text = message.get("content") or first.get("text") or ""
    if not isinstance(text, str):
        raise LLMProviderError("LLM response message.content was not a string")

    usage = body.get("usage") or {}
    tokens_in = int(usage.get("prompt_tokens") or 0)
    tokens_out = int(usage.get("completion_tokens") or 0)
    served_model = body.get("model") or requested_model
    finish_reason = str(first.get("finish_reason") or "stop")

    return LLMResponse(
        text=text,
        model_id=str(served_model),
        usage=LLMUsage(tokens_in=tokens_in, tokens_out=tokens_out),
        finish_reason=finish_reason,
    )
