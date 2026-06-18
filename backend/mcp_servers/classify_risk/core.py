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

# Mistral Large (and some other chat models) wrap structured outputs under
# the schema name, e.g. {"AttributeSet": {...real fields...}}. The prompt
# tries to discourage this; the parser unwraps defensively so a single
# misbehaving generation does not fail extraction.
_KNOWN_ENVELOPE_KEYS = frozenset(
    {"AttributeSet", "attributes", "attribute_set", "result", "data", "output"}
)


def _unwrap_envelope(parsed: dict[str, Any]) -> dict[str, Any]:
    if len(parsed) != 1:
        return parsed
    only_key = next(iter(parsed))
    inner = parsed[only_key]
    if only_key in _KNOWN_ENVELOPE_KEYS and isinstance(inner, dict):
        return inner
    return parsed


def _strip_fences(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```\s*$", "", stripped)
    return stripped


def _largest_balanced_object(text: str) -> str | None:
    """Return the longest balanced {...} substring, or None.

    Handles models that prepend a sentence ("Here is the JSON:"), append
    trailing prose, or return multiple candidate objects. Quote-aware so it
    does not get confused by braces inside string values.
    """
    best: tuple[int, int] | None = None
    depth = 0
    start = -1
    in_string = False
    escape = False
    for i, ch in enumerate(text):
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
            continue
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            if depth > 0:
                depth -= 1
                if depth == 0 and start >= 0:
                    span = (start, i + 1)
                    if best is None or (span[1] - span[0]) > (best[1] - best[0]):
                        best = span
    return text[best[0] : best[1]] if best else None


# Smart quotes Mistral occasionally emits in spite of json_mode.
_SMART_QUOTE_MAP = str.maketrans({"“": '"', "”": '"', "’": "'", "‘": "'"})


def _repair_json(candidate: str) -> str:
    """Best-effort fixes for common LLM JSON glitches.

    The list is deliberately conservative; we only patch malformations we
    have seen in the wild. Order matters: normalise quotes before stripping
    trailing commas so commas inside repaired strings stay put.
    """
    repaired = candidate.translate(_SMART_QUOTE_MAP)
    # Strip ASCII control chars that break json.loads (0x00..0x1F except \t/\n/\r).
    repaired = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", repaired)
    # Trailing commas before } or ].
    repaired = re.sub(r",(\s*[}\]])", r"\1", repaired)
    return repaired


def _extract_json(text: str) -> dict[str, Any]:
    """
    Parse a JSON object out of the LLM response.

    Robust to: markdown fences, leading/trailing prose, trailing commas,
    smart quotes, stray control characters, multiple candidate objects.
    Strict shape validation still lives in Pydantic's AttributeSet parsing.
    """
    stripped = _strip_fences(text)

    # Fast path: the whole stripped body is already valid JSON.
    try:
        parsed = json.loads(stripped)
        if isinstance(parsed, dict):
            return _unwrap_envelope(parsed)
    except json.JSONDecodeError:
        pass

    # Find the largest balanced {...} block and try as-is, then with repairs.
    candidate = _largest_balanced_object(text) or _largest_balanced_object(stripped)
    if candidate is None:
        raise AttributeExtractionError(
            f"LLM response did not contain a JSON object: {text[:200]}"
        )

    for attempt in (candidate, _repair_json(candidate)):
        try:
            parsed = json.loads(attempt)
        except json.JSONDecodeError:
            continue
        if not isinstance(parsed, dict):
            continue
        return _unwrap_envelope(parsed)

    # Both attempts failed: surface a useful diagnostic including a slice of
    # the original response so the operator can see what Mistral returned.
    try:
        json.loads(_repair_json(candidate))
    except json.JSONDecodeError as exc:
        preview = text.strip().replace("\n", " ")[:240]
        raise AttributeExtractionError(
            f"LLM response JSON was malformed at {exc.lineno}:{exc.colno} "
            f"({exc.msg}). Preview: {preview!r}"
        ) from exc
    raise AttributeExtractionError("LLM response JSON was not an object")


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
    # json_mode constrains the decoder to strict JSON on providers that
    # support it (Mistral La Plateforme, OpenAI-compatible vLLM servers).
    # Self-hosted backends that ignore the flag still pass through
    # _extract_json's defensive repairer below.
    #
    # max_tokens 2048: the AttributeSet has ~20 fields and FR/EN narrative
    # values can be verbose. The previous 1024 default truncated mid-string
    # in production (see assess.agent_error 2026-06-18).
    response = await llm.complete(rendered, json_mode=True, max_tokens=2048)
    if response.finish_reason == "length":
        raise AttributeExtractionError(
            "LLM hit the max_tokens budget before completing the attribute JSON; "
            "raise the budget or shorten the system description."
        )
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
