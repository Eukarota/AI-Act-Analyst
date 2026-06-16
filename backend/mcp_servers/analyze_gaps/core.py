"""
analyze_gaps: diff declared controls against required obligations.

Pragmatic v1 matcher:
  - Each Obligation has an obligation_id (e.g. "art_9.risk_management_system")
    and a free-text summary.
  - Each declared control is a free-text line from the client describing what
    they already do.
  - We match a declared control to an obligation when the obligation_id (or
    its keyword-stripped form) appears as a substring, OR when at least two
    distinct content words from the summary are present in the declared
    control (case-insensitive, after stop-word stripping).

This is intentionally not the final matcher; Phase 9's eval will tighten it
once we have labelled examples. For Phase 5, it surfaces obvious matches
and leaves ambiguous ones as MISSING for the agent to flag.

Citation guarantee:
  Every GapFinding references an obligation_id; the calling agent already
  has the obligations map and can re-render citations from it. The grounding
  contract is enforced when the assembled report cites Art. 9 etc.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from backend.agent.state import (
    ActorRole,
    GapFinding,
    Obligation,
)

_STOPWORDS = frozenset(
    [
        "a",
        "an",
        "and",
        "or",
        "the",
        "of",
        "for",
        "to",
        "in",
        "on",
        "by",
        "with",
        "that",
        "this",
        "these",
        "those",
        "it",
        "its",
        "is",
        "are",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "include",
        "including",
        "ensure",
        "must",
        "shall",
        "should",
        "may",
        "such",
        "as",
        "appropriate",
        "any",
        "all",
        "etc",
    ]
)
_TOKEN_RE = re.compile(r"[A-Za-zÀ-ÿ0-9_]+")


def _content_tokens(text: str) -> set[str]:
    tokens = (m.group(0).lower() for m in _TOKEN_RE.finditer(text))
    return {t for t in tokens if t not in _STOPWORDS and len(t) > 2}


@dataclass(frozen=True)
class AnalyzeGapsArgs:
    required: tuple[Obligation, ...]
    declared_controls: tuple[str, ...]
    actor_role: ActorRole | None = None
    keyword_match_threshold: int = 2
    language: str = "EN"


_NOTE_TEMPLATES: dict[str, dict[str, str]] = {
    "EN": {
        "covered": "Matched declared control for {ref}.",
        "partial": "Possible match found for {ref}; review required.",
        "missing": "No declared control found for {ref}; flag for follow-up.",
    },
    "FR": {
        "covered": "Contrôle déclaré couvrant {ref}.",
        "partial": "Correspondance possible pour {ref} ; à vérifier.",
        "missing": "Aucun contrôle déclaré pour {ref} ; à suivre.",
    },
}


def _note_for(language: str, status: str, ref: str) -> str:
    lang = language.upper()
    templates = _NOTE_TEMPLATES.get(lang, _NOTE_TEMPLATES["EN"])
    return templates[status].format(ref=ref)


@dataclass(frozen=True)
class AnalyzeGapsResult:
    findings: list[GapFinding]
    coverage_ratio: float


def _match_score(obligation: Obligation, declared: str, *, threshold: int) -> tuple[str, str]:
    """
    Return (status, evidence) for this declared control against this obligation.

    status in {"covered", "partial"}; non-matches return ("none", "").
    """
    obligation_keyword = obligation.obligation_id.split(".", 1)[-1].replace("_", " ").lower()
    declared_lower = declared.lower()
    if obligation_keyword in declared_lower:
        return "covered", declared

    summary_tokens = _content_tokens(obligation.summary)
    declared_tokens = _content_tokens(declared)
    overlap = summary_tokens & declared_tokens
    if len(overlap) >= threshold:
        if len(overlap) >= threshold + 2:
            return "covered", declared
        return "partial", declared
    return "none", ""


async def analyze_gaps(args: AnalyzeGapsArgs) -> AnalyzeGapsResult:
    obligations = (
        args.required
        if args.actor_role is None
        else tuple(o for o in args.required if args.actor_role in o.applies_to)
    )

    findings: list[GapFinding] = []
    covered_count = 0
    for obligation in obligations:
        best_status = "missing"
        best_evidence: str | None = None
        for declared in args.declared_controls:
            status, evidence = _match_score(
                obligation, declared, threshold=args.keyword_match_threshold
            )
            if status == "covered":
                best_status = "covered"
                best_evidence = evidence
                break
            if status == "partial" and best_status != "covered":
                best_status = "partial"
                best_evidence = evidence
        if best_status == "covered":
            covered_count += 1
        findings.append(
            GapFinding(
                obligation_id=obligation.obligation_id,
                status=best_status,
                notes=_note_for(args.language, best_status, obligation.article_ref),
                declared_evidence=best_evidence,
            )
        )

    coverage_ratio = covered_count / len(obligations) if obligations else 1.0
    return AnalyzeGapsResult(findings=findings, coverage_ratio=coverage_ratio)
