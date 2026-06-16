"""
French rationales for the AI Act classifier.

Keyed by fired_rule. The classifier is language-agnostic (the Protocol's
classify(attributes) signature has no language parameter); we localize at
the boundary, in the report-assembly step, by swapping ClassificationResult.rationale.

When a fired_rule has no entry here, the original English rationale is kept;
that surfaces the limitation honestly rather than fabricating a translation.
"""

from __future__ import annotations

from backend.agent.state import ClassificationResult

FR_RATIONALES: dict[str, str] = {
    "default.minimal": (
        "Aucune pratique interdite, déclencheur de l'annexe I ou III, "
        "déclencheur de transparence de l'article 50 ou condition GPAI ne "
        "s'applique. Le système est classé risque minimal au sens du règlement "
        "IA. Aucune obligation impérative au titre du règlement, mais le droit "
        "commun (RGPD, etc.) reste applicable."
    ),
    "art_5_1_a.subliminal_or_manipulative": (
        "Le système recourt à des techniques subliminales ou manipulatrices "
        "susceptibles de fausser de manière significative le comportement "
        "d'une personne. Pratique interdite au titre de l'article 5(1)(a)."
    ),
    "art_5_1_b.exploit_vulnerabilities": (
        "Le système exploite des vulnérabilités liées à l'âge, au handicap ou "
        "à une situation socio-économique. Pratique interdite au titre de "
        "l'article 5(1)(b)."
    ),
    "art_5_1_c.social_scoring": (
        "Le système procède à une notation sociale susceptible d'engendrer un "
        "traitement défavorable ou préjudiciable. Pratique interdite au titre "
        "de l'article 5(1)(c)."
    ),
    "art_5_1_d.predictive_policing": (
        "Le système évalue ou prédit le risque qu'une personne physique commette "
        "une infraction pénale sur la seule base de son profil. Pratique "
        "interdite au titre de l'article 5(1)(d)."
    ),
    "art_5_1_e.facial_recognition_db_scraping": (
        "Le système crée ou enrichit des bases de données de reconnaissance "
        "faciale par moissonnage non ciblé d'images. Pratique interdite au "
        "titre de l'article 5(1)(e)."
    ),
    "art_5_1_f.emotion_recognition_workplace_or_education": (
        "Le système procède à de la reconnaissance d'émotions en milieu "
        "professionnel ou éducatif. Pratique interdite au titre de "
        "l'article 5(1)(f)."
    ),
    "art_5_1_g.biometric_categorisation_sensitive": (
        "Le système procède à de la catégorisation biométrique pour inférer "
        "des attributs sensibles (origine, opinions, religion, orientation, "
        "etc.). Pratique interdite au titre de l'article 5(1)(g)."
    ),
    "art_5_1_h.real_time_remote_biometric_id": (
        "Le système réalise une identification biométrique à distance en temps "
        "réel dans des espaces accessibles au public à des fins répressives. "
        "Pratique interdite au titre de l'article 5(1)(h), sauf exceptions "
        "strictement encadrées."
    ),
    "annex_i.safety_component_of_regulated_product": (
        "Le système est un composant de sécurité d'un produit relevant d'une "
        "législation harmonisée de l'Union (annexe I). Classé à haut risque "
        "au titre de l'article 6(1)."
    ),
    "annex_i.safety_component_unknown_legislation": (
        "Le système est désigné comme composant de sécurité d'un produit "
        "régulé, mais la législation harmonisée applicable n'est pas "
        "renseignée. Classé à haut risque par précaution au titre de "
        "l'article 6(1) ; à confirmer."
    ),
    "annex_iii_1.biometrics_flag": (
        "Le système est un système biométrique relevant de l'annexe III(1). "
        "Classé à haut risque au titre de l'article 6(2)."
    ),
    "chapter_v.gpai": (
        "Modèle d'IA à usage général au sens du chapitre V (articles 51 à 56). "
        "Obligations spécifiques applicables au titre de l'article 53."
    ),
    "chapter_v.gpai_systemic": (
        "Modèle d'IA à usage général présentant un risque systémique au sens "
        "de l'article 51(1)(a). Obligations supplémentaires au titre de "
        "l'article 55, en plus de celles de l'article 53."
    ),
}

# Annex III paragraph rationales are keyed by rule_id pattern. The article 50
# rule emits a fired_rule like "art_50.transparency_paragraphs_1_2"; we match
# that prefix and translate.

_ART50_PREFIX = "art_50.transparency_paragraphs_"
_ANNEX_III_PREFIX = "annex_iii_"


def _translate_article_50(fired_rule: str) -> str:
    suffix = fired_rule[len(_ART50_PREFIX) :].replace("_", ", ")
    return (
        f"Déclencheurs de transparence de l'article 50 identifiés "
        f"(paragraphes {suffix}). Risque limité, obligations d'information."
    )


def _translate_annex_iii(fired_rule: str) -> str:
    return (
        "Cas d'usage relevant de l'annexe III (système à haut risque "
        "autonome). Classé à haut risque au titre de l'article 6(2)."
    )


def localize_classification(
    classification: ClassificationResult, language: str
) -> ClassificationResult:
    if language.upper() != "FR":
        return classification

    fired = classification.fired_rule
    fr_rationale = FR_RATIONALES.get(fired)
    if fr_rationale is None:
        if fired.startswith(_ART50_PREFIX):
            fr_rationale = _translate_article_50(fired)
        elif fired.startswith(_ANNEX_III_PREFIX):
            fr_rationale = _translate_annex_iii(fired)
    if fr_rationale is None:
        return classification

    return classification.model_copy(update={"rationale": fr_rationale})
