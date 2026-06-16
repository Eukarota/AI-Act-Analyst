# Boussole

> Pré-évaluation technique d'un système d'IA contre le Règlement (UE) 2024/1689 (AI Act). Glass-box, ancrée, souveraine.
>
> Technical pre-assessment of an AI system against Regulation (EU) 2024/1689 (the AI Act). Glass-box, grounded, sovereign.

[Français](#français) · [English](#english)

---

## Français

### Présentation

Boussole prend en entrée la description d'un système d'IA et produit un rapport structuré : niveau de risque au sens du Règlement (UE) 2024/1689, obligations applicables, analyse d'écart contre les contrôles déclarés, squelettes de documentation (annexe IV, articles 50). Chaque affirmation juridique est ancrée à un passage précis du texte consolidé (article, paragraphe, annexe, considérant).

Boussole n'est pas un avis juridique. Le rapport est cadré comme une pré-évaluation technique destinée à appuyer une revue qualifiée. C'est volontaire : le seul agent crédible auprès d'un service conformité est celui qui *refuse* de produire un verdict.

### Pour les CTO et les recruteurs

Ce projet démontre cinq compétences qui ne se voient pas dans un CV :

1. **Conception d'agents en production**, pas de démos. Graphe d'état explicite (LangGraph), boucle de clarification bornée, taxonomie d'erreurs typées, échec explicite plutôt que dégradation silencieuse vers une réponse fabriquée.
2. **Ingénierie de contexte mature.** Récupération hybride (dense + sparse) fusionnée par Reciprocal Rank Fusion, re-ranker cross-encoder, scope par nœud du graphe, injection des termes définis. Pas de RAG « top-k naïf ».
3. **Discipline LLMOps.** Manifeste de run versionné, registre de prompts à sha-pinned, pipeline de corpus idempotente avec rapport de diff, contrôle d'ancrage identique en eval et en prod (même fonction, deux appelants).
4. **Souveraineté tenue par construction.** Modèle, embeddings, base vectorielle, persistance : tout reste dans l'enveloppe OVHcloud UE. La sécurité n'est pas une promesse marketing, c'est une contrainte d'architecture vérifiable.
5. **Modèle économique du portfolio = modèle économique du métier.** Provisionnement Terraform à la demande (15 min apply, 5 min destroy). Le coût de tourner la démo est de zéro entre deux sessions. C'est exactement comme une vraie mission d'évaluation AI Act se vend : un environnement dédié par engagement, détruit à la livraison.

### Fonctionnalités

**Agent et orchestration**

- Graphe d'état Pydantic-typé sous LangGraph : `intake → clarify (boucle bornée ≤ 3) → classify → retrieve_context → enumerate_obligations → gap_analysis → draft_docs → assemble_report`.
- Cinq serveurs MCP exposant chaque capacité : `retrieve_law`, `classify_risk`, `lookup_obligations`, `analyze_gaps`, `draft_documentation`.
- Boucle de clarification interactive : l'agent identifie les attributs sous-spécifiés et pose des questions ciblées (« quel humain examine les sorties ? », « contexte de déploiement ? »). Réponses renvoyées en boucle dans une nouvelle évaluation.
- Budgets bornés par nœud (timeout) et par run (token budget, tool-call budget). Aucune boucle infinie possible.

**Couche de règles déterministe**

- Classification = fonction pure `classify(AttributeSet) -> ClassificationResult`. Le LLM extrait les attributs (température 0), les règles statuent.
- Ordre déterministe : Article 5 (pratiques interdites) → Annexe I (composants de sécurité de produits régulés) → Annexe III (cas autonomes à haut risque) → Article 50 (transparence) → minimal. Voie parallèle pour les modèles GPAI (Chapitre V, seuil systémique selon l'article 55).
- Chaque règle renvoie l'identifiant qui s'est déclenché et les références d'articles à l'appui. Reproductible : même `AttributeSet` + même `rules_version` => même résultat.
- Tests pilotés par tables sur chaque branche, y compris les cas-frontières (annexe III boundaries, GPAI vs système-construit-sur-GPAI).

**Récupération et ancrage**

- Corpus : texte consolidé du Règlement (UE) 2024/1689 récupéré depuis le cellar du Publications Office UE, soit ~880 chunks (180 considérants, ~560 paragraphes d'articles, ~140 points d'annexes). Versionné, immuable, hashé.
- Récupération hybride : dense via `multilingual-e5-large` (1024d) sur `pgvector`, sparse via `tsvector` PostgreSQL, fusion par Reciprocal Rank Fusion, re-ranker cross-encoder `bge-reranker-v2`. Le pur-dense échoue sur le texte juridique (les numéros d'articles et termes définis exigent un recall exact).
- Récupération scopée par nœud : `classify` lit Art. 5 + Annexes I/III, `enumerate_obligations` lit Art. 8 à 15 / 26 / 50 / 53. Pas de passe globale unique.
- Contrat d'ancrage (`assert_grounded`) : toute affirmation juridique non couverte par un passage du corpus retourné dans le tour courant est rejetée par construction. Fonction unique, deux appelants (eval et prod). Pas de chemins parallèles.

**Boîte de verre (glass-box trace)**

- Une span OpenTelemetry par nœud du graphe et par appel d'outil, avec hash d'entrée, latence, tokens, `model_id`.
- Le panneau de trace en UI rend exactement le même flux d'évènements : aucun chemin de log dédié à la démo.
- Cube 3D des embeddings (Three.js + PCA) : visualisation interactive du corpus avec mise en surbrillance des passages effectivement consultés par l'agent. Mode plein écran.
- Manifeste de run persisté pour chaque évaluation : `{run_id, corpus_version, model_id, embedding_model, prompt_set_version, rules_version, timestamp}`. Rien ne tourne sans version épinglée.

**LLMOps et reproductibilité**

- Registre de prompts (`prompts/registry.yaml`) : nom → version + sha. Aucun prompt inliné nulle part dans le code.
- Pipeline de corpus idempotente : `scripts/index_corpus.py` ré-indexe avec rapport de diff (quels articles ont changé) et émet un nouveau `corpus_version`.
- Cache de récupération clé par `corpus_version`, cache sémantique pour les sous-requêtes répétées.
- Télémétrie Prometheus exposée sur `/metrics` : latence p95, tokens entrants/sortants par évaluation, taux de hit du cache, taux d'ancrage. Dérive de domaine et de tier suivie sur `/drift`.
- Garde d'ancrage en ligne : la vérification de l'eval tourne aussi sur chaque réponse de `/assess`. Une violation bloque la réponse (HTTP 502) et lève une alerte.

**Frontend (Next.js)**

- Intake conversationnelle plutôt que formulaire rigide, avec exemples prêts à charger (recrutement, social scoring, traduction, chatbot).
- Rapport structuré : tier de risque, manifeste pliable, obligations cliquables vers leurs citations, écarts contre contrôles déclarés, brouillons de documents repliables.
- Trace en temps réel rendue dans la colonne de droite, événements typés (node_start, tool_call, retrieval, grounding_check, etc.).
- Bilingue intégral FR / EN : prompt, rationale de classification, résumés d'obligations, notes d'écart, squelette annexe IV, notice de pré-évaluation. Bascule en localStorage.
- Identité visuelle inspirée de l'agence Ceres Broker (capsules glass-morph, Inter Tight, transitions Framer Motion).

**Souveraineté et conformité**

- Modèle : Mistral La Plateforme (endpoint UE, opérateur français), ou vLLM auto-hébergé sur GPU OVH pour les missions où la description du système ne doit jamais quitter l'enveloppe client.
- Embeddings : `multilingual-e5-large` chargé localement via `sentence-transformers`.
- Base vectorielle : `pgvector` sur Postgres managé OVHcloud.
- Aucune dépendance Cloud Act dans le chemin d'inférence, d'embedding ou de stockage. Documenté article par article dans `docs/reference_architecture.md`.

**Adaptabilité (régulation comme plugin)**

- Le cœur de l'agent est régulation-agnostique. Toute régulation (AI Act aujourd'hui, RGPD, DORA, NIS2 demain) implémente le Protocol `Regulation { corpus_loader, chunker_config, classifier_rules, obligations_map, document_templates, defined_terms, timeline }`.
- Suite de conformité (`tests/regulation_conformance/`) : une régulation-fixture passée end-to-end. Toute nouvelle régulation doit la passer. L'adaptabilité est vérifiée, pas asseratée.
- Aucune date réglementaire codée en dur. Tout est sous `regulations/<nom>/config/timeline.yaml`, sourcé.

### Architecture et fonctionnement

```
Client (Next.js)
   │  POST /assess (description, controls, role, language)
   ▼
FastAPI + LangGraph
   │  state graph (Pydantic AgentState)
   │
   │  intake (LLM, T=0) ──► extraction des attributs
   │     │
   │     └──► clarify (≤ 3 itérations) si attribut load-bearing manquant
   │
   │  classify (règles pures) ──► tier + fired_rule + supporting_refs
   │     │
   │  retrieve_context (MCP retrieve_law) ──► passages cités avec ancrage
   │     │   dense (e5) + sparse (tsvector) + RRF + bge-reranker
   │     │
   │  enumerate_obligations (MCP) ──► obligations applicables par rôle
   │     │
   │  gap_analysis (MCP) ──► écart contre les contrôles déclarés
   │     │
   │  draft_docs (MCP, T > 0 autorisée ici uniquement) ──► annexe IV + Art. 50
   │     │
   │  assemble_report ──► assert_grounded(report)
   │     │
   ▼
HTTP 200 + AssessmentReport (manifest, tier, obligations, gaps, drafts, citations)
HTTP 502 si une affirmation est non-ancrée
```

Trois propriétés que cette architecture rend vraies plutôt que promises :

1. **Le LLM ne décide jamais le tier de risque.** Il extrait des attributs structurés à température 0. La fonction `classify` est testable en tableau, reproductible, auditable. Un compliance officer peut suivre la règle qui s'est déclenchée et la confronter au texte.
2. **Aucune affirmation juridique non-ancrée ne sort.** L'ancrage est une fonction unique (`backend/rag/grounding.py`) appelée à la fois par l'eval et par le runner de prod. Pas d'écart possible entre « ce qui passe en CI » et « ce qui passe en ligne ».
3. **Toute évaluation est reproductible.** Le manifeste contient `(corpus_version, model_id, embedding_model, prompt_set_version, rules_version)`. Rejouer une évaluation à six mois sur un autre laptop est mécanique.

### Pile technique

| Couche | Choix |
| --- | --- |
| Modèle | Mistral La Plateforme (`mistral-large-latest`, endpoint UE) ou vLLM auto-hébergé |
| Embeddings | `intfloat/multilingual-e5-large` via `sentence-transformers` |
| Base vectorielle | PostgreSQL 16 + `pgvector` |
| Re-ranker | `BAAI/bge-reranker-v2-m3` |
| Orchestration | LangGraph (state graph Pydantic) |
| Outils | MCP Python SDK (cinq serveurs) |
| Backend | Python 3.11, FastAPI, asyncpg, structlog, Pydantic v2 |
| Frontend | Next.js 15 (App Router), React 19, Tailwind CSS 4, Framer Motion, Three.js |
| Observabilité | OpenTelemetry, Prometheus (`/metrics`), structlog JSON |
| Infrastructure | OVHcloud Public Cloud, Managed Postgres, Kapsule (Kubernetes managé) |
| IaC | Terraform |
| Qualité | ruff, mypy, pytest |

### Démarrer en local

Prérequis : Docker, Python 3.11+, Node 20+, [uv](https://docs.astral.sh/uv/), une clé Mistral La Plateforme.

```bash
# 1. Cloner et installer les dépendances Python
make install

# 2. Renseigner .env (voir .env.example)
#    Minimum : MISTRAL_API_KEY=...
cp .env.example .env

# 3. Lever Postgres + indexer le corpus AI Act + projeter le cube 3D
make demo-local

# 4. Dans deux terminaux séparés
make dev-backend     # FastAPI sur :8000
make dev-frontend    # Next.js sur :3000

# 5. Ouvrir http://localhost:3000

# Tout démonter
make demo-local-down
```

La première indexation télécharge le texte officiel du JOUE depuis le cellar du Publications Office (~1 Mo), génère 881 chunks et embed la totalité avec `multilingual-e5-large` (~1.1 Go de poids chargés localement). Compter 5 à 10 minutes en CPU sur la première exécution. Le cube 3D du corpus est projeté immédiatement après.

### Provisionnement OVHcloud à la demande

Le stack complet (projet Public Cloud + Managed Postgres + Kapsule + Object Storage) se provisionne et se détruit via Terraform :

```bash
make demo-up      # terraform apply, ~15 min, affiche les outputs
# walkthrough avec le client ou le recruteur
make demo-down    # terraform destroy, retour à zéro sur ces lignes de facture
```

Voir `infra/terraform/`, `infra/k8s/` et `docs/adr/0005-ovh-hosting.md`.

### Endpoints

| Méthode | Chemin | Rôle |
| --- | --- | --- |
| POST | `/assess` | Lance une évaluation, renvoie l'`AssessmentReport`. |
| GET  | `/trace/{run_id}` | Trace OTel persistée. |
| GET  | `/health` | Liveness. |
| GET  | `/ready` | Readiness (run-store + DB). |
| GET  | `/metrics` | Format Prometheus 0.0.4. |
| GET  | `/drift` | Distributions roulantes (domaine, tier). |

### Variables d'environnement

| Clé | Défaut | Rôle |
| --- | --- | --- |
| `MISTRAL_API_KEY` (alias `BOUSSOLE_LLM_API_KEY`) | _vide_ | Clé La Plateforme. Vide => vLLM auto-hébergé attendu. |
| `BOUSSOLE_LLM_URL` | `http://localhost:11434` | Endpoint OpenAI-compatible. En prod : `https://api.mistral.ai` ou le service vLLM in-cluster. |
| `BOUSSOLE_LLM_MODEL` | `mistral:7b-instruct` | Identifiant du modèle. En prod : `mistral-large-latest`. |
| `BOUSSOLE_DATABASE_URL` | `postgresql://boussole:boussole@localhost:5432/boussole` | DSN Postgres (run-store + corpus pgvector). |
| `BOUSSOLE_USE_IN_MEMORY_STORE` | `false` | `true` pour dev sans Postgres. |
| `BOUSSOLE_FIXTURE_CORPUS` | `false` | `true` pour charger l'extrait fixture + FakeEmbedder (CI, smoke). |
| `BOUSSOLE_REGULATION` | `ai_act` | Plugin de régulation actif. |
| `BOUSSOLE_LOG_LEVEL` | `INFO` | Niveau structlog. |

### Tests et évaluation

```bash
make test         # suite unit (sans intégration, sans eval)
make smoke        # smoke Phase 1
make eval-smoke   # 5 cas de smoke (gating CI)
make eval         # eval gold contre la baseline (CLAUDE.md §12.1)
```

Le jeu d'évaluation (gold set) fige les gates §12.1 : exactitude par tier, précision et rappel des citations, taux d'ancrage, rappel des obligations, taux de faux-négatifs sur le haut risque, résistance à l'injection. La régression bloque le déploiement.

### Limites connues (honnêtes)

- Le gold set est à 30 cas seedés, sous extension. Les gates §12.1 ne sont pas encore mordants en CI.
- Le coloriage par-nœud des points retrouvés dans le cube RAG n'est pas implémenté : tous les chunks consultés partagent une seule couleur.
- Le texte des passages affiché à l'utilisateur reste en EN même quand `language=FR` : le corpus FR est supporté côté fetcher / parser mais n'est pas encore indexé par défaut.
- L'étape `draft_documentation` est principalement gabarit pour l'instant ; l'enrichissement LLM y est gated et minimal.

### Licence

Propriétaire. Contact Ceres Broker pour licensing.

---

## English

### Overview

Boussole takes the description of an AI system as input and produces a structured report: risk tier under Regulation (EU) 2024/1689, applicable obligations, gap analysis against declared controls, drafted documentation skeletons (Annex IV, Article 50). Every legal claim is grounded to a specific passage of the consolidated text (article, paragraph, annex, recital).

Boussole is not legal advice. The report is framed as a technical pre-assessment intended to support qualified legal review. That framing is deliberate: the only agent a compliance officer will trust is one that *refuses* to render a verdict.

### For CTOs and recruiters

This project demonstrates five engineering skills that don't show up on a CV:

1. **Designing agents for production**, not demos. Explicit state graph (LangGraph), bounded clarify loop, typed error taxonomy, explicit failure rather than silent degradation to a fabricated answer.
2. **Mature context engineering.** Hybrid retrieval (dense + sparse) fused via Reciprocal Rank Fusion, cross-encoder re-ranker, per-node retrieval scope, defined-terms injection. No naïve "top-k embedding lookup."
3. **LLMOps discipline.** Versioned run manifest, sha-pinned prompt registry, idempotent corpus pipeline with diff report, grounding check identical in eval and in prod (one function, two callers).
4. **Sovereignty as an architectural invariant.** Model, embeddings, vector store, persistence: every component stays inside the OVHcloud EU envelope. Sovereignty is not a marketing promise; it is a verifiable architectural constraint.
5. **The portfolio's economics mirror the work's economics.** Terraform-driven provisioning (15 min apply, 5 min destroy). Cost-to-run between sessions: zero. That is exactly how a real AI Act assessment engagement is sold: dedicated environment per mission, torn down on delivery.

### Features

**Agent and orchestration**

- Pydantic-typed state graph on LangGraph: `intake → clarify (bounded ≤ 3) → classify → retrieve_context → enumerate_obligations → gap_analysis → draft_docs → assemble_report`.
- Five MCP servers exposing each capability: `retrieve_law`, `classify_risk`, `lookup_obligations`, `analyze_gaps`, `draft_documentation`.
- Interactive clarification loop: the agent identifies under-specified load-bearing attributes and asks targeted questions ("who reviews the outputs?", "deployment context?"). Answers are folded back into a new assessment.
- Bounded budgets per node (timeout) and per run (token, tool-call). No unbounded loops.

**Deterministic rules layer**

- Classification is a pure function `classify(AttributeSet) -> ClassificationResult`. The LLM extracts attributes (temperature 0); the rules decide.
- Deterministic ordering: Article 5 (prohibitions) → Annex I (safety components of regulated products) → Annex III (standalone high-risk) → Article 50 (transparency) → minimal. Parallel track for GPAI models (Chapter V, systemic threshold per Article 55).
- Each rule emits the identifier that fired and supporting article refs. Reproducible: same `AttributeSet` + same `rules_version` => identical result.
- Table-driven tests on every branch, including boundary cases (Annex III boundaries, GPAI vs system-built-on-GPAI).

**Retrieval and grounding**

- Corpus: consolidated text of Regulation (EU) 2024/1689 pulled from the EU Publications Office cellar, yielding ~880 chunks (180 recitals, ~560 article paragraphs, ~140 annex points). Versioned, immutable, hashed.
- Hybrid retrieval: dense via `multilingual-e5-large` (1024-d) over `pgvector`, sparse via PostgreSQL `tsvector`, fused with Reciprocal Rank Fusion, re-ranked by `bge-reranker-v2`. Pure-dense fails on legal text (article numbers and defined terms require exact-match recall).
- Per-node scoped retrieval: `classify` queries Art. 5 + Annexes I/III; `enumerate_obligations` queries Art. 8–15 / 26 / 50 / 53. No single global pass.
- Grounding contract (`assert_grounded`): any legal claim not backed by a passage retrieved in the current turn is rejected by construction. One function, two callers (eval and prod). No parallel paths.

**Glass-box trace**

- One OpenTelemetry span per graph node and per tool call, recording input hash, latency, tokens, `model_id`.
- The UI trace panel renders the exact same event stream. No "demo" logging path.
- 3D embedding cube (Three.js + PCA): interactive visualization of the corpus with the retrieved chunks highlighted in real time. Fullscreen mode.
- Run manifest persisted per assessment: `{run_id, corpus_version, model_id, embedding_model, prompt_set_version, rules_version, timestamp}`. Nothing runs unversioned.

**LLMOps and reproducibility**

- Prompt registry (`prompts/registry.yaml`): name → version + sha. No prompts inlined anywhere in the code.
- Idempotent corpus pipeline: `scripts/index_corpus.py` produces a diff report (which articles changed) and a new `corpus_version` on every re-index.
- Retrieval cache keyed by `corpus_version`, semantic cache for repeated sub-queries.
- Prometheus telemetry on `/metrics`: p95 latency, tokens in/out per assessment, cache hit rate, groundedness rate. Domain and tier drift on `/drift`.
- Online grounding check: the same assertion that runs in eval also runs on every `/assess` response. A violation blocks the response (HTTP 502) and raises an alert.

**Frontend (Next.js)**

- Conversational intake rather than rigid form, with ready-to-load examples (recruitment, social scoring, translation, chatbot).
- Structured report: risk tier, collapsible run manifest, citation-linked obligations, gap analysis against declared controls, collapsible document drafts.
- Real-time trace rendered in the right column, typed events (node_start, tool_call, retrieval, grounding_check, ...).
- Fully bilingual EN / FR: prompts, classification rationale, obligation summaries, gap notes, Annex IV skeleton, pre-assessment notice. Switch persisted in localStorage.
- Visual identity inspired by the Ceres Broker agency (glass-morph capsules, Inter Tight, Framer Motion transitions).

**Sovereignty and compliance**

- Model: Mistral La Plateforme (EU endpoint, French operator), or self-hosted vLLM on OVH GPU for missions where the system description must never leave the client envelope.
- Embeddings: `multilingual-e5-large` loaded locally via `sentence-transformers`.
- Vector store: `pgvector` on OVHcloud Managed Postgres.
- No Cloud Act dependency in the inference, embedding, or storage path. Documented article by article in `docs/reference_architecture.md`.

**Adaptability (regulation-as-plugin)**

- The agent core is regulation-agnostic. Any regulation (AI Act today; GDPR, DORA, NIS2 tomorrow) implements the `Regulation { corpus_loader, chunker_config, classifier_rules, obligations_map, document_templates, defined_terms, timeline }` Protocol.
- Conformance suite (`tests/regulation_conformance/`): a fixture regulation runs end-to-end. Any new regulation must pass it. Adaptability is verified, not asserted.
- No regulatory date hardcoded anywhere. Everything lives under `regulations/<name>/config/timeline.yaml`, with its source.

### Architecture and flow

```
Client (Next.js)
   │  POST /assess (description, controls, role, language)
   ▼
FastAPI + LangGraph
   │  state graph (Pydantic AgentState)
   │
   │  intake (LLM, T=0) ──► attribute extraction
   │     │
   │     └──► clarify (≤ 3 iterations) if a load-bearing attribute is missing
   │
   │  classify (pure rules) ──► tier + fired_rule + supporting_refs
   │     │
   │  retrieve_context (MCP retrieve_law) ──► cited grounded passages
   │     │   dense (e5) + sparse (tsvector) + RRF + bge-reranker
   │     │
   │  enumerate_obligations (MCP) ──► obligations applicable by role
   │     │
   │  gap_analysis (MCP) ──► gap against declared controls
   │     │
   │  draft_docs (MCP, T > 0 allowed here only) ──► Annex IV + Art. 50
   │     │
   │  assemble_report ──► assert_grounded(report)
   │     │
   ▼
HTTP 200 + AssessmentReport (manifest, tier, obligations, gaps, drafts, citations)
HTTP 502 if any claim is ungrounded
```

Three properties the architecture makes true rather than promised:

1. **The LLM never decides the risk tier.** It extracts structured attributes at temperature 0. `classify` is table-tested, reproducible, auditable. A compliance officer can follow the rule that fired and check it against the consolidated text.
2. **No ungrounded legal claim escapes.** Grounding is one function (`backend/rag/grounding.py`) called by both the eval and the prod runner. No drift possible between "what passes in CI" and "what passes online."
3. **Every assessment is reproducible.** The manifest carries `(corpus_version, model_id, embedding_model, prompt_set_version, rules_version)`. Replaying an assessment six months later on a different machine is mechanical.

### Stack

| Layer | Choice |
| --- | --- |
| Model | Mistral La Plateforme (`mistral-large-latest`, EU endpoint) or self-hosted vLLM |
| Embeddings | `intfloat/multilingual-e5-large` via `sentence-transformers` |
| Vector store | PostgreSQL 16 + `pgvector` |
| Re-ranker | `BAAI/bge-reranker-v2-m3` |
| Orchestration | LangGraph (Pydantic state graph) |
| Tools | MCP Python SDK (five servers) |
| Backend | Python 3.11, FastAPI, asyncpg, structlog, Pydantic v2 |
| Frontend | Next.js 15 (App Router), React 19, Tailwind CSS 4, Framer Motion, Three.js |
| Observability | OpenTelemetry, Prometheus (`/metrics`), structlog JSON |
| Infrastructure | OVHcloud Public Cloud, Managed Postgres, Kapsule (managed Kubernetes) |
| IaC | Terraform |
| Quality gates | ruff, mypy, pytest |

### Run it locally

Prerequisites: Docker, Python 3.11+, Node 20+, [uv](https://docs.astral.sh/uv/), a Mistral La Plateforme key.

```bash
# 1. Clone and install Python dependencies
make install

# 2. Fill .env (see .env.example)
#    Minimum: MISTRAL_API_KEY=...
cp .env.example .env

# 3. Bring up Postgres + index the AI Act corpus + project the 3D cube
make demo-local

# 4. In two separate terminals
make dev-backend     # FastAPI on :8000
make dev-frontend    # Next.js on :3000

# 5. Open http://localhost:3000

# Tear everything down
make demo-local-down
```

The first index pulls the OJ EU text from the Publications Office cellar (~1 MB), produces 881 chunks, and embeds them locally with `multilingual-e5-large` (~1.1 GB of weights). Expect 5 to 10 minutes on CPU for the first run. The 3D corpus cube is projected immediately after.

### On-demand OVHcloud provisioning

The full stack (Public Cloud project + Managed Postgres + Kapsule + Object Storage) provisions and destroys via Terraform:

```bash
make demo-up      # terraform apply, ~15 min, prints outputs
# walkthrough with the client or interviewer
make demo-down    # terraform destroy, bill returns to zero on those lines
```

See `infra/terraform/`, `infra/k8s/`, and `docs/adr/0005-ovh-hosting.md`.

### Endpoints

| Method | Path | Role |
| --- | --- | --- |
| POST | `/assess` | Run an assessment, returns the `AssessmentReport`. |
| GET  | `/trace/{run_id}` | Persisted OTel trace. |
| GET  | `/health` | Liveness. |
| GET  | `/ready` | Readiness (run-store + DB). |
| GET  | `/metrics` | Prometheus 0.0.4 format. |
| GET  | `/drift` | Rolling distributions (domain, tier). |

### Environment variables

| Key | Default | Role |
| --- | --- | --- |
| `MISTRAL_API_KEY` (alias `BOUSSOLE_LLM_API_KEY`) | _empty_ | La Plateforme key. Empty => self-hosted vLLM expected. |
| `BOUSSOLE_LLM_URL` | `http://localhost:11434` | OpenAI-compatible endpoint. In prod: `https://api.mistral.ai` or the in-cluster vLLM service. |
| `BOUSSOLE_LLM_MODEL` | `mistral:7b-instruct` | Model identifier. In prod: `mistral-large-latest`. |
| `BOUSSOLE_DATABASE_URL` | `postgresql://boussole:boussole@localhost:5432/boussole` | Postgres DSN (run-store + pgvector). |
| `BOUSSOLE_USE_IN_MEMORY_STORE` | `false` | `true` for dev without Postgres. |
| `BOUSSOLE_FIXTURE_CORPUS` | `false` | `true` to load the fixture excerpt + FakeEmbedder (CI, smoke). |
| `BOUSSOLE_REGULATION` | `ai_act` | Active regulation plugin. |
| `BOUSSOLE_LOG_LEVEL` | `INFO` | structlog level. |

### Tests and evaluation

```bash
make test         # unit suite (no integration, no eval)
make smoke        # Phase 1 smoke
make eval-smoke   # 5 smoke cases (CI gate)
make eval         # gold eval against the frozen baseline (CLAUDE.md §12.1)
```

The gold set freezes the §12.1 gates: tier accuracy, citation precision and recall, groundedness rate, obligation recall, false-negative rate on high-risk, injection resistance. Regression blocks deploy.

### Known limitations (honest)

- The gold set is at 30 seeded cases, under extension. The §12.1 gates are not yet biting in CI.
- Per-node coloring of the retrieved points in the RAG cube is not implemented: all consulted chunks share one color.
- Passage text shown to the user stays in EN even when `language=FR`: the FR corpus is supported in the fetcher / parser but not indexed by default yet.
- The `draft_documentation` step is mostly template-driven today; LLM enrichment is gated and minimal.

### License

Proprietary. Contact Ceres Broker for licensing.
