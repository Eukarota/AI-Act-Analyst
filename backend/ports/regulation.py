"""
Regulation plugin Protocol (CLAUDE.md section 12.5).

The agent core is regulation-agnostic. Each regulation (AI Act, RGPD, DORA,
NIS2) is one module under regulations/<name>/ implementing this Protocol.
Adding a new regulation must not require changes to backend/agent/.

The conformance suite under tests/regulation_conformance/ exercises a fixture
regulation against this Protocol; any new plugin must pass that suite.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol, runtime_checkable

from backend.agent.state import (
    AttributeSet,
    Citation,
    ClassificationResult,
    Obligation,
)


@runtime_checkable
class CorpusLoader(Protocol):
    """Loads regulation text + citation metadata for indexing."""

    def iter_chunks(self) -> Iterable[tuple[str, Citation]]:
        """Yield (text, citation) pairs at the chunking granularity for this regulation."""
        ...

    def corpus_version(self) -> str: ...


@runtime_checkable
class ChunkerConfig(Protocol):
    """Per-regulation chunking parameters (granularity, recital handling, etc.)."""

    max_chars: int
    overlap_chars: int
    index_recitals_separately: bool


@runtime_checkable
class RuleSet(Protocol):
    """Ordered, deterministic classification rules over an AttributeSet."""

    rules_version: str

    def classify(self, attributes: AttributeSet) -> ClassificationResult: ...


@runtime_checkable
class ObligationsMap(Protocol):
    """Tier -> required obligations, each with its article reference."""

    def obligations_for(self, classification: ClassificationResult) -> list[Obligation]: ...


@runtime_checkable
class TemplateSet(Protocol):
    """Named Jinja2 templates for drafted documents (Annex IV skeleton, Art. 50, etc.)."""

    def render(self, name: str, context: dict[str, object]) -> str: ...

    def names(self) -> list[str]: ...


@runtime_checkable
class Glossary(Protocol):
    """Defined-terms glossary (Art. 3 for the AI Act)."""

    def lookup(self, term: str) -> str | None: ...

    def all_terms(self) -> dict[str, str]: ...


@runtime_checkable
class TimelineConfig(Protocol):
    """Application dates and milestones, each sourced; never hardcoded in code."""

    def applicable_on(self, milestone: str) -> str | None:
        """Returns the date string for a milestone, or None if unknown."""
        ...

    def all_milestones(self) -> dict[str, dict[str, str]]:
        """Each milestone: {date, source, note}."""
        ...


@runtime_checkable
class Regulation(Protocol):
    """
    A complete regulation plugin.

    Implementations live under regulations/<name>/ and are loaded by name.
    """

    name: str
    corpus_loader: CorpusLoader
    chunker_config: ChunkerConfig
    classifier_rules: RuleSet
    obligations_map: ObligationsMap
    document_templates: TemplateSet
    defined_terms: Glossary
    timeline: TimelineConfig
