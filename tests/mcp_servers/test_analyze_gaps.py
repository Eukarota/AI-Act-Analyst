"""analyze_gaps unit tests."""

from __future__ import annotations

from backend.agent.state import ActorRole, ClassificationResult, Obligation, Tier
from backend.mcp_servers.analyze_gaps import AnalyzeGapsArgs, analyze_gaps
from regulations.ai_act.obligations import AiActObligations
from regulations.ai_act.rules import RULES_VERSION


async def _high_risk_obligations() -> tuple[Obligation, ...]:
    obligations = AiActObligations().obligations_for(
        ClassificationResult(
            tier=Tier.HIGH_RISK_ANNEX_III,
            fired_rule="test",
            supporting_refs=(),
            rules_version=RULES_VERSION,
        )
    )
    return tuple(obligations)


async def test_analyze_gaps_marks_obvious_match_as_covered() -> None:
    obligations = await _high_risk_obligations()
    declared = ("Risk management system reviewed quarterly and tied to incident response.",)
    result = await analyze_gaps(
        AnalyzeGapsArgs(
            required=obligations,
            declared_controls=declared,
            actor_role=ActorRole.PROVIDER,
        )
    )
    risk_mgmt_finding = next(
        f for f in result.findings if f.obligation_id == "art_9.risk_management_system"
    )
    assert risk_mgmt_finding.status in ("covered", "partial")
    assert risk_mgmt_finding.declared_evidence is not None


async def test_analyze_gaps_marks_unrelated_as_missing() -> None:
    obligations = await _high_risk_obligations()
    declared = ("We have a French website and weekly stand-ups.",)
    result = await analyze_gaps(
        AnalyzeGapsArgs(
            required=obligations,
            declared_controls=declared,
            actor_role=ActorRole.PROVIDER,
        )
    )
    missing = [f for f in result.findings if f.status == "missing"]
    assert missing, "unrelated declarations should leave many obligations missing"
    assert result.coverage_ratio < 0.5


async def test_analyze_gaps_filters_by_actor_role() -> None:
    obligations = await _high_risk_obligations()
    result = await analyze_gaps(
        AnalyzeGapsArgs(
            required=obligations,
            declared_controls=("Quarterly review by the deployment ops team.",),
            actor_role=ActorRole.DEPLOYER,
        )
    )
    # All findings must correspond to obligations that apply to deployers.
    for finding in result.findings:
        matched_obligation = next(
            o for o in obligations if o.obligation_id == finding.obligation_id
        )
        assert ActorRole.DEPLOYER in matched_obligation.applies_to


async def test_analyze_gaps_handles_empty_required() -> None:
    result = await analyze_gaps(AnalyzeGapsArgs(required=(), declared_controls=("we have stuff",)))
    assert result.findings == []
    assert result.coverage_ratio == 1.0
