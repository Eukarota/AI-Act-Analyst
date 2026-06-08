# Boussole

Pre-evaluation agent for the EU AI Act, sovereign by construction.

[Francais](#francais-version-de-reference) | [English](#english)

---

## Francais (version de reference)

Boussole prend en entree la description d'un systeme d'IA et produit une
pre-evaluation technique structuree : classification de risque au sens
du Reglement (UE) 2024/1689, obligations applicables, analyse d'ecart
par rapport aux controles declares, brouillon de documentation. Chaque
affirmation juridique pointe vers le passage exact du texte consolide.

Boussole n'est pas un avis juridique. Le rapport est cadre comme une
pre-evaluation technique destinee a appuyer une revue qualifiee.

### Pourquoi

- **Souverain par construction.** Modele, embeddings, base vectorielle,
  inference, stockage : tout reste dans l'enveloppe OVHcloud EU. Aucune
  donnee client ne transite par une juridiction Cloud Act.
- **Auditable.** Le panneau de trace (UI) expose chaque nœud du graphe,
  chaque appel d'outil, chaque passage recupere, chaque verification
  d'ancrage. La trace est le produit, pas une vue debug.
- **Determinisme la ou il faut.** La couche de regles (Art. 5,
  Annexes I et III, Art. 50, Chapitre V) est une fonction pure
  testee en tableau. Le LLM extrait, les regles statuent.

Voir `docs/reference_architecture.md` pour le detail et `CLAUDE.md`
pour la specification operationnelle.

### Pile technique

Python 3.11+, FastAPI, LangGraph, MCP. Next.js 15, Tailwind 4, Inter
Tight. Postgres + pgvector. Mistral 7B Instruct via vLLM (ou Ollama
en developpement local). OpenTelemetry + Prometheus. Terraform pour
OVHcloud.

### Demarrage rapide

```bash
# Installer uv si necessaire
curl -LsSf https://astral.sh/uv/install.sh | sh

# Dependances Python
make install

# Lancer le smoke test (sans services externes)
make smoke

# Lancer la suite complete
make test

# Lancer l'eval (sortie : eval/reports/gold_report.md)
make eval

# Demarrer le backend en local (run-store en memoire, pas de Postgres)
make dev-backend-fake

# Demarrer le frontend
make dev-frontend
```

Le backend ecoute sur `http://localhost:8000`, le frontend sur
`http://localhost:3000`. Les rewrites Next.js proxient `/api/*` vers le
backend.

### Endpoints

| Methode | Chemin | Description |
| --- | --- | --- |
| POST | `/assess` | Lance une evaluation, renvoie le `AssessmentReport`. |
| GET  | `/trace/{run_id}` | Retourne la trace OTel persistee. |
| GET  | `/health` | Liveness. |
| GET  | `/ready` | Readiness (verifie le run-store). |
| GET  | `/metrics` | Format texte Prometheus 0.0.4. |
| GET  | `/drift` | Distributions roulantes domaine + tier. |

### Variables d'environnement

| Cle | Defaut | Role |
| --- | --- | --- |
| `BOUSSOLE_LLM_URL` | `http://localhost:11434` | URL de l'API OpenAI-compatible (vLLM ou Ollama). |
| `BOUSSOLE_LLM_MODEL` | `mistral:7b-instruct` | Identifiant du modele servi. |
| `BOUSSOLE_LLM_API_KEY` | _vide_ | Cle si le serveur en exige une. |
| `BOUSSOLE_DATABASE_URL` | `postgresql://boussole:boussole@localhost:5432/boussole` | DSN Postgres. |
| `BOUSSOLE_USE_IN_MEMORY_STORE` | `false` | `true` pour le dev sans Postgres. |
| `BOUSSOLE_LOG_LEVEL` | `INFO` | Niveau de log structlog. |

### Deploiement OVHcloud

`infra/terraform/` provisionne le projet Public Cloud, l'instance
Managed Postgres (pgvector requis), Kapsule (Kubernetes gere) et
Object Storage pour les artefacts.

```bash
cd infra/terraform
cp environments/prod/main.tfvars.example environments/prod/main.tfvars
# Remplir service_name (ID du projet OVH) et backend_image / frontend_image
terraform init
terraform apply -var-file=environments/prod/main.tfvars
```

Le deploiement Kubernetes utilise `kustomize` :

```bash
cd infra/k8s/overlays/prod
kustomize edit set image \
  boussole-backend=$REGISTRY/backend:$TAG \
  boussole-frontend=$REGISTRY/frontend:$TAG
kubectl apply -k .
```

Le runbook de rollback est `docs/runbook_rollback.md`.

### Mesure

Le jeu d'evaluation gele les gates CLAUDE.md section 12.1. La
regression bloque le deploy. Voir `eval/gold_set.jsonl` (cas) et
`eval/baselines/<corpus_version>.json` (baseline).

---

## English

Boussole takes a description of an AI system as input and produces a
structured technical pre-assessment: risk tier under Regulation (EU)
2024/1689, applicable obligations, gap analysis against declared
controls, drafted documentation. Every legal claim points at the exact
passage of the consolidated text.

Boussole is not legal advice. The report is framed as a technical
pre-assessment intended to support qualified legal review.

### Why

- **Sovereign by construction.** Model, embeddings, vector store,
  inference, persistence: all stays inside the OVHcloud EU envelope.
  No client data transits a Cloud-Act-exposed jurisdiction.
- **Auditable.** The glass-box trace panel exposes every graph node,
  every tool call, every retrieved passage, every grounding check. The
  trace IS the product, not a debug view.
- **Determinism where it counts.** The rules layer (Art. 5, Annex I and
  III, Art. 50, Chapter V) is a pure function tested in a table-driven
  suite. The LLM extracts attributes; the rules decide.

See `docs/reference_architecture.md` for the detail and `CLAUDE.md`
for the operational specification.

### Stack

Python 3.11+, FastAPI, LangGraph, MCP. Next.js 15, Tailwind 4, Inter
Tight. Postgres + pgvector. Mistral 7B Instruct via vLLM (or Ollama
for local dev). OpenTelemetry + Prometheus. Terraform for OVHcloud.

### Quickstart

```bash
# Install uv if needed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Python dependencies
make install

# Smoke test (no external services)
make smoke

# Full test suite
make test

# Gold eval (writes eval/reports/gold_report.md)
make eval

# Run backend locally with the in-memory run-store
make dev-backend-fake

# Run the frontend
make dev-frontend
```

The backend listens on `http://localhost:8000`; the frontend on
`http://localhost:3000` and proxies `/api/*` to the backend.

### Deployment

Terraform under `infra/terraform/` provisions the OVHcloud Public
Cloud project (Managed Postgres with pgvector, Kapsule, Object
Storage). The Kubernetes manifests under `infra/k8s/` are kustomize
based.

The rollback runbook lives at `docs/runbook_rollback.md`.

### Evaluation

The gold set freezes the CLAUDE.md section 12.1 gates. Regressions
block deploy. See `eval/gold_set.jsonl` for cases and
`eval/baselines/<corpus_version>.json` for the frozen numbers.

---

## License

Proprietary. Contact Ceres Broker for licensing.
