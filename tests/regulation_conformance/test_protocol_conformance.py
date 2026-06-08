"""
Protocol conformance test.

In Phase 1, this asserts the fixture regulation satisfies the Regulation
Protocol structurally and that each component returns sensible values on a
toy AttributeSet. The full end-to-end conformance run (intake to assembled
report) lands in Phase 6 once the LangGraph agent exists.

Any new regulation plugin must pass these tests AND the Phase 6 e2e suite.
"""

from __future__ import annotations

from backend.agent.state import AttributeSet, Tier
from backend.ports.regulation import (
    ChunkerConfig,
    CorpusLoader,
    Glossary,
    ObligationsMap,
    Regulation,
    RuleSet,
    TemplateSet,
    TimelineConfig,
)
from tests.regulation_conformance.fixture_regulation import FixtureRegulation


def test_fixture_satisfies_regulation_protocol() -> None:
    reg = FixtureRegulation()
    assert isinstance(reg, Regulation)
    assert isinstance(reg.corpus_loader, CorpusLoader)
    assert isinstance(reg.chunker_config, ChunkerConfig)
    assert isinstance(reg.classifier_rules, RuleSet)
    assert isinstance(reg.obligations_map, ObligationsMap)
    assert isinstance(reg.document_templates, TemplateSet)
    assert isinstance(reg.defined_terms, Glossary)
    assert isinstance(reg.timeline, TimelineConfig)


def test_fixture_corpus_yields_cited_chunks() -> None:
    reg = FixtureRegulation()
    chunks = list(reg.corpus_loader.iter_chunks())
    assert chunks, "corpus loader must yield at least one chunk"
    for text, citation in chunks:
        assert text.strip()
        assert citation.corpus_version == reg.corpus_loader.corpus_version()
        assert citation.celex_id


def test_fixture_rules_are_deterministic() -> None:
    reg = FixtureRegulation()
    attrs = AttributeSet(purpose="Make automatic credit decisions for applicants.")
    first = reg.classifier_rules.classify(attrs)
    second = reg.classifier_rules.classify(attrs)
    assert first == second
    assert first.tier == Tier.HIGH_RISK_ANNEX_III
    assert first.supporting_refs


def test_fixture_rules_default_to_transparency() -> None:
    reg = FixtureRegulation()
    attrs = AttributeSet(purpose="Greet visitors.")
    result = reg.classifier_rules.classify(attrs)
    assert result.tier == Tier.TRANSPARENCY


def test_fixture_obligations_match_tier() -> None:
    reg = FixtureRegulation()
    attrs = AttributeSet(purpose="Make automatic credit decisions for applicants.")
    classification = reg.classifier_rules.classify(attrs)
    obligations = reg.obligations_map.obligations_for(classification)
    assert obligations
    assert all(o.citation.celex_id for o in obligations)


def test_fixture_templates_render() -> None:
    reg = FixtureRegulation()
    rendered = reg.document_templates.render("fixture_doc", {"system_name": "Test Bot"})
    assert "Test Bot" in rendered


def test_fixture_glossary_and_timeline() -> None:
    reg = FixtureRegulation()
    assert reg.defined_terms.lookup("provider")
    assert reg.timeline.applicable_on("entry_into_force") == "2099-01-01"
