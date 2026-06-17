<div align="center">

<img src="./docs/images/logo.png" alt="AI Act Analyst logo" width="220" height="220"/>

# `ai-act-analyst`

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![EU AI Act](https://img.shields.io/badge/Regulation-(EU)_2024%2F1689-6366f1)](https://eur-lex.europa.eu/eli/reg/2024/1689/oj)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Next.js 15](https://img.shields.io/badge/Next.js-15-000000?logo=next.js&logoColor=white)](https://nextjs.org/)
[![Mistral](https://img.shields.io/badge/Mistral-La_Plateforme-FA520F)](https://mistral.ai/)
[![OVHcloud](https://img.shields.io/badge/Hosting-OVHcloud-123F6D)](https://www.ovhcloud.com/)
[![by Ceres Broker](https://img.shields.io/badge/by-Ceres_Broker-7c3aed)](https://ceres.broker)

<h4>A sovereign agent that pre-assesses an AI system against the EU AI Act, grounded in the consolidated text, line by line.</h4>

<p>
  <a href="#français"><strong>Français</strong></a> ·
  <a href="#english"><strong>English</strong></a>
</p>

<img src="./docs/images/screenshot.png" alt="Screenshot of AI Act Analyst" />

</div>

<p align="center">
  <a href="#what-and-why">What and why</a> ·
  <a href="#features">Features</a> ·
  <a href="#architecture">Architecture</a> ·
  <a href="#installation">Installation</a> ·
  <a href="#deployment">Deployment</a> ·
  <a href="#api">API</a> ·
  <a href="#evaluation">Evaluation</a> ·
  <a href="#known-limitations">Known limitations</a> ·
  <a href="#about-ceres-broker">About Ceres Broker</a> ·
  <a href="#license">License</a>
</p>

---

## What and why

The EU AI Act (Regulation (EU) 2024/1689) starts to bite from **2 August 2026**, with fines up to **€35M**. Most teams shipping AI today do not know which tier they fall under, which articles apply, or what documentation they owe. The standard advice "ask a lawyer" is correct but does not scale.

`ai-act-analyst` takes the description of an AI system and returns a structured, source-cited **pre-assessment**: risk tier under the Act, applicable obligations, gap analysis against declared controls, drafted documentation skeletons (Annex IV, Article 50). **Every legal claim points to a specific passage of the consolidated text** (article, paragraph, annex, or recital).

It is explicitly not legal advice. The framing is "technical pre-assessment to support qualified legal review." That refusal to render a verdict is the project's first credibility move.

Three design constraints make this different from a chatbot:

1. **Deterministic core.** Risk classification is a pure function tested in a table-driven suite. The LLM extracts attributes at temperature 0; the rules decide.
2. **No fabricated citations.** A single grounding function (`assert_grounded`) runs both in eval and on every production response. An ungrounded claim blocks the response (HTTP 502).
3. **Sovereign by construction.** Model, embeddings, vector store, persistence: every component stays inside the OVHcloud EU envelope. No Cloud Act exposure on the inference, embedding, or storage path.

## Features

<details open>
<summary><strong>Agent and orchestration</strong></summary>

- Pydantic-typed state graph on LangGraph: `intake → clarify (bounded ≤ 3) → classify → retrieve_context → enumerate_obligations → gap_analysis → draft_docs → assemble_report`.
- Five MCP servers exposing each capability: `retrieve_law`, `classify_risk`, `lookup_obligations`, `analyze_gaps`, `draft_documentation`.
- Interactive clarification loop with answer-back UI.
- Bounded budgets per node (timeout) and per run (token, tool-call). No unbounded loops.

</details>

<details open>
<summary><strong>Deterministic rules layer</strong></summary>

- Classification is a pure function `classify(AttributeSet) -> ClassificationResult`. The LLM extracts attributes (temperature 0); the rules decide.
- Deterministic ordering: Article 5 (prohibitions) → Annex I (safety components of regulated products) → Annex III (standalone high-risk) → Article 50 (transparency) → minimal. Parallel track for GPAI models (Chapter V, systemic threshold per Article 55).
- Each rule emits the identifier that fired and supporting article refs. Same `AttributeSet` + same `rules_version` => identical result.
- Table-driven tests on every branch, including boundary cases (Annex III boundaries, GPAI vs system-built-on-GPAI).

</details>

<details open>
<summary><strong>Retrieval and grounding</strong></summary>

- Corpus: consolidated text of Regulation (EU) 2024/1689 pulled from the EU Publications Office cellar, yielding ~880 chunks (180 recitals, ~560 article paragraphs, ~140 annex points). Versioned, immutable, hashed.
- **Hybrid retrieval**: dense via `multilingual-e5-large` (1024-d) over `pgvector`, sparse via PostgreSQL `tsvector`, fused with Reciprocal Rank Fusion, re-ranked by `bge-reranker-v2`. Pure-dense fails on legal text.
- Per-node scoped retrieval: `classify` queries Art. 5 + Annexes I/III; `enumerate_obligations` queries Art. 8 to 15 / 26 / 50 / 53. No single global pass.
- **Grounding contract** (`assert_grounded`): any legal claim not backed by a passage retrieved in the current turn is rejected by construction. One function, two callers (eval and prod).

</details>

<details>
<summary><strong>Glass-box trace</strong></summary>

- One OpenTelemetry span per graph node and per tool call, recording input hash, latency, tokens, `model_id`.
- The UI trace panel renders the exact same event stream. No "demo" logging path.
- 3D embedding cube (Three.js + PCA): interactive visualization of the corpus with the retrieved chunks highlighted in real time. Fullscreen mode.
- Run manifest persisted per assessment: `{run_id, corpus_version, model_id, embedding_model, prompt_set_version, rules_version, timestamp}`.

</details>

<details>
<summary><strong>LLMOps and reproducibility</strong></summary>

- Prompt registry (`prompts/registry.yaml`): name → version + sha. No prompts inlined anywhere in the code.
- Idempotent corpus pipeline: `scripts/index_corpus.py` produces a diff report and a new `corpus_version` on every re-index.
- Retrieval cache keyed by `corpus_version`, semantic cache for repeated sub-queries.
- Prometheus telemetry on `/metrics`: p95 latency, tokens in/out, cache hit rate, groundedness rate. Domain and tier drift on `/drift`.
- Online grounding check: identical to the eval check. Violation blocks the response (HTTP 502) and raises an alert.

</details>

<details>
<summary><strong>Frontend (Next.js)</strong></summary>

- Conversational intake with ready-to-load examples (recruitment, social scoring, translation, chatbot).
- Structured report: risk tier, collapsible run manifest, citation-linked obligations, gap analysis against declared controls, collapsible document drafts.
- Real-time glass-box trace rendered in the right column.
- Fully bilingual FR / EN: prompts, classification rationale, obligation summaries, gap notes, Annex IV skeleton. Switch persisted in localStorage.

</details>

<details>
<summary><strong>Sovereignty</strong></summary>

- Model: Mistral La Plateforme (EU endpoint, French operator) or self-hosted vLLM on OVH GPU.
- Embeddings: `multilingual-e5-large` loaded locally via `sentence-transformers`.
- Vector store: `pgvector` on OVHcloud Managed Postgres.
- No Cloud Act dependency in the inference, embedding, or storage path. Documented in `docs/reference_architecture.md`.

</details>

<details>
<summary><strong>Adaptability (regulation-as-plugin)</strong></summary>

- The agent core is regulation-agnostic. Any regulation (AI Act today; GDPR, DORA, NIS2 tomorrow) implements the `Regulation { corpus_loader, chunker_config, classifier_rules, obligations_map, document_templates, defined_terms, timeline }` Protocol.
- Conformance suite: a fixture regulation runs end-to-end. Any new regulation must pass it.
- No regulatory date hardcoded anywhere. Everything lives under `regulations/<name>/config/timeline.yaml`.

</details>

## Architecture

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

1. **The LLM never decides the risk tier.** It extracts structured attributes at temperature 0. `classify` is table-tested, reproducible, auditable.
2. **No ungrounded legal claim escapes.** Grounding is one function called by both eval and prod runner. No drift possible between "what passes in CI" and "what passes online."
3. **Every assessment is reproducible.** The manifest carries `(corpus_version, model_id, embedding_model, prompt_set_version, rules_version)`. Replaying an assessment six months later is mechanical.

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

## Installation

Prerequisites: Docker, Python 3.11+, Node 20+, [uv](https://docs.astral.sh/uv/), a Mistral La Plateforme key.

```bash
# 1. Install Python dependencies
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
```

The first index pulls the OJ EU text from the Publications Office cellar (~1 MB), produces 881 chunks, and embeds them locally with `multilingual-e5-large` (~1.1 GB of weights). Expect 5 to 10 minutes on CPU for the first run. The 3D corpus cube is projected immediately after.

Tear everything down with `make demo-local-down`.

## Deployment

The full sovereign stack (Public Cloud project + Managed Postgres + Kapsule + Object Storage) provisions and destroys via Terraform:

```bash
make demo-up      # terraform apply, ~15 min, prints outputs
# walkthrough with the client or interviewer
make demo-down    # terraform destroy, bill returns to zero on those lines
```

Provisioning is intentionally short-lived. Between sessions, cost-to-run is zero. See `infra/terraform/`, `infra/k8s/`, and `docs/adr/0005-ovh-hosting.md`.

## API

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

## Evaluation

```bash
make test         # unit suite (no integration, no eval)
make smoke        # Phase 1 smoke
make eval-smoke   # 5 smoke cases (CI gate)
make eval         # gold eval against the frozen baseline
```

The gold set freezes the gates: tier accuracy, citation precision and recall, groundedness rate, obligation recall, false-negative rate on high-risk, injection resistance. Regression blocks deploy.

## Known limitations

- The gold set is at 30 seeded cases, under extension. The §12.1 gates are not yet biting in CI.
- Per-node coloring of the retrieved points in the RAG cube is not implemented: all consulted chunks share one color.
- Passage text shown to the user stays in EN even when `language=FR`: the FR corpus is supported in the fetcher / parser but not indexed by default yet.
- The `draft_documentation` step is mostly template-driven today; LLM enrichment is gated and minimal.

## Documentation

- `docs/reference_architecture.md` : the portfolio case study, sovereignty reasoning, architecture diagram, stack, outcome.
- `docs/adr/` : architecture decision records.
- `CLAUDE.md` : the operational specification (single source of truth for contributors and agents).

---

## Français

`ai-act-analyst` prend en entrée la description d'un système d'IA et produit un rapport structuré : niveau de risque au sens du Règlement (UE) 2024/1689, obligations applicables, analyse d'écart contre les contrôles déclarés, squelettes de documentation (annexe IV, articles 50). **Chaque affirmation juridique est ancrée à un passage précis du texte consolidé** (article, paragraphe, annexe, considérant).

Ce n'est pas un avis juridique. Le rapport est cadré comme une pré-évaluation technique destinée à appuyer une revue qualifiée. C'est volontaire : le seul agent crédible auprès d'un service conformité est celui qui *refuse* de produire un verdict.

### Pourquoi

L'AI Act entre en application progressive jusqu'au **2 août 2026**, avec des amendes jusqu'à **35 M€**. La plupart des équipes qui déploient des systèmes d'IA aujourd'hui ne savent pas dans quel tier elles tombent, quels articles s'appliquent, ni quelle documentation elles doivent produire. « Demande à un avocat » est juste mais ne passe pas à l'échelle.

Trois contraintes de conception qui distinguent ce projet d'un chatbot :

1. **Cœur déterministe.** La classification est une fonction pure testée en tableau. Le LLM extrait les attributs à température 0, les règles statuent.
2. **Aucune citation fabriquée.** Une fonction unique d'ancrage (`assert_grounded`) tourne en eval ET sur chaque réponse de production. Une affirmation non ancrée bloque la réponse (HTTP 502).
3. **Souveraineté par construction.** Modèle, embeddings, base vectorielle, persistance : tout reste dans l'enveloppe OVHcloud UE. Aucune dépendance Cloud Act.

### Démarrer en local

Prérequis : Docker, Python 3.11+, Node 20+, [uv](https://docs.astral.sh/uv/), une clé Mistral La Plateforme.

```bash
make install                      # dépendances Python
cp .env.example .env              # MISTRAL_API_KEY au minimum
make demo-local                   # Postgres + indexation du corpus + projection 3D

# Dans deux terminaux séparés
make dev-backend                  # FastAPI sur :8000
make dev-frontend                 # Next.js sur :3000

# Ouvrir http://localhost:3000
make demo-local-down              # tout démonter
```

La première indexation télécharge le texte officiel du JOUE depuis le cellar du Publications Office (~1 Mo), génère 881 chunks et les embed localement avec `multilingual-e5-large` (~1.1 Go de poids chargés). Compter 5 à 10 minutes en CPU au premier lancement.

### Provisionnement OVHcloud à la demande

```bash
make demo-up      # terraform apply, ~15 min, affiche les outputs
make demo-down    # terraform destroy, retour à zéro
```

Voir `infra/terraform/`, `infra/k8s/`, `docs/adr/0005-ovh-hosting.md`.

### Limites connues

- Le gold set est à 30 cas seedés, sous extension. Les gates §12.1 ne mordent pas encore en CI.
- Le coloriage par-nœud des points retrouvés dans le cube RAG n'est pas implémenté.
- Le texte des passages affiché reste en EN même quand `language=FR` : le corpus FR est supporté côté fetcher / parser mais pas encore indexé par défaut.
- L'étape `draft_documentation` est principalement gabarit ; l'enrichissement LLM y est minimal.

---

## About Ceres Broker

`ai-act-analyst` is built and maintained by **[Mathias Dupey](https://www.malt.fr/profile/mathiasdupey)**, founder of **[Ceres Broker](https://ceres.broker)**, a Paris-based engineering studio specializing in **sovereign generative AI** for French and EU regulated organisations (public sector, healthcare, finance, industry).

If you need help deploying this in production, running an AI Act readiness assessment on a real system, or building an equivalent on top of another regulation (GDPR, DORA, NIS2), find me on:

<p>
  <a href="https://ceres.broker"><img alt="Website" src="https://img.shields.io/badge/Website-ceres.broker-7c3aed?style=for-the-badge"></a>
  <a href="https://www.malt.fr/profile/mathiasdupey"><img alt="Malt" src="https://img.shields.io/badge/Malt-Hire_me-FC5656?style=for-the-badge&logo=malt"></a>
  <a href="mailto:contact@ceres.broker"><img alt="Email" src="https://img.shields.io/badge/Email-contact%40ceres.broker-0ea5e9?style=for-the-badge&logo=protonmail&logoColor=white"></a>
  <a href="https://github.com/Eukarota"><img alt="GitHub" src="https://img.shields.io/badge/GitHub-Eukarota-181717?style=for-the-badge&logo=github"></a>
</p>

## License

`ai-act-analyst` is released under the [MIT License](./LICENSE).

The consolidated text of Regulation (EU) 2024/1689 is © European Union, reused under the [Commission Reuse Decision (2011/833/EU)](https://eur-lex.europa.eu/eli/dec/2011/833/oj). The regulation itself is law, not licensed software, and `ai-act-analyst`'s reuse is limited to retrieval and citation.

Trademarks belong to their respective owners.
