"""Fixture regulation: a toy two-tier regime to exercise the Regulation Protocol."""

from __future__ import annotations

from collections.abc import Iterable
from typing import ClassVar

from backend.agent.state import (
    ActorRole,
    AttributeSet,
    Citation,
    ClassificationResult,
    Obligation,
    Tier,
)

FIXTURE_CORPUS_VERSION = "fixture-v1"
FIXTURE_RULES_VERSION = "fixture-rules-v1"


def _citation(article: str) -> Citation:
    return Citation(
        celex_id="FIXTURE",
        article=article,
        corpus_version=FIXTURE_CORPUS_VERSION,
        url=f"https://example.test/fixture/art-{article}",
    )


class FixtureCorpusLoader:
    def iter_chunks(self) -> Iterable[tuple[str, Citation]]:
        yield (
            "Article 1. Systems that issue automatic decisions about people are restricted.",
            _citation("1"),
        )
        yield (
            "Article 2. All other systems are subject only to general transparency duties.",
            _citation("2"),
        )

    def corpus_version(self) -> str:
        return FIXTURE_CORPUS_VERSION


class FixtureChunkerConfig:
    max_chars: int = 500
    overlap_chars: int = 50
    index_recitals_separately: bool = False


class FixtureRules:
    rules_version: str = FIXTURE_RULES_VERSION

    def classify(self, attributes: AttributeSet) -> ClassificationResult:
        if "decision" in attributes.purpose.lower():
            return ClassificationResult(
                tier=Tier.HIGH_RISK_ANNEX_III,
                fired_rule="fixture.art_1.automatic_decisions",
                supporting_refs=(_citation("1"),),
                confidence=1.0,
                rationale="Purpose mentions automatic decisions.",
                rules_version=self.rules_version,
            )
        return ClassificationResult(
            tier=Tier.TRANSPARENCY,
            fired_rule="fixture.art_2.general",
            supporting_refs=(_citation("2"),),
            confidence=1.0,
            rationale="Default transparency duty.",
            rules_version=self.rules_version,
        )


class FixtureObligations:
    def obligations_for(self, classification: ClassificationResult) -> list[Obligation]:
        if classification.tier == Tier.HIGH_RISK_ANNEX_III:
            return [
                Obligation(
                    obligation_id="fixture.docs",
                    summary="Maintain technical documentation.",
                    article_ref="Art. 1",
                    applies_to=(ActorRole.PROVIDER,),
                    citation=_citation("1"),
                ),
            ]
        return [
            Obligation(
                obligation_id="fixture.disclosure",
                summary="Inform users they are interacting with an automated system.",
                article_ref="Art. 2",
                applies_to=(ActorRole.PROVIDER, ActorRole.DEPLOYER),
                citation=_citation("2"),
            ),
        ]


class FixtureTemplates:
    _templates: ClassVar[dict[str, str]] = {
        "fixture_doc": "Technical documentation for {{ system_name }}.",
        "fixture_disclosure": "This is an automated system. ({{ system_name }})",
    }

    def render(self, name: str, context: dict[str, object]) -> str:
        if name not in self._templates:
            raise KeyError(name)
        template = self._templates[name]
        for key, value in context.items():
            template = template.replace(f"{{{{ {key} }}}}", str(value))
        return template

    def names(self) -> list[str]:
        return list(self._templates)


class FixtureGlossary:
    _terms: ClassVar[dict[str, str]] = {
        "system": "An automated process producing outputs from inputs.",
        "provider": "Entity that places a system on the market.",
    }

    def lookup(self, term: str) -> str | None:
        return self._terms.get(term)

    def all_terms(self) -> dict[str, str]:
        return dict(self._terms)


class FixtureTimeline:
    _milestones: ClassVar[dict[str, dict[str, str]]] = {
        "entry_into_force": {
            "date": "2099-01-01",
            "source": "Fixture regulation, Art. 99",
            "note": "Synthetic milestone for tests only.",
        },
    }

    def applicable_on(self, milestone: str) -> str | None:
        entry = self._milestones.get(milestone)
        return entry.get("date") if entry else None

    def all_milestones(self) -> dict[str, dict[str, str]]:
        return dict(self._milestones)


class FixtureRegulation:
    """Complete Regulation Protocol implementation for tests."""

    name: str = "fixture"

    def __init__(self) -> None:
        self.corpus_loader = FixtureCorpusLoader()
        self.chunker_config = FixtureChunkerConfig()
        self.classifier_rules = FixtureRules()
        self.obligations_map = FixtureObligations()
        self.document_templates = FixtureTemplates()
        self.defined_terms = FixtureGlossary()
        self.timeline = FixtureTimeline()
