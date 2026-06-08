"""
lookup_obligations: tier -> obligations + article refs.

Pure wrapper around the AiActObligations map (Phase 4). Exists as a tool
because the agent's enumerate_obligations node calls it; existing as a tool
keeps the agent's tool surface uniform with the rest.

Citation guarantee:
  Every returned Obligation carries a Citation with a valid celex_id and
  article. See tests/rules/test_obligations.py for the invariant.
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.agent.state import ActorRole, ClassificationResult, Obligation
from backend.ports.regulation import ObligationsMap


@dataclass(frozen=True)
class LookupObligationsArgs:
    classification: ClassificationResult
    actor_role: ActorRole | None = None


@dataclass(frozen=True)
class LookupObligationsResult:
    obligations: list[Obligation]
    tier: str


async def lookup_obligations(
    args: LookupObligationsArgs,
    *,
    obligations_map: ObligationsMap,
) -> LookupObligationsResult:
    everything = obligations_map.obligations_for(args.classification)
    if args.actor_role is not None:
        filtered = [o for o in everything if args.actor_role in o.applies_to]
    else:
        filtered = everything
    return LookupObligationsResult(
        obligations=filtered,
        tier=args.classification.tier.value,
    )
