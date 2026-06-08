"""AI Act classification rules layer.

The deterministic decision logic for risk tiers. The agent's LLM nodes extract
attributes into an AttributeSet; this layer decides the tier from those
attributes. See engine.AiActRules for the public entry point.
"""

from regulations.ai_act.rules import (
    annex_i,
    annex_iii,
    article_5,
    article_50,
    chapter_v,
)
from regulations.ai_act.rules._common import (
    CELEX_ID,
    RULES_CORPUS_VERSION,
    RuleMatch,
    annex_citation,
    article_citation,
)
from regulations.ai_act.rules.engine import RULES_VERSION, AiActRules

__all__ = [
    "CELEX_ID",
    "RULES_CORPUS_VERSION",
    "RULES_VERSION",
    "AiActRules",
    "RuleMatch",
    "annex_citation",
    "annex_i",
    "annex_iii",
    "article_5",
    "article_50",
    "article_citation",
    "chapter_v",
]
