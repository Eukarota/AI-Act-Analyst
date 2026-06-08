"""AI Act corpus: fetcher, parser, loader, scope mapping."""

from regulations.ai_act.corpus.loader import AiActChunkerConfig, AiActCorpusLoader
from regulations.ai_act.corpus.parser import (
    ParsedSection,
    SectionKind,
    parse_consolidated_text,
)
from regulations.ai_act.corpus.scope import scope_for_citation

__all__ = [
    "AiActChunkerConfig",
    "AiActCorpusLoader",
    "ParsedSection",
    "SectionKind",
    "parse_consolidated_text",
    "scope_for_citation",
]
