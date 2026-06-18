# Boussole, architecture de référence

> Cible de lecture : direction conformité, RSSI, équipe achats.
> Niveau requis : compréhension générale d'un système agentique.
> Anglais : voir `docs/reference_architecture.en.md`.

## 1. Problème et contraintes

Le Règlement (UE) 2024/1689 (l'AI Act) s'applique aux systèmes d'IA mis
sur le marché ou utilisés dans l'Union. Sa logique repose sur une
classification par niveau de risque : pratique prohibée, haut risque
(Annexes I et III), risque limité (Article 50), risque minimal. À
chaque niveau correspond un jeu d'obligations différenciées pour le
fournisseur, le déployeur, l'importateur et le distributeur.

Le marché français pose trois contraintes simultanées :

- **Souveraineté**. La description d'un système d'IA, fournie à
  l'évaluation, est de la propriété intellectuelle du client. Elle ne
  doit pas transiter par une infrastructure exposée au Cloud Act
  américain.
- **Auditabilité**. La décision de classification doit être
  reproductible et justifiable, article par article. Une réponse "le
  modèle pense que..." n'est pas une trace de conformité.
- **Réalisme du calendrier**. L'AI Act entre en application par
  paliers : dispositions générales le 2 août 2026, obligations « haut
  risque » autonomes (Annexe III) repoussées au 2 décembre 2027 et
  embarquées (Annexe I) au 2 août 2028 par l'accord politique provisoire
  du Digital Omnibus du 6 mai 2026. Ces dates restent susceptibles
  d'amendement jusqu'à la publication au JOUE. Toute date inscrite en
  dur dans le code est fausse le jour suivant ; les dates sont lues
  depuis `regulations/ai_act/config/timeline.yaml`.

Boussole adresse ces trois contraintes simultanément.

## 2. Cadrage produit

Boussole n'est pas un chatbot juridique. C'est un agent qui prend en
entrée la description d'un système d'IA et produit en sortie une
pré-évaluation technique structurée comprenant :

1. La classe de risque, avec la règle qui a déclenché et les références
   exactes (Article, Annexe, Considérant).
2. La liste des obligations applicables, chacune adossée à un passage
   du texte consolidé.
3. Une analyse d'écart entre les contrôles déjà déclarés par le client
   et ces obligations.
4. Un brouillon de documentation (squelette Annexe IV, mention
   Article 50) prêt à être complété par les équipes internes.

Le rapport est cadré comme une **pré-évaluation technique destinée à
appuyer une revue juridique qualifiée**. Le système ne rend jamais de
verdict de conformité.

## 3. Architecture en une page

```
                +-----------------------------------------+
   Utilisateur  | Next.js 15 (UI, panneau de trace,       |
   client       | citations cliquables, FR + EN)          |
                +---------------------+-------------------+
                                      |
                                      |  HTTPS, EU
                                      v
                +-----------------------------------------+
                | FastAPI                                  |
                |   POST /assess     /trace/{run_id}      |
                |   /health  /ready  /metrics  /drift     |
                +---------------------+-------------------+
                                      |
                                      |  LangGraph StateGraph
                                      v
   +------------+   +------------+   +------------+   +------------+
   |  intake    |-->|  clarify   |-->|  classify  |-->|  retrieve  |
   |   (LLM)    |   |  (<= 3x)   |   |  (regles)  |   |  contexte  |
   +------------+   +------------+   +------------+   +-----+------+
                                                            |
                                                            v
                                                  +-------------------+
                                                  |  obligations      |
                                                  |  ecart            |
                                                  |  brouillons       |
                                                  |  assemble_rapport |
                                                  +---------+---------+
                                                            |
                                                            v
                                          +---------------------------------+
                                          |  Verification d'ancrage         |
                                          |  (refus si non citee)           |
                                          +---------------------------------+
                                                            |
                                                            v
                                +---------------------------------------------+
                                | Postgres (Managed OVH)                       |
                                |   pgvector + tsvector pour le corpus         |
                                |   table des manifestes d'execution           |
                                |   table des traces                            |
                                +-----------------------+----------------------+
                                                        |
                                                        v
                                             +---------------------+
                                             | vLLM / Mistral 7B   |
                                             | (OVH GPU, EU)       |
                                             +---------------------+
```

Le diagramme représente le **shape B** (mission client) : toute
flèche reste à l'intérieur de l'enveloppe OVHcloud EU. Le **shape A**
(démo publique, défaut) substitue Mistral La Plateforme à la dernière
case ; la flèche d'inférence sort alors vers l'enveloppe Mistral (FR,
EU). Les deux shapes restent souverains au sens Cloud Act ; ils
diffèrent sur la frontière du périmètre auditable par l'acheteur. Voir
ADR 0005 et section 7.

## 4. Où vivent les données

| Donnée | Localisation | Justification |
| --- | --- | --- |
| Description du système d'IA (entrée client) | Postgres OVH (France) | IP client, jamais en dehors de l'UE. |
| Texte consolidé du Règlement (UE) 2024/1689 | Postgres OVH (corpus indexé) | Texte public ; indexation locale pour le RAG. |
| Embeddings (multilingual-e5-large) | Calcul local, stockage pgvector OVH | Modèle open-weight ; aucune API externe. |
| Inférence LLM (shape A, démo) | Mistral La Plateforme (Mistral AI, FR/EU) | EU-resident, hors juridiction Cloud Act, pas de plancher GPU. |
| Inférence LLM (shape B, mission client) | vLLM sur GPU OVH (France) | Poids ouverts dans l'enveloppe OVH du client. |
| Manifeste d'exécution (run_id, versions) | Postgres OVH | Audit ; persisté par run. |
| Trace d'exécution (OpenTelemetry) | Postgres OVH + Prometheus local | Audit + observabilité. |
| Artéfacts d'évaluation (rapports, baselines) | Object Storage OVH | Versionnage des numéros publiés. |

Aucune dépendance d'inférence, d'embedding ou de stockage ne transite
par une juridiction Cloud Act, quel que soit le shape choisi. Le
compromis entre shape A et shape B (frontière du périmètre auditable
par l'acheteur, coût) est exposé en section 7.

## 5. Cartographie AI Act et RGPD

### 5.1 AI Act, niveaux et obligations

| Tier | Déclenchement | Obligations sorties par Boussole |
| --- | --- | --- |
| Pratique prohibée | Art. 5 (notation sociale, biométrie temps réel, etc.) | Art. 5 ; sortie systématique du rapport. |
| Haut risque Annexe I | Composant de sécurité d'un produit régulé (MDR, Machines, etc.) | Art. 6, 9 à 15, 17, 26, 43, 47, 48, 49. |
| Haut risque Annexe III | Usage standalone listé (emploi, justice, etc.) | Art. 6, 9 à 15, 17, 26, 43, 47, 48, 49. |
| Risque limité | Art. 50 (chatbot, contenu synthétique, deepfake) | Art. 50 (paragraphe précis selon la nature). |
| Risque minimal | Aucun déclencheur | Pas d'obligation matérielle, RGPD demeure. |
| GPAI | Modèle d'usage général | Art. 53. |
| GPAI risque systémique | Désignation Art. 51(1)(b) ou seuil de compute | Art. 51, 53, 55. |

Le moteur de règles est déterministe (ADR 0002). Le LLM extrait les
attributs ; les règles statuent.

### 5.2 RGPD

L'RGPD s'applique en parallèle. Boussole ne stocke aucune donnée
personnelle dans la description : les pages "intake" préviennent
l'utilisateur de ne pas en saisir, et la documentation rappelle que
toute donnée personnelle relève du traitement séparé sous RGPD. La
description elle-même est cryptée au repos (chiffrement Postgres au
niveau de l'instance OVH gérée) et en transit (TLS 1.3).

### 5.3 Cloud Act et SecNumCloud

Le choix OVHcloud (acteur français incorporé en France) ferme
l'exposition Cloud Act. Pour les clients exigeant la qualification
SecNumCloud (secteur public sensible, HDS, défense-adjacent), la même
architecture Terraform se réplique sur Outscale moyennant
substitution du provider Terraform. Le code applicatif est identique.

## 6. Pile technique

| Couche | Choix | Pourquoi |
| --- | --- | --- |
| Modèle (shape A, défaut démo) | Mistral La Plateforme, `mistral-large-latest` | Managé EU, pay-per-token, pas de plancher GPU. |
| Modèle (shape B, mission client) | Mistral 7B Instruct via vLLM sur GPU OVH | Poids ouverts entièrement dans le projet OVH du client. |
| Embeddings | multilingual-e5-large auto-hébergé | FR + EN, inférence en juridiction. |
| Stockage vectoriel | pgvector (Postgres) | Souverain, simple, pas de dépendance tierce. |
| Recherche | Hybride dense + tsvector + RRF + reranker | Voir ADR 0004 (le texte légal exige le sparse). |
| Orchestration | LangGraph StateGraph | Explicite, observable, pas de magie d'agent. |
| Outils | MCP (Python SDK) | Frontières outil claires, inspectables. |
| Backend | FastAPI, Python 3.11+ | Typage, FastAPI mature. |
| Frontend | Next.js 15, Tailwind 4, Inter Tight | Statique-first, sobre, rapide. |
| Hébergement | OVHcloud Public Cloud (GRA / SBG / RBX) | Souverain, multi-régions FR. |
| IaC | Terraform | Reproductible, neutre vendeur. |
| Conteneurisation | Docker multi-stage | Image runtime minimale. |
| Observabilité | OpenTelemetry + Prometheus auto-hébergés | Trace + métriques sans dépendance tierce. |

## 7. Compromis assumés

- **Mistral La Plateforme managée vs vLLM auto-hébergé**. Le défaut
  documenté est **La Plateforme** pour la démo publique
  `aiact.ceres.broker` : Mistral AI est incorporé en France, ses
  endpoints sont EU-resident, le périmètre Cloud Act reste fermé, et
  le coût est aligné sur l'usage (pas de plancher GPU). Pour une
  mission client où la description du système ne doit pas quitter
  l'enveloppe OVH du client, le shape B (vLLM auto-hébergé sur
  instance GPU OVH) est sélectionné par variable d'environnement
  (`BOUSSOLE_LLM_URL`), sans changement de code (ADR 0003, port
  `LLMProvider`). L'acheteur choisit ; l'architecture absorbe.
- **OVH Managed Postgres et pgvector**. L'extension `vector` est
  disponible sur les plans récents. Un test de disponibilité conditionne
  l'`apply` Terraform. Le fallback documenté est Postgres auto-hébergé
  sur VM dans le même projet OVH.
- **Reranker cross-encoder**. bge-reranker-v2 est open-weight mais
  n'est pas aligné Mistral. Un équivalent EU-resident est suivi en
  veille pour une substitution Phase 12.

## 8. Cycle de vie d'une évaluation

1. Le client soumet une description via la page d'intake.
2. Le nœud `intake` extrait un `AttributeSet` typé (LLM, température 0).
3. Si des attributs critiques manquent, le nœud `clarify` pose une
   question ciblée et boucle (au plus trois itérations).
4. Le nœud `classify` exécute la couche de règles déterministe sur
   l'`AttributeSet` et produit un `ClassificationResult` (tier + règle
   + références).
5. Le nœud `retrieve_context` interroge la couche RAG par scopes
   (Art. 5, Annexe III, Art. 50, etc.) pour récupérer les passages
   nécessaires.
6. Le nœud `enumerate_obligations` matérialise les obligations
   applicables au tier.
7. Le nœud `gap_analysis` compare les contrôles déclarés aux
   obligations requises.
8. Le nœud `draft_docs` génère un squelette de documentation (Annexe
   IV, mention Art. 50) à partir de templates versionnés.
9. Le nœud `assemble_report` vérifie l'ancrage : toute affirmation
   juridique du rapport doit pointer vers un passage récupéré. Une
   violation bloque la réponse.
10. Le rapport, le manifeste d'exécution et la trace OpenTelemetry sont
    persistés. L'UI affiche le tout.

## 9. Limites explicites

Boussole **ne rend pas** un verdict juridique. La sortie est cadrée
comme une pré-évaluation technique. Elle ne se substitue pas à la
revue d'un conseil qualifié. Le rapport contient cette mention dans le
corps et à l'export.

Boussole **ne traite pas** les données personnelles des sujets du
système d'IA. Les obligations RGPD restent à la charge du client.

Boussole **ne garantit pas** la conformité d'un système ; il identifie
les obligations qui s'appliquent et signale les écarts par rapport aux
contrôles déclarés.

## 10. Mesure

Un jeu d'évaluation (`eval/gold_set.jsonl`) couvre les sept tiers, 15
domaines, trois tranches (stratifiée, difficile, adverse). Sept gates
sont publiés dans CI :

| Métrique | Seuil |
| --- | ---: |
| Précision de classification (tier) | >= 0.90 |
| Précision de citation | >= 0.95 |
| Rappel de citation | >= 0.80 |
| Ancrage (groundedness) | = 1.00 |
| Rappel d'obligations | >= 0.85 |
| Faux-négatif haut-risque | <= 0.02 |
| Résistance à l'injection | >= 0.95 |

Une régression bloque le déploiement. Les baselines sont gelées par
`corpus_version` ; une réindexation produit un diff article par
article et déclenche une ré-évaluation.

## 11. Pour aller plus loin

- ADR 0001 : la trace est le produit.
- ADR 0002 : les règles statuent, pas le LLM.
- ADR 0003 : la régulation comme plugin.
- ADR 0004 : la recherche hybride est obligatoire.
- ADR 0005 : production sur OVHcloud.
- ADR 0006 : surface LLMOps (cache, télémétrie, dérive).
- `docs/runbook_rollback.md` : procédure de rollback opérationnelle.
- `TASKS_USER.md` : actions opérateur (provisioning OVH, revue règles,
  curation du jeu d'évaluation).
