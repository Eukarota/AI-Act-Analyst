"""
Article 5 prohibited practices.

The Art. 5 list (as amended) covers practices that may not be placed on the
market, put into service or used in the Union. We evaluate the explicit
AttributeSet flags first, then fall back to a small set of keyword triggers
for cases the model marked in domain/purpose text without raising the
dedicated flag.

The flags we trust verbatim (the LLM is responsible for extracting them):
  - uses_subliminal_techniques  -> Art. 5(1)(a)
  - social_scoring              -> Art. 5(1)(c)
  - real_time_remote_biometric_id (in publicly accessible spaces) -> Art. 5(1)(h)
  - emotion_recognition (workplace / education context)            -> Art. 5(1)(f)

Caveats:
  - Art. 5(1)(b) (exploitation of vulnerabilities) is hard to detect from
    attributes alone; we rely on a keyword check over the description.
  - Art. 5(1)(d) (predictive policing solely from profiling) we trigger from
    explicit text since we do not carry a dedicated flag.
  - Art. 5(1)(e) (untargeted facial-recognition database scraping) we trigger
    from explicit text plus the biometric flag.
  - Art. 5(1)(g) (biometric categorisation by sensitive attributes) we trigger
    from the biometric flag plus a keyword filter for sensitive categories.

Real-world classification depth comes in Phase 6 when the agent's clarify
loop fills in ambiguous attributes before this rule layer ever runs.
"""

from __future__ import annotations

from backend.agent.state import AttributeSet, Tier
from regulations.ai_act.rules._common import (
    RuleMatch,
    any_phrase,
    article_citation,
    text_search,
)

_EXPLOITATION_PHRASES = (
    "exploit vulnerabilit",
    "target vulnerable",
    "manipulat",
    "deceptive technique",
)
_PREDICTIVE_POLICING_PHRASES = (
    "predictive policing",
    "predict crim",
    "criminal risk score",
    "recidivism score",
    "criminal profiling",
)
_FACE_SCRAPING_PHRASES = (
    "scrape facial image",
    "scraping of facial",
    "facial recognition database",
    "untargeted scraping",
)
_SENSITIVE_CATEGORY_PHRASES = (
    "race",
    "ethnic",
    "political opinion",
    "religious belief",
    "trade union",
    "sexual orientation",
    "philosophical belief",
)
_WORKPLACE_OR_EDU_PHRASES = (
    "workplace",
    "workers",
    "employee",
    "school",
    "classroom",
    "educational institution",
    "vocational training",
    "students",
)


def evaluate(attributes: AttributeSet) -> RuleMatch | None:
    text = text_search(attributes)

    if attributes.uses_subliminal_techniques:
        return RuleMatch(
            tier=Tier.PROHIBITED,
            fired_rule="art_5_1_a.subliminal_or_manipulative",
            supporting_refs=(article_citation("5", paragraph="1"),),
            rationale=(
                "AI system deploys subliminal or purposefully manipulative or deceptive "
                "techniques, prohibited under Art. 5(1)(a)."
            ),
        )

    if any_phrase(text, _EXPLOITATION_PHRASES):
        return RuleMatch(
            tier=Tier.PROHIBITED,
            fired_rule="art_5_1_b.exploit_vulnerabilities",
            supporting_refs=(article_citation("5", paragraph="1"),),
            rationale=(
                "Description indicates exploitation of vulnerabilities of natural persons; "
                "prohibited under Art. 5(1)(b)."
            ),
        )

    if attributes.social_scoring:
        return RuleMatch(
            tier=Tier.PROHIBITED,
            fired_rule="art_5_1_c.social_scoring",
            supporting_refs=(article_citation("5", paragraph="1"),),
            rationale=(
                "Social scoring by or on behalf of public/private actors leading to "
                "detrimental treatment is prohibited under Art. 5(1)(c)."
            ),
        )

    if any_phrase(text, _PREDICTIVE_POLICING_PHRASES):
        return RuleMatch(
            tier=Tier.PROHIBITED,
            fired_rule="art_5_1_d.predictive_policing",
            supporting_refs=(article_citation("5", paragraph="1"),),
            rationale=(
                "AI systems making risk assessments of natural persons solely from "
                "profiling are prohibited for predictive policing under Art. 5(1)(d)."
            ),
        )

    if attributes.biometric and any_phrase(text, _FACE_SCRAPING_PHRASES):
        return RuleMatch(
            tier=Tier.PROHIBITED,
            fired_rule="art_5_1_e.facial_recognition_db_scraping",
            supporting_refs=(article_citation("5", paragraph="1"),),
            rationale=(
                "Creating or expanding facial-recognition databases through untargeted "
                "scraping is prohibited under Art. 5(1)(e)."
            ),
        )

    if attributes.emotion_recognition and any_phrase(text, _WORKPLACE_OR_EDU_PHRASES):
        return RuleMatch(
            tier=Tier.PROHIBITED,
            fired_rule="art_5_1_f.emotion_recognition_workplace_or_education",
            supporting_refs=(article_citation("5", paragraph="1"),),
            rationale=(
                "Emotion-recognition systems in workplaces or educational institutions "
                "are prohibited under Art. 5(1)(f)."
            ),
        )

    if attributes.biometric and any_phrase(text, _SENSITIVE_CATEGORY_PHRASES):
        return RuleMatch(
            tier=Tier.PROHIBITED,
            fired_rule="art_5_1_g.biometric_categorisation_sensitive",
            supporting_refs=(article_citation("5", paragraph="1"),),
            rationale=(
                "Biometric categorisation that infers sensitive categories such as race, "
                "political opinion or sexual orientation is prohibited under Art. 5(1)(g)."
            ),
        )

    if attributes.real_time_remote_biometric_id:
        return RuleMatch(
            tier=Tier.PROHIBITED,
            fired_rule="art_5_1_h.real_time_remote_biometric_id",
            supporting_refs=(article_citation("5", paragraph="1"),),
            rationale=(
                "Real-time remote biometric identification in publicly accessible spaces "
                "for law-enforcement purposes is prohibited (with narrow exceptions) under "
                "Art. 5(1)(h)."
            ),
        )

    return None
