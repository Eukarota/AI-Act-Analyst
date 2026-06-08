"""
Deterministic in-process LLM for tests and Phase 1 smoke runs.

Scripted via a prompt -> response dict, with a defaulted echo. Never reaches
the network. Phase 3's SelfHostedVLLM replaces this for real runs; FakeLLM
remains for unit tests.
"""

from __future__ import annotations

from collections.abc import Mapping

from backend.ports.llm_provider import LLMResponse, LLMUsage


class FakeLLM:
    model_id: str = "fake-llm-v0"

    def __init__(self, scripted: Mapping[str, str] | None = None) -> None:
        self._scripted: dict[str, str] = dict(scripted or {})
        self.calls: list[tuple[str, dict[str, object]]] = []

    def script(self, prompt: str, response: str) -> None:
        self._scripted[prompt] = response

    async def complete(
        self,
        prompt: str,
        *,
        max_tokens: int = 1024,
        stop: list[str] | None = None,
    ) -> LLMResponse:
        self.calls.append(("complete", {"prompt": prompt, "max_tokens": max_tokens, "stop": stop}))
        text = self._scripted.get(prompt, f"[fake completion for: {prompt[:60]}]")
        return LLMResponse(
            text=text,
            model_id=self.model_id,
            usage=LLMUsage(tokens_in=len(prompt) // 4, tokens_out=len(text) // 4),
        )

    async def creative_complete(
        self,
        prompt: str,
        *,
        max_tokens: int = 1024,
        temperature: float = 0.4,
        stop: list[str] | None = None,
    ) -> LLMResponse:
        # FakeLLM ignores temperature; determinism is the whole point.
        self.calls.append(
            (
                "creative_complete",
                {
                    "prompt": prompt,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "stop": stop,
                },
            )
        )
        return await self.complete(prompt, max_tokens=max_tokens, stop=stop)
