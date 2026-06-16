"""
French summaries for AI Act obligations.

Keyed by obligation_id. The localizer (loader.localize_for) substitutes these
into Obligation.summary when the request language is FR. The article_ref
field stays in its language-neutral "Art. N(p)" form.
"""

from __future__ import annotations

FR_SUMMARIES: dict[str, str] = {
    "art_9.risk_management_system": (
        "Mettre en place, documenter et maintenir un système de gestion des "
        "risques couvrant tout le cycle de vie du système d'IA à haut risque."
    ),
    "art_10.data_and_data_governance": (
        "Les jeux de données d'entraînement, de validation et de test doivent "
        "faire l'objet d'une gouvernance adaptée à la finalité visée : "
        "pertinence, représentativité et atténuation des biais."
    ),
    "art_11.technical_documentation": (
        "Établir la documentation technique avant la mise sur le marché et la "
        "tenir à jour ; le contenu requis figure à l'annexe IV."
    ),
    "art_12.record_keeping": (
        "Le système à haut risque doit techniquement permettre l'enregistrement "
        "automatique des évènements (journaux) tout au long de sa durée de vie."
    ),
    "art_13.transparency_and_information": (
        "Concevoir le système de manière suffisamment transparente pour que les "
        "déployeurs puissent interpréter ses sorties et l'utiliser correctement ; "
        "fournir une notice d'utilisation."
    ),
    "art_14.human_oversight": (
        "Concevoir le système pour qu'il puisse être supervisé efficacement par "
        "des personnes physiques ; les mesures de supervision doivent être à la "
        "mesure des risques."
    ),
    "art_15.accuracy_robustness_cybersecurity": (
        "Concevoir et développer le système pour atteindre un niveau approprié "
        "d'exactitude, de robustesse et de cybersécurité tout au long de son "
        "cycle de vie."
    ),
    "art_17.quality_management_system": (
        "Mettre en place un système de gestion de la qualité couvrant les "
        "procédures de conformité, la conception, la gouvernance des données, "
        "les essais, la surveillance post-commercialisation et le signalement "
        "des incidents."
    ),
    "art_43.conformity_assessment": (
        "Soumettre le système à la procédure d'évaluation de la conformité "
        "applicable avant sa mise sur le marché ou sa mise en service."
    ),
    "art_47.declaration_of_conformity": (
        "Établir une déclaration UE de conformité écrite attestant que le "
        "système respecte les exigences applicables ; la conserver pendant "
        "dix ans."
    ),
    "art_48.ce_marking": (
        "Apposer le marquage CE sur le système d'IA à haut risque, sur son "
        "emballage ou dans la documentation qui l'accompagne."
    ),
    "art_49.registration": (
        "Enregistrer le système à haut risque dans la base de données de l'UE "
        "avant sa mise sur le marché ou sa mise en service."
    ),
    "art_26.deployer_obligations": (
        "Utiliser le système conformément aux instructions du fournisseur, "
        "affecter une supervision humaine, surveiller son fonctionnement, "
        "conserver les journaux, informer les personnes concernées lorsque "
        "requis et coopérer avec les autorités."
    ),
    "art_50_1.interaction_disclosure": (
        "Informer les personnes physiques qu'elles interagissent avec un "
        "système d'IA, sauf si cela ressort clairement des circonstances."
    ),
    "art_50_2.synthetic_content_marking": (
        "Marquer les sorties des systèmes d'IA qui génèrent des contenus "
        "synthétiques (audio, image, vidéo, texte) dans un format lisible par "
        "machine et détectable comme artificiellement généré ou manipulé."
    ),
    "art_50_3.emotion_or_biometric_notice": (
        "Les déployeurs de systèmes de reconnaissance d'émotions ou de "
        "catégorisation biométrique doivent informer les personnes physiques "
        "exposées à leur fonctionnement."
    ),
    "art_50_4.deepfake_disclosure": (
        "Les déployeurs de systèmes d'IA qui génèrent ou manipulent un contenu "
        "de type hypertrucage (« deepfake ») doivent indiquer que le contenu a "
        "été généré ou manipulé artificiellement."
    ),
    "art_53_1_a.technical_documentation_model": (
        "Établir et tenir à jour la documentation technique du modèle "
        "(processus d'entraînement et d'évaluation, résultats des essais) ; le "
        "contenu requis figure à l'annexe XI."
    ),
    "art_53_1_b.information_to_downstream_providers": (
        "Mettre informations et documentation à disposition des fournisseurs "
        "en aval qui intègreront le modèle dans leurs systèmes d'IA ; contenu "
        "minimal à l'annexe XII."
    ),
    "art_53_1_c.copyright_policy": (
        "Mettre en place une politique de respect du droit d'auteur de l'Union, "
        "notamment pour identifier et respecter les réserves de droits exprimées "
        "en application de l'article 4(3) de la directive (UE) 2019/790."
    ),
    "art_53_1_d.training_content_summary": (
        "Établir et rendre publiquement accessible un résumé suffisamment "
        "détaillé du contenu utilisé pour entraîner le modèle d'IA à usage "
        "général."
    ),
    "art_55_1_a.model_evaluation": (
        "Effectuer une évaluation du modèle selon des protocoles standardisés, "
        "incluant des tests adversariaux, afin d'identifier et d'atténuer les "
        "risques systémiques."
    ),
    "art_55_1_b.systemic_risk_assessment_mitigation": (
        "Évaluer et atténuer les risques systémiques au niveau de l'Union, y "
        "compris leurs sources, susceptibles de découler du développement, de "
        "la mise sur le marché ou de l'utilisation des modèles d'IA à usage "
        "général présentant un risque systémique."
    ),
    "art_55_1_c.incident_reporting": (
        "Suivre, documenter et signaler sans délai les incidents graves et les "
        "éventuelles mesures correctives au Bureau de l'IA et, le cas échéant, "
        "aux autorités nationales compétentes."
    ),
    "art_55_1_d.cybersecurity": (
        "Garantir un niveau adéquat de protection de cybersécurité pour le "
        "modèle et son infrastructure physique."
    ),
}
