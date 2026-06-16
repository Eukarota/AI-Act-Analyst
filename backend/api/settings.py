"""
ApiSettings: typed env config for the FastAPI app.

Everything that varies between dev / CI / OVH lives here. No magic literals
in route code, no secrets in the repo (CLAUDE.md section 9).
"""

from __future__ import annotations

from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ApiSettings(BaseSettings):
    """Process-level configuration. Read once at startup."""

    model_config = SettingsConfigDict(
        env_prefix="BOUSSOLE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    # LLM. Defaults target local Ollama for dev; .env / cluster secret
    # override for La Plateforme or self-hosted vLLM in prod.
    llm_url: str = "http://localhost:11434"
    llm_model: str = "mistral:7b-instruct"
    llm_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("BOUSSOLE_LLM_API_KEY", "MISTRAL_API_KEY"),
        description=(
            "Bearer token for the OpenAI-compatible LLM endpoint. "
            "Accepts MISTRAL_API_KEY as an alias so the same .env works "
            "for the La Plateforme path."
        ),
    )
    llm_timeout_seconds: float = 60.0
    llm_send_seed: bool = Field(
        default=False,
        description=(
            "Send the `seed` field on chat completion requests. False by "
            "default because Mistral La Plateforme rejects it; flip to true "
            "when targeting vLLM or Ollama if the extra pinning is wanted."
        ),
    )

    # Persistence
    database_url: str = Field(
        default="postgresql://boussole:boussole@localhost:5432/boussole",
        description="DSN for the run-manifest + traces Postgres instance.",
    )
    use_in_memory_store: bool = Field(
        default=False,
        description="Run with InMemoryRunStore + InMemoryVectorStore (dev/test only).",
    )

    # Corpus
    regulation: str = "ai_act"
    fixture_corpus: bool = Field(
        default=True,
        description=(
            "Phase 7 default: load the committed fixture text instead of fetching "
            "from EUR-Lex. Set False once the corpus pipeline has indexed the full text."
        ),
    )

    # Embedder
    embedding_model: str = "fake-embedder-v0"

    # Service
    log_level: str = "INFO"
    pre_assessment_notice_lang: str = "en"

    @property
    def fixture_path(self) -> Path:
        repo_root = Path(__file__).resolve().parents[2]
        return repo_root / "regulations" / "ai_act" / "corpus" / "fixture_excerpt.txt"
