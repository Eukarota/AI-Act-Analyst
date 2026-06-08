"""
LLM provider port.

Phase 1: Protocol + LLMResponse + LLMUsage.
Phase 3: SelfHostedVLLM adapter. The Mistral EU adapter lives behind the same
Protocol and can be added without changes to callers.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict


class LLMUsage(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    tokens_in: int
    tokens_out: int


class LLMResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    text: str
    model_id: str
    usage: LLMUsage
    finish_reason: str = "stop"


@runtime_checkable
class LLMProvider(Protocol):
    """
    Inference port. All LLM calls in the codebase pass through this.

    Conventions:
      - Default temperature is 0. Only draft_documentation may call
        creative_complete() with a higher temperature.
      - Implementations must report the model_id they served.
      - No streaming in v1; classification and report assembly are atomic.
    """

    model_id: str

    async def complete(
        self,
        prompt: str,
        *,
        max_tokens: int = 1024,
        stop: list[str] | None = None,
    ) -> LLMResponse:
        """Deterministic completion (temperature=0)."""
        ...

    async def creative_complete(
        self,
        prompt: str,
        *,
        max_tokens: int = 1024,
        temperature: float = 0.4,
        stop: list[str] | None = None,
    ) -> LLMResponse:
        """Higher-temperature completion. Restricted to draft_documentation."""
        ...
