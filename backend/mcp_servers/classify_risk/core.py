"""
classify_risk: extract attributes from a system description and classify.

Two-step:
  1. LLM extracts an AttributeSet from the free-form description, at
     temperature 0 (CLAUDE.md section 12.3).
  2. The deterministic rules engine (Phase 4) classifies the AttributeSet.

The LLM never decides the tier; it only extracts attributes. Declared
overrides from the agent's intake step (e.g. attributes the client filled
in explicitly) take precedence over the LLM's guesses.

Citation guarantee:
  The ClassificationResult.supporting_refs are populated by the rules layer
  with Article / Annex citations. They are NOT retrieved-passage citations
  -- the corpus_version stamp is "ai_act-rules" -- but the grounding key
  (celex + article + paragraph + annex_ref + recital_ref) still matches
  retrieved passages for the same article.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from backend.agent.state import AttributeSet, ClassificationResult
from backend.ports.llm_provider import LLMProvider
from backend.prompts.loader import PromptRegistry
from regulations.ai_act.rules import AiActRules


@dataclass(frozen=True)
class ClassifyRiskArgs:
    system_description: str
    declared_attributes: dict[str, Any] | None = None


@dataclass(frozen=True)
class ClassifyRiskResult:
    attributes: AttributeSet
    classification: ClassificationResult


class AttributeExtractionError(RuntimeError):
    """The LLM response could not be parsed into an AttributeSet."""


_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


def _extract_json(text: str) -> dict[str, Any]:
    """
    Parse a JSON object out of the LLM response.

    Lenient on purpose: chat models sometimes wrap JSON in markdown fences or
    prepend a sentence. We grab the first {...} block. The strict shape
    validation lives in Pydantic's AttributeSet parsing.
    """
    stripped = text.strip()
    if stripped.startswith("```"):
        # Strip a markdown fence if present.
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```\s*$", "", stripped)
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, dict):
        return parsed
    match = _JSON_OBJECT_RE.search(text)
    if not match:
        raise AttributeExtractionError(f"LLM response did not contain a JSON object: {text[:200]}")
    try:
        fallback = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise AttributeExtractionError(f"LLM response JSON was malformed: {exc.msg}") from exc
    if not isinstance(fallback, dict):
        raise AttributeExtractionError("LLM response JSON was not an object")
    return fallback


def _merge_attributes(
    extracted: dict[str, Any],
    declared: dict[str, Any] | None,
) -> dict[str, Any]:
    """Declared (operator-confirmed) attributes override LLM extraction."""
    if not declared:
        return extracted
    merged = dict(extracted)
    merged.update(declared)
    return merged


async def extract_attributes(
    args: ClassifyRiskArgs,
    *,
    llm: LLMProvider,
    prompts: PromptRegistry,
) -> AttributeSet:
    """
    LLM-only attribute extraction; no classification.

    Agent's intake node calls this directly so the clarify loop can run
    before the rules engine is invoked. The one-shot classify_risk() below
    composes extract_attributes + rules.classify for callers that want
    both steps in a single tool call (the MCP server, drive_tool.py).
    """
    rendered = prompts.render(
        "intake_extract_attributes",
        {"system_description": args.system_description},
    )
    response = await llm.complete(rendered)
    parsed = _extract_json(response.text)
    merged = _merge_attributes(parsed, args.declared_attributes)
    try:
        return AttributeSet.model_validate(merged)
    except Exception as exc:
        raise AttributeExtractionError(
            f"LLM-extracted attributes did not validate against AttributeSet: {exc}"
        ) from exc


async def classify_risk(
    args: ClassifyRiskArgs,
    *,
    llm: LLMProvider,
    rules: AiActRules,
    prompts: PromptRegistry,
) -> ClassifyRiskResult:
    attributes = await extract_attributes(args, llm=llm, prompts=prompts)
    classification = rules.classify(attributes)
    return ClassifyRiskResult(attributes=attributes, classification=classification)
