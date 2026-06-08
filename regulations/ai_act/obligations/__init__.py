"""AI Act tier-to-obligations mapping."""

from regulations.ai_act.obligations._data import OBLIGATIONS_BY_TIER
from regulations.ai_act.obligations.loader import AiActObligations

__all__ = ["OBLIGATIONS_BY_TIER", "AiActObligations"]
