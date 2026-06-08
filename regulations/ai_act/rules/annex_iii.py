"""
Annex III high-risk track: standalone AI systems whose intended use falls in
one of the listed areas.

Per Art. 6(2) read with Annex III, AI systems "intended to be used" in the
eight listed areas are high-risk. The Annex III(2) carve-out (Art. 6(3))
allows a provider to declare the system is NOT high-risk if it does not pose
a significant risk of harm; this rule does not attempt to apply the carve-out
automatically, the agent's clarify loop surfaces it as a question instead.

Detection strategy:
  - explicit flags first (biometric is the cleanest)
  - then keyword matching on purpose / domain / deployment_context
  - keywords are conservative and tied to the Annex III text language
"""

from __future__ import annotations

from backend.agent.state import AttributeSet, Tier
from regulations.ai_act.rules._common import (
    RuleMatch,
    annex_citation,
    any_phrase,
    article_citation,
    text_search,
)

# Annex III(1) Biometrics
_BIOMETRIC_PHRASES = (
    "remote biometric identification",
    "biometric categorisation",
    "emotion recognition",
)

# Annex III(2) Critical infrastructure
_CRITICAL_INFRA_PHRASES = (
    "critical infrastructure",
    "critical digital infrastructure",
    "road traffic",
    "water supply",
    "gas supply",
    "electricity supply",
    "heating supply",
    "water, gas",
    "energy grid",
    "power grid",
)

# Annex III(3) Education and vocational training
_EDUCATION_PHRASES = (
    "school admission",
    "educational institution",
    "vocational training",
    "exam scoring",
    "exam grading",
    "student assessment",
    "evaluate learning outcomes",
    "assign students",
    "place in educational",
    "detect cheating",
    "monitor students",
)

# Annex III(4) Employment, workers management, access to self-employment
_EMPLOYMENT_PHRASES = (
    "recruitment",
    "recruiting",
    "hiring",
    "screen job applic",
    "filter job applic",
    "rank candidates",
    "evaluate candidates",
    "place targeted job advert",
    "promotion decision",
    "task allocation",
    "monitor worker",
    "evaluate performance of employee",
    "terminate employ",
)

# Annex III(5) Access to and enjoyment of essential private/public services and benefits
_ESSENTIAL_SERVICES_PHRASES = (
    "credit score",
    "creditworthiness",
    "credit decision",
    "loan approval",
    "insurance pricing",
    "insurance risk",
    "life insurance",
    "health insurance",
    "social benefit",
    "welfare",
    "public assistance",
    "emergency call dispatch",
    "triage emergency",
    "first response priorit",
)

# Annex III(6) Law enforcement
_LAW_ENFORCEMENT_PHRASES = (
    "law enforcement",
    "police investigation",
    "polygraph",
    "lie detect",
    "evidence reliability",
    "profiling for crim",
    "criminal investigation",
)

# Annex III(7) Migration, asylum, border
_MIGRATION_PHRASES = (
    "migration",
    "asylum",
    "border control",
    "visa application",
    "residence permit",
    "refugee",
)

# Annex III(8) Administration of justice and democratic processes
_JUSTICE_PHRASES = (
    "judicial",
    "administration of justice",
    "court decision",
    "judge",
    "democratic process",
    "election",
    "voting behaviour",
    "influence voting",
)


_AREAS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "1",
        "annex_iii_1.biometrics",
        _BIOMETRIC_PHRASES,
    ),
    ("2", "annex_iii_2.critical_infrastructure", _CRITICAL_INFRA_PHRASES),
    ("3", "annex_iii_3.education", _EDUCATION_PHRASES),
    ("4", "annex_iii_4.employment", _EMPLOYMENT_PHRASES),
    ("5", "annex_iii_5.essential_services", _ESSENTIAL_SERVICES_PHRASES),
    ("6", "annex_iii_6.law_enforcement", _LAW_ENFORCEMENT_PHRASES),
    ("7", "annex_iii_7.migration_border", _MIGRATION_PHRASES),
    ("8", "annex_iii_8.justice_and_democracy", _JUSTICE_PHRASES),
)


def evaluate(attributes: AttributeSet) -> RuleMatch | None:
    text = text_search(attributes)

    # Annex III(1) is the only area we let an explicit flag short-circuit, since
    # the biometric flag is well-defined and unambiguous.
    if attributes.biometric and not attributes.real_time_remote_biometric_id:
        return RuleMatch(
            tier=Tier.HIGH_RISK_ANNEX_III,
            fired_rule="annex_iii_1.biometrics_flag",
            supporting_refs=(
                article_citation("6", paragraph="2"),
                annex_citation("III", point="1"),
            ),
            rationale=(
                "System uses biometric identification or categorisation as declared by "
                "the biometric flag; falls within Annex III(1). Real-time remote "
                "biometric ID in publicly accessible spaces would have been caught "
                "earlier as a prohibited practice under Art. 5(1)(h)."
            ),
        )

    for point, rule_id, phrases in _AREAS:
        if any_phrase(text, phrases):
            return RuleMatch(
                tier=Tier.HIGH_RISK_ANNEX_III,
                fired_rule=rule_id,
                supporting_refs=(
                    article_citation("6", paragraph="2"),
                    annex_citation("III", point=point),
                ),
                rationale=(
                    f"Intended use falls within Annex III({point}); classified as "
                    f"high-risk under Art. 6(2). The provider may declare the system "
                    f"not high-risk under the Art. 6(3) carve-out, which requires a "
                    f"documented assessment."
                ),
            )

    return None
