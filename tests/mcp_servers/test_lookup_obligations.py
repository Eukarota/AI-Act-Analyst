"""lookup_obligations unit tests."""

from __future__ import annotations

from backend.agent.state import ActorRole, ClassificationResult, Tier
from backend.mcp_servers.lookup_obligations import (
    LookupObligationsArgs,
    lookup_obligations,
)
from regulations.ai_act.obligations import AiActObligations
from regulations.ai_act.rules import RULES_VERSION


def _classification(tier: Tier) -> ClassificationResult:
    return ClassificationResult(
        tier=tier,
        fired_rule="test",
        supporting_refs=(),
        rules_version=RULES_VERSION,
    )


async def test_lookup_obligations_returns_high_risk_set() -> None:
    result = await lookup_obligations(
        LookupObligationsArgs(classification=_classification(Tier.HIGH_RISK_ANNEX_III)),
        obligations_map=AiActObligations(),
    )
    assert result.tier == "high_risk_annex_iii"
    assert any(o.article_ref == "Art. 9" for o in result.obligations)
    for o in result.obligations:
        assert o.citation.celex_id == "32024R1689"


async def test_lookup_obligations_filters_by_actor_role_deployer() -> None:
    result = await lookup_obligations(
        LookupObligationsArgs(
            classification=_classification(Tier.HIGH_RISK_ANNEX_III),
            actor_role=ActorRole.DEPLOYER,
        ),
        obligations_map=AiActObligations(),
    )
    assert result.obligations, "deployer obligations should not be empty for high-risk"
    for o in result.obligations:
        assert ActorRole.DEPLOYER in o.applies_to


async def test_lookup_obligations_empty_for_minimal_tier() -> None:
    result = await lookup_obligations(
        LookupObligationsArgs(classification=_classification(Tier.MINIMAL)),
        obligations_map=AiActObligations(),
    )
    assert result.obligations == []
