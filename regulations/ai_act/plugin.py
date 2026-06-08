"""
AI Act regulation plugin (complete).

By Phase 5 all Regulation Protocol components are wired. Adding a new
regulation (RGPD, DORA, NIS2) is now a matter of writing a parallel module
under regulations/<name>/ implementing the same Protocol -- the agent core
remains regulation-agnostic.
"""

from __future__ import annotations

from backend.ports.regulation import (
    ChunkerConfig,
    CorpusLoader,
    Glossary,
    ObligationsMap,
    RuleSet,
    TemplateSet,
    TimelineConfig,
)
from regulations.ai_act.corpus.loader import AiActChunkerConfig, AiActCorpusLoader
from regulations.ai_act.defined_terms import AiActGlossary
from regulations.ai_act.document_templates import AiActTemplates
from regulations.ai_act.obligations import AiActObligations
from regulations.ai_act.rules import AiActRules
from regulations.ai_act.timeline import AiActTimeline


class AiActRegulation:
    """Regulation plugin for Regulation (EU) 2024/1689."""

    name: str = "ai_act"

    # Protocol-typed attributes so mypy treats AiActRegulation as a
    # structural Regulation: concrete subclasses (AiActRules, etc.) satisfy
    # the Protocols at runtime via runtime_checkable.
    corpus_loader: CorpusLoader
    chunker_config: ChunkerConfig
    classifier_rules: RuleSet
    obligations_map: ObligationsMap
    document_templates: TemplateSet
    defined_terms: Glossary
    timeline: TimelineConfig

    def __init__(
        self,
        *,
        corpus_loader: AiActCorpusLoader | None = None,
        chunker_config: AiActChunkerConfig | None = None,
        classifier_rules: AiActRules | None = None,
        obligations_map: AiActObligations | None = None,
        document_templates: AiActTemplates | None = None,
        defined_terms: AiActGlossary | None = None,
    ) -> None:
        self.corpus_loader = corpus_loader or AiActCorpusLoader()
        self.chunker_config = chunker_config or AiActChunkerConfig()
        self.classifier_rules = classifier_rules or AiActRules()
        self.obligations_map = obligations_map or AiActObligations()
        self.document_templates = document_templates or AiActTemplates()
        self.defined_terms = defined_terms or AiActGlossary()
        self.timeline = AiActTimeline()
