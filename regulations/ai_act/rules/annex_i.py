"""
Annex I high-risk track: AI systems that are safety components of products
falling under Union harmonisation legislation listed in Annex I.

Trigger (Art. 6(1) in combination with Annex I): the AI system is (a) a
safety component of a product covered by the legislation listed in Annex I,
or (b) is itself such a product, AND (c) the product is required to undergo
third-party conformity assessment under that legislation.

We trust two explicit AttributeSet flags here:
  - is_safety_component
  - regulated_product_legislation (non-empty)

A small recognised-legislation set is checked to give the rule a meaningful
fired_rule string and to surface the underlying regulation in the rationale.
Unknown legislation strings still trigger Annex I; the rule just notes that
the specific instrument is not recognised by this build.
"""

from __future__ import annotations

from backend.agent.state import AttributeSet, Tier
from regulations.ai_act.rules._common import (
    RuleMatch,
    annex_citation,
    article_citation,
)

# Each entry: substring (case-insensitive) that should appear in
# attributes.regulated_product_legislation, plus a short label.
RECOGNISED_LEGISLATION: tuple[tuple[str, str], ...] = (
    ("machinery", "Machinery Regulation (EU) 2023/1230"),
    ("toy safety", "Toy Safety Directive 2009/48/EC"),
    ("recreational craft", "Recreational Craft Directive 2013/53/EU"),
    ("lift", "Lifts Directive 2014/33/EU"),
    ("atex", "ATEX Directive 2014/34/EU"),
    ("radio equipment", "Radio Equipment Directive 2014/53/EU"),
    ("pressure equipment", "Pressure Equipment Directive 2014/68/EU"),
    ("cableway", "Cableway Installations Regulation (EU) 2016/424"),
    ("ppe", "PPE Regulation (EU) 2016/425"),
    ("personal protective", "PPE Regulation (EU) 2016/425"),
    ("gas appliance", "Gas Appliances Regulation (EU) 2016/426"),
    ("medical device", "Medical Devices Regulation (EU) 2017/745"),
    ("in vitro diagnostic", "IVDR (EU) 2017/746"),
    ("ivdr", "IVDR (EU) 2017/746"),
    ("civil aviation", "Civil Aviation Regulation (EU) 2018/1139"),
    ("agricultural vehicle", "Agricultural/Forestry Vehicles Regulation (EU) 167/2013"),
    ("forestry vehicle", "Agricultural/Forestry Vehicles Regulation (EU) 167/2013"),
    ("marine equipment", "Marine Equipment Directive 2014/90/EU"),
    ("railway interoperability", "Railway Interoperability Directive (EU) 2016/797"),
    ("motor vehicle", "Type-Approval Regulation (EU) 2018/858"),
)


def _identify_legislation(legislation: str) -> str | None:
    text = legislation.lower()
    for needle, label in RECOGNISED_LEGISLATION:
        if needle in text:
            return label
    return None


def evaluate(attributes: AttributeSet) -> RuleMatch | None:
    if not attributes.is_safety_component:
        return None
    if not attributes.regulated_product_legislation:
        return None

    label = _identify_legislation(attributes.regulated_product_legislation)
    supporting = (
        article_citation("6", paragraph="1"),
        annex_citation("I"),
    )

    if label:
        return RuleMatch(
            tier=Tier.HIGH_RISK_ANNEX_I,
            fired_rule="annex_i.safety_component_of_regulated_product",
            supporting_refs=supporting,
            rationale=(
                f"AI system declared as a safety component of a product covered by "
                f"{label}, which is listed in Annex I; classified as high-risk under "
                f"Art. 6(1)."
            ),
        )

    return RuleMatch(
        tier=Tier.HIGH_RISK_ANNEX_I,
        fired_rule="annex_i.safety_component_unknown_legislation",
        supporting_refs=supporting,
        rationale=(
            "AI system declared as a safety component of a regulated product, but the "
            "stated legislation does not match the recognised Annex I list in this "
            "build. Treating as high-risk under Art. 6(1); confirm with counsel that "
            "the cited legislation appears in Annex I."
        ),
        confidence=0.6,
    )
