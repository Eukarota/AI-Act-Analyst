"""AiActObligations table tests."""

from __future__ import annotations

from backend.agent.state import (
    ActorRole,
    Citation,
    ClassificationResult,
    Tier,
)
from regulations.ai_act.obligations import OBLIGATIONS_BY_TIER, AiActObligations
from regulations.ai_act.rules import RULES_VERSION


def _classification(tier: Tier) -> ClassificationResult:
    return ClassificationResult(
        tier=tier,
        fired_rule="test",
        supporting_refs=(),
        rationale="",
        rules_version=RULES_VERSION,
    )


def test_high_risk_annex_iii_includes_provider_and_deployer_articles() -> None:
    obligations = AiActObligations().obligations_for(_classification(Tier.HIGH_RISK_ANNEX_III))
    articles = {o.citation.article for o in obligations}
    # Provider obligations: Art. 9-15, 17, 43, 47, 48, 49 must all be present.
    for art in ["9", "10", "11", "12", "13", "14", "15", "17", "43", "47", "48", "49"]:
        assert art in articles, f"Art. {art} missing from HIGH_RISK_ANNEX_III obligations"
    # Deployer obligations: Art. 26 must be present.
    assert "26" in articles


def test_high_risk_annex_i_and_iii_have_same_obligations() -> None:
    """Annex I and Annex III high-risk systems share the same obligation set (CLAUDE.md §10)."""
    obligations = AiActObligations()
    set_i = obligations.obligations_for(_classification(Tier.HIGH_RISK_ANNEX_I))
    set_iii = obligations.obligations_for(_classification(Tier.HIGH_RISK_ANNEX_III))
    assert {o.obligation_id for o in set_i} == {o.obligation_id for o in set_iii}


def test_transparency_obligations_cover_all_four_paragraphs() -> None:
    obligations = AiActObligations().obligations_for(_classification(Tier.TRANSPARENCY))
    paragraphs = {o.citation.paragraph for o in obligations}
    assert paragraphs == {"1", "2", "3", "4"}


def test_gpai_systemic_is_superset_of_gpai() -> None:
    """A systemic-risk GPAI carries all Art. 53 duties plus Art. 55."""
    obligations = AiActObligations()
    gpai_ids = {o.obligation_id for o in obligations.obligations_for(_classification(Tier.GPAI))}
    systemic_ids = {
        o.obligation_id for o in obligations.obligations_for(_classification(Tier.GPAI_SYSTEMIC))
    }
    assert gpai_ids.issubset(systemic_ids)
    assert any("art_55" in oid for oid in systemic_ids)


def test_prohibited_and_minimal_carry_no_mandatory_obligations() -> None:
    obligations = AiActObligations()
    assert obligations.obligations_for(_classification(Tier.PROHIBITED)) == []
    assert obligations.obligations_for(_classification(Tier.MINIMAL)) == []


def test_every_obligation_carries_a_valid_citation() -> None:
    """The grounding contract relies on citations matching by celex_id + article."""
    for tier, obligations in OBLIGATIONS_BY_TIER.items():
        for obligation in obligations:
            assert isinstance(obligation.citation, Citation)
            assert obligation.citation.celex_id == "32024R1689"
            assert obligation.citation.article, (
                f"obligation {obligation.obligation_id} for tier {tier} has no article"
            )
            assert obligation.applies_to, (
                f"obligation {obligation.obligation_id} has no applicable actor role"
            )


def test_actor_roles_are_well_typed() -> None:
    for obligations in OBLIGATIONS_BY_TIER.values():
        for obligation in obligations:
            for role in obligation.applies_to:
                assert isinstance(role, ActorRole)
