"""
Grounding contract: the anti-hallucination guard.

The LLM may only state a legal claim that is backed by a passage returned from
retrieval in the current turn. This module is the single implementation of
that contract. It is imported by:

  - Phase 5: retrieve_law MCP server (filters non-grounded text at source)
  - Phase 7: FastAPI report assembler (online check before responding)
  - Phase 9: eval/run_eval.py (offline groundedness metric)

CLAUDE.md non-negotiable: "Eval and prod call the identical check" -- enforced
by import, never duplicated. If a second implementation appears anywhere in
the repo, treat that as a bug.

A claim is grounded when one of its declared citations matches the citation
metadata of a passage that was actually retrieved in the same turn. Matching
uses a normalized citation key (celex_id + article + paragraph + annex_ref +
recital_ref). String similarity of the claim text is intentionally NOT used:
the contract is about provenance, not paraphrase quality.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

from backend.agent.state import Citation, RetrievedPassage


def citation_key(citation: Citation) -> tuple[str, str | None, str | None, str | None, str | None]:
    """Canonical key for matching a claim's citation against retrieved passages."""
    return (
        citation.celex_id,
        citation.article,
        citation.paragraph,
        citation.annex_ref,
        citation.recital_ref,
    )


@dataclass(frozen=True)
class Claim:
    """A statement made in a generated report, with the citations supporting it."""

    text: str
    citations: tuple[Citation, ...]
    source_node: str | None = None


@dataclass(frozen=True)
class GroundingViolation:
    claim: Claim
    reason: str
    unmatched_citations: tuple[Citation, ...] = ()
    uncited: bool = False

    def describe(self) -> str:
        if self.uncited:
            return f"uncited claim: {self.claim.text[:120]}"
        keys = [c.short() for c in self.unmatched_citations]
        return f"unsupported citations {keys}: {self.claim.text[:120]}"


@dataclass(frozen=True)
class GroundingResult:
    grounded: bool
    violations: tuple[GroundingViolation, ...] = field(default_factory=tuple)
    checked_claims: int = 0

    @property
    def violation_count(self) -> int:
        return len(self.violations)


class GroundingError(RuntimeError):
    """Raised when fail_closed=True and a violation is detected."""

    def __init__(self, result: GroundingResult) -> None:
        super().__init__(
            f"grounding contract violated: {result.violation_count} of "
            f"{result.checked_claims} claims unsupported"
        )
        self.result = result


def assert_grounded(
    claims: Iterable[Claim],
    retrieved: Sequence[RetrievedPassage],
    *,
    fail_closed: bool = True,
) -> GroundingResult:
    """
    Verify every claim is backed by at least one retrieved passage.

    Args:
        claims: claims emitted by the report assembler (or any LLM output that
            asserts something about the regulation).
        retrieved: the passages retrieved in the same turn. Order does not
            matter.
        fail_closed: when True (the default and the only acceptable production
            setting), a violation raises GroundingError. Eval mode passes
            False because it aggregates statistics across many runs.

    Returns:
        GroundingResult describing what was checked. In production, callers
        should pass fail_closed=True and rely on the exception; in eval,
        callers pass fail_closed=False and inspect violations.

    The check is intentionally strict: an empty citation list on a non-empty
    claim is itself a violation (uncited=True). This makes "the model forgot
    to cite" indistinguishable from "the model invented a citation" in terms
    of the contract -- both fail closed.
    """
    available_keys = {citation_key(passage.citation) for passage in retrieved}

    violations: list[GroundingViolation] = []
    checked = 0

    for claim in claims:
        if not claim.text.strip():
            continue
        checked += 1

        if not claim.citations:
            violations.append(
                GroundingViolation(claim=claim, reason="no citations attached", uncited=True)
            )
            continue

        unmatched = tuple(c for c in claim.citations if citation_key(c) not in available_keys)
        if unmatched:
            violations.append(
                GroundingViolation(
                    claim=claim,
                    reason="cited passages were not in the retrieved set",
                    unmatched_citations=unmatched,
                )
            )

    result = GroundingResult(
        grounded=not violations,
        violations=tuple(violations),
        checked_claims=checked,
    )

    if fail_closed and not result.grounded:
        raise GroundingError(result)

    return result
