"""
AI Act regulation plugin.

Phase 4 wires classifier_rules and obligations_map. Phase 5 fills in
document_templates and defined_terms (Art. 3 glossary).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from regulations.ai_act.corpus.loader import AiActChunkerConfig, AiActCorpusLoader
from regulations.ai_act.obligations import AiActObligations
from regulations.ai_act.rules import AiActRules
from regulations.ai_act.timeline import AiActTimeline

if TYPE_CHECKING:
    from backend.ports.regulation import Glossary, TemplateSet


class _PendingPhase(Exception):
    """Raised when accessing a plugin component that lands in a later phase."""


class AiActRegulation:
    """Regulation plugin for Regulation (EU) 2024/1689."""

    name: str = "ai_act"

    def __init__(
        self,
        *,
        corpus_loader: AiActCorpusLoader | None = None,
        chunker_config: AiActChunkerConfig | None = None,
        classifier_rules: AiActRules | None = None,
        obligations_map: AiActObligations | None = None,
    ) -> None:
        self.corpus_loader = corpus_loader or AiActCorpusLoader()
        self.chunker_config = chunker_config or AiActChunkerConfig()
        self.classifier_rules = classifier_rules or AiActRules()
        self.obligations_map = obligations_map or AiActObligations()
        self.timeline = AiActTimeline()

    @property
    def document_templates(self) -> TemplateSet:
        raise _PendingPhase("AiActRegulation.document_templates lands in Phase 5.")

    @property
    def defined_terms(self) -> Glossary:
        raise _PendingPhase("AiActRegulation.defined_terms lands in Phase 5.")
