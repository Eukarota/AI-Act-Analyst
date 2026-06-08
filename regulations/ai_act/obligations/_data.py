"""
Tier -> Obligations table for the AI Act.

Each Obligation is a structured statement of a duty owed by a named actor
under Regulation (EU) 2024/1689. The downstream lookup_obligations MCP tool
(Phase 5) materialises these into the agent's state and the report
assembler renders them with the Phase 2 retrieval results so the *text* of
each article is grounded against the actual corpus.

These records are the rule-layer authority for which articles apply at each
tier; the corpus is the authority for what those articles *say*.
"""

from __future__ import annotations

from backend.agent.state import ActorRole, Obligation, Tier
from regulations.ai_act.rules._common import article_citation


def _o(
    obligation_id: str,
    *,
    summary: str,
    article: str,
    applies_to: tuple[ActorRole, ...],
    paragraph: str | None = None,
) -> Obligation:
    return Obligation(
        obligation_id=obligation_id,
        summary=summary,
        article_ref=f"Art. {article}" + (f"({paragraph})" if paragraph else ""),
        applies_to=applies_to,
        citation=article_citation(article, paragraph=paragraph),
    )


_HIGH_RISK_PROVIDER_OBLIGATIONS: tuple[Obligation, ...] = (
    _o(
        "art_9.risk_management_system",
        summary=(
            "Establish, implement, document and maintain a risk management system that "
            "runs throughout the entire lifecycle of the high-risk AI system."
        ),
        article="9",
        applies_to=(ActorRole.PROVIDER,),
    ),
    _o(
        "art_10.data_and_data_governance",
        summary=(
            "Training, validation and testing data sets must be subject to data "
            "governance practices appropriate to the intended purpose, including "
            "relevance, representativeness, and bias mitigation."
        ),
        article="10",
        applies_to=(ActorRole.PROVIDER,),
    ),
    _o(
        "art_11.technical_documentation",
        summary=(
            "Draw up technical documentation before the system is placed on the market "
            "and keep it up to date; the documentation must contain the elements set out "
            "in Annex IV."
        ),
        article="11",
        applies_to=(ActorRole.PROVIDER,),
    ),
    _o(
        "art_12.record_keeping",
        summary=(
            "The high-risk AI system must technically allow for the automatic recording "
            "of events (logs) over the duration of its lifetime."
        ),
        article="12",
        applies_to=(ActorRole.PROVIDER,),
    ),
    _o(
        "art_13.transparency_and_information",
        summary=(
            "Design the system to be sufficiently transparent so deployers can interpret "
            "outputs and use it appropriately; provide instructions for use."
        ),
        article="13",
        applies_to=(ActorRole.PROVIDER,),
    ),
    _o(
        "art_14.human_oversight",
        summary=(
            "Design the system so it can be effectively overseen by natural persons; "
            "oversight measures must be commensurate with the risks."
        ),
        article="14",
        applies_to=(ActorRole.PROVIDER,),
    ),
    _o(
        "art_15.accuracy_robustness_cybersecurity",
        summary=(
            "Design and develop the system to achieve appropriate levels of accuracy, "
            "robustness and cybersecurity throughout its lifecycle."
        ),
        article="15",
        applies_to=(ActorRole.PROVIDER,),
    ),
    _o(
        "art_17.quality_management_system",
        summary=(
            "Put in place a quality management system covering compliance procedures, "
            "design, data governance, testing, post-market monitoring, and incident "
            "reporting."
        ),
        article="17",
        applies_to=(ActorRole.PROVIDER,),
    ),
    _o(
        "art_43.conformity_assessment",
        summary=(
            "Subject the system to the relevant conformity assessment procedure before "
            "placing it on the market or putting it into service."
        ),
        article="43",
        applies_to=(ActorRole.PROVIDER,),
    ),
    _o(
        "art_47.declaration_of_conformity",
        summary=(
            "Draw up a written EU declaration of conformity attesting that the system "
            "meets the applicable requirements; keep it for ten years."
        ),
        article="47",
        applies_to=(ActorRole.PROVIDER,),
    ),
    _o(
        "art_48.ce_marking",
        summary=(
            "Affix the CE marking to the high-risk AI system, or to its packaging or "
            "accompanying documentation."
        ),
        article="48",
        applies_to=(ActorRole.PROVIDER,),
    ),
    _o(
        "art_49.registration",
        summary=(
            "Register the high-risk AI system in the EU database before placing it on "
            "the market or putting it into service."
        ),
        article="49",
        applies_to=(ActorRole.PROVIDER,),
    ),
)

_HIGH_RISK_DEPLOYER_OBLIGATIONS: tuple[Obligation, ...] = (
    _o(
        "art_26.deployer_obligations",
        summary=(
            "Use the system in accordance with the provider's instructions, assign "
            "human oversight, monitor operation, keep logs, inform affected persons "
            "where required, and cooperate with authorities."
        ),
        article="26",
        applies_to=(ActorRole.DEPLOYER,),
    ),
)

_TRANSPARENCY_OBLIGATIONS: tuple[Obligation, ...] = (
    _o(
        "art_50_1.interaction_disclosure",
        summary=(
            "Inform natural persons that they are interacting with an AI system, "
            "unless this is obvious from the circumstances."
        ),
        article="50",
        paragraph="1",
        applies_to=(ActorRole.PROVIDER,),
    ),
    _o(
        "art_50_2.synthetic_content_marking",
        summary=(
            "Mark outputs of AI systems generating synthetic audio, image, video or "
            "text content in a machine-readable format detectable as artificially "
            "generated or manipulated."
        ),
        article="50",
        paragraph="2",
        applies_to=(ActorRole.PROVIDER,),
    ),
    _o(
        "art_50_3.emotion_or_biometric_notice",
        summary=(
            "Deployers of emotion-recognition or biometric-categorisation systems must "
            "inform natural persons exposed to their operation."
        ),
        article="50",
        paragraph="3",
        applies_to=(ActorRole.DEPLOYER,),
    ),
    _o(
        "art_50_4.deepfake_disclosure",
        summary=(
            "Deployers of AI systems generating or manipulating deepfake content must "
            "disclose that the content has been artificially generated or manipulated."
        ),
        article="50",
        paragraph="4",
        applies_to=(ActorRole.DEPLOYER,),
    ),
)

_GPAI_OBLIGATIONS: tuple[Obligation, ...] = (
    _o(
        "art_53_1_a.technical_documentation_model",
        summary=(
            "Draw up and keep up-to-date the technical documentation of the model "
            "(training and testing process, evaluation results); the contents are set "
            "out in Annex XI."
        ),
        article="53",
        paragraph="1",
        applies_to=(ActorRole.PROVIDER,),
    ),
    _o(
        "art_53_1_b.information_to_downstream_providers",
        summary=(
            "Make information and documentation available to downstream providers that "
            "intend to integrate the model into their AI systems; minimum content set "
            "out in Annex XII."
        ),
        article="53",
        paragraph="1",
        applies_to=(ActorRole.PROVIDER,),
    ),
    _o(
        "art_53_1_c.copyright_policy",
        summary=(
            "Put in place a policy to comply with Union copyright law, in particular to "
            "identify and respect reservations of rights expressed pursuant to "
            "Art. 4(3) of Directive (EU) 2019/790."
        ),
        article="53",
        paragraph="1",
        applies_to=(ActorRole.PROVIDER,),
    ),
    _o(
        "art_53_1_d.training_content_summary",
        summary=(
            "Draw up and make publicly available a sufficiently detailed summary about "
            "the content used to train the general-purpose AI model."
        ),
        article="53",
        paragraph="1",
        applies_to=(ActorRole.PROVIDER,),
    ),
)

_GPAI_SYSTEMIC_OBLIGATIONS: tuple[Obligation, ...] = (
    *_GPAI_OBLIGATIONS,
    _o(
        "art_55_1_a.model_evaluation",
        summary=(
            "Perform model evaluation in accordance with standardised protocols, "
            "including adversarial testing of the model, to identify and mitigate "
            "systemic risks."
        ),
        article="55",
        paragraph="1",
        applies_to=(ActorRole.PROVIDER,),
    ),
    _o(
        "art_55_1_b.systemic_risk_assessment_mitigation",
        summary=(
            "Assess and mitigate possible systemic risks at Union level, including "
            "their sources, that may stem from the development, placing on the market "
            "or use of GPAI models with systemic risk."
        ),
        article="55",
        paragraph="1",
        applies_to=(ActorRole.PROVIDER,),
    ),
    _o(
        "art_55_1_c.incident_reporting",
        summary=(
            "Keep track of, document and report, without undue delay, serious incidents "
            "and possible corrective measures to the AI Office and, as appropriate, to "
            "national competent authorities."
        ),
        article="55",
        paragraph="1",
        applies_to=(ActorRole.PROVIDER,),
    ),
    _o(
        "art_55_1_d.cybersecurity",
        summary=(
            "Ensure an adequate level of cybersecurity protection for the model and "
            "its physical infrastructure."
        ),
        article="55",
        paragraph="1",
        applies_to=(ActorRole.PROVIDER,),
    ),
)

_HIGH_RISK_ALL: tuple[Obligation, ...] = (
    *_HIGH_RISK_PROVIDER_OBLIGATIONS,
    *_HIGH_RISK_DEPLOYER_OBLIGATIONS,
)

OBLIGATIONS_BY_TIER: dict[Tier, tuple[Obligation, ...]] = {
    Tier.PROHIBITED: (),
    Tier.HIGH_RISK_ANNEX_I: _HIGH_RISK_ALL,
    Tier.HIGH_RISK_ANNEX_III: _HIGH_RISK_ALL,
    Tier.TRANSPARENCY: _TRANSPARENCY_OBLIGATIONS,
    Tier.GPAI: _GPAI_OBLIGATIONS,
    Tier.GPAI_SYSTEMIC: _GPAI_SYSTEMIC_OBLIGATIONS,
    Tier.MINIMAL: (),
    Tier.UNDETERMINED: (),
}
