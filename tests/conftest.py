"""Shared pytest fixtures."""

from __future__ import annotations

import pytest

from backend.adapters.fake_embedder import FakeEmbedder
from backend.adapters.fake_llm import FakeLLM


@pytest.fixture()
def fake_llm() -> FakeLLM:
    return FakeLLM()


@pytest.fixture()
def fake_embedder() -> FakeEmbedder:
    return FakeEmbedder()
