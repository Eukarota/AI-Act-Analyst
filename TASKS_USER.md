# Boussole — Tasks for You

Everything in the codebase has been built by Claude. The items in this file
are the ones that need **your hands**: provisioning accounts, accepting
licences, installing tools on your machine, making policy decisions, and
reviewing artefacts before they ship.

Each item has:

- **When**: phase / urgency
- **Why**: what gets unblocked when you do it
- **Notes**: anything you should be aware of (Cloud Act exposure, costs,
  alternatives)

The icon `[USER]` is searchable so future-Claude can scan for items that
still need you.

---

## 1. Right now (optional, unblocks local end-to-end verification)

These let you actually exercise the Phase 2/3 work locally. The unit suite
runs without any of them; integration tests need at least Docker.

- [ ] **[USER] Install Docker Desktop** (Apple Silicon-compatible build)
  *When*: Phase 2 verification onward.
  *Why*: brings up Postgres+pgvector for the PgVectorStore integration test,
  and is the platform for Ollama-on-Docker if you go that route.
  *Notes*: free.

- [ ] **[USER] Install Ollama and pull a Mistral weight**
  ```bash
  brew install ollama
  ollama serve              # in a separate terminal
  ollama pull mistral:7b-instruct
  ```
  *When*: Phase 3 verification (live determinism test).
  *Why*: vLLM's Docker image is CUDA-only and won't run usefully on Apple
  Silicon. Ollama gives you the same OpenAI-compatible `/v1/chat/completions`
  endpoint that the production vLLM target will speak. The
  `SelfHostedVLLM` adapter doesn't care which one is on the other end.
  *Notes*: ~4 GB download. Pure-local; no Cloud Act exposure.

- [ ] **[USER] Run the Phase 3 live determinism test against Ollama**
  ```bash
  BOUSSOLE_LLM_URL=http://localhost:11434 \
    BOUSSOLE_LLM_MODEL=mistral:7b-instruct \
    make integration-test
  ```
  *When*: after the two items above.
  *Why*: confirms the CLAUDE.md §12.3 contract ("extraction/classification
  LLM calls at temperature 0 ⇒ identical output") holds against your real
  local model. Without this, we're trusting the adapter on unit tests alone.

- [ ] **[USER] Bring up Postgres locally and re-run index_corpus.py against it**
  ```bash
  make up-db
  uv run python scripts/index_corpus.py --regulation ai_act --source local --target pgvector
  ```
  *When*: any time after Phase 2.
  *Why*: exercises the real `PgVectorStore`, including the HNSW and GIN
  indexes the production retrieval will use. The default test suite uses
  the in-memory store, which has slightly different scoring behaviour.

---

## 2. Mid-build decisions (review when prompted)

I'll seed defaults; you confirm or override.

- [ ] **[USER] Production model choice**
  Default I'll wire for OVH: `mistralai/Mistral-7B-Instruct-v0.3` on vLLM
  (open-weight, EU-aligned vendor, fits a single L4/L40S GPU).
  *Alternatives to consider*:
    - `mistralai/Mistral-Small-3` (24 B) — better quality, needs more VRAM
    - `mistralai/Mixtral-8x7B-Instruct-v0.1` — sparse MoE, strong but
      heavier
    - Mistral La Plateforme **managed** EU endpoint — fastest path to prod,
      no GPU to operate, still EU-resident, but a managed dependency
  *When*: before Phase 11 (deployment).
  *Why*: drives GPU sizing and the `BOUSSOLE_VLLM_MODEL` env in compose / Helm.

- [ ] **[USER] Accept the Mistral model licence on HuggingFace + create an HF token**
  `mistralai/Mistral-7B-Instruct-v0.3` is gated. Steps:
    1. Sign in at huggingface.co, accept the licence on the model page.
    2. Create a token (read-only is enough) at huggingface.co/settings/tokens.
    3. Add it to your local `.env` as `HUGGING_FACE_HUB_TOKEN=hf_...` and to
       OVH secrets the same way at deploy time.
  *When*: only when you decide to run vLLM (Phase 3 live test OR Phase 11
  deploy). You can skip entirely if you stay on Ollama locally + a managed
  API in prod.

- [ ] **[USER] Review the Phase 4 rules layer when it lands**
  *Why*: I will commit a deterministic AI-Act classification engine (Art. 5,
  Annex I, Annex III, Art. 50, Ch. V/GPAI). I'm an engineer, not a lawyer.
  Skim the rule modules under `regulations/ai_act/rules/` and flag anything
  that misreads the regulation — this is the load-bearing correctness piece.

- [ ] **[USER] Review the eval gold set (Phase 9 has landed)**
  30 cases now live at `eval/gold_set.jsonl`, every row marked `draft: true`,
  stratified across all 7 tiers and 15 domains, plus a 3-case hard slice
  (Annex III carve-out candidate, system built on GPAI, dual-use biometric)
  and a 2-case adversarial slice (prompt injection in the description).
  *Why*: I'm an engineer, not a lawyer. Skim the rows, flip `draft: false`
  on the ones you confirm, edit the labels that miss, and add more until
  you cross the §12.1 threshold of ≥ 60. The frozen baseline at
  `eval/baselines/<corpus_version>.json` rebases whenever you re-freeze
  (`uv run python eval/run_eval.py --regulation ai_act --gold --freeze-baseline`).

- [ ] **[USER] Build the LLM-as-judge calibration set**
  `eval/judge.py` runs an LLM judge on every drafted document but reports
  `calibrated_kappa: null` until a human-labelled calibration set exists.
  *How*: create `eval/judge_calibration.jsonl` with ≥ 20 rows of shape
  `{"doc_kind": "...", "criterion": "...", "judge_score": 1-4, "human_score": 1-4}`,
  scoring the same drafted documents the judge sees. Cohen's κ reports
  automatically; if κ < 0.6 the rubric in `eval/judge.py` needs recalibration
  before the judge can be cited publicly.

- [ ] **[USER] French copy review for the frontend**
  *When*: Phase 8.
  *Why*: the UI primary language is FR. I'll draft, but final brand voice
  and the "pre-assessment, not legal advice" framing should be your call.

---

## 3. Before deployment (Phase 11)

Everything below is OVH provisioning and CI plumbing. None of it blocks
earlier phases.

### 3.1 OVH account and project

- [ ] **[USER] Create / verify OVH Public Cloud project**
  *Notes*: tier matters less than the available **regions**. Pick a French
  region (GRA / SBG / RBX / WAW are EU-resident; GRA is generally the
  default for French sovereign workloads).

- [ ] **[USER] Generate OVH API credentials**
  application key + application secret + consumer key, scoped to the new
  project. Store in a password manager; I'll consume them through Terraform
  variables — never inline them in code.
  *Notes*: needed for Phase 11 `terraform apply`.

### 3.2 Managed Postgres + pgvector

- [ ] **[USER] Verify pgvector availability on OVH Managed Postgres**
  *Notes*: OVH's Managed Postgres exposes a curated list of extensions and
  `vector` is on it as of 2026. Verify before relying on it; the fallback
  is to run Postgres ourselves on a VM (slightly more ops, full extension
  control). If pgvector isn't available on the tier you picked, ping me
  and I'll switch the Terraform module to a self-hosted variant.

- [ ] **[USER] Provision Managed Postgres (or approve self-hosted)**
  *Notes*: I'll write the Terraform; you approve the apply.

### 3.3 GPU instance for vLLM, OR managed Mistral endpoint

This is the decision point for sovereign LLM hosting. Pick one path.

- [ ] **[USER] Path A — Self-hosted vLLM on OVH GPU instance**
  Provision an OVH Public Cloud GPU flavour (e.g. `t2-le-90` with L40S or
  `t2-le-180` with H100). Install NVIDIA drivers + Docker + nvidia-runtime.
  The compose file I shipped runs unchanged. Persistent volume for the
  HuggingFace cache so the model doesn't redownload on restart.
  *Notes*: cheapest per-token, full sovereignty, you operate the box.
  Plan ~€1.50–€3.50/hr for the GPU depending on flavour.

- [ ] **[USER] Path B — Mistral La Plateforme EU endpoint**
  Faster, no GPU to operate, EU-resident, but a managed dependency. Get an
  API key at console.mistral.ai (sign in with a French address) and store
  as a deploy secret. I'll wire a `MistralEU` adapter under the same
  `LLMProvider` port — same code switches via env var.
  *Notes*: best fit if first paying mission has aggressive timelines.

- [ ] **[USER] Path C — Both**
  Build the GPU instance for the portfolio demo (sovereignty signal), use
  La Plateforme for paid missions that don't require self-hosted. Two
  adapters live behind the same Protocol; switching is a config change.

### 3.4 Kubernetes / orchestration

- [ ] **[USER] Provision OVH Managed Kubernetes (Kapsule)**
  *Notes*: I'll target Kapsule in the Terraform. Three nodes (small) are
  enough for the demo. Add a GPU node pool if you went with Path A above.

- [ ] **[USER] Configure OVH Object Storage**
  For raw corpus snapshots and eval report archives.

### 3.5 GitLab CI

- [ ] **[USER] Create GitLab project (self-hosted or gitlab.com)**
  *Notes*: the `.gitlab-ci.yml` I shipped expects a Docker executor with
  Python 3.11. gitlab.com's shared runners work for everything except the
  integration tests (no Docker-in-Docker needed for unit + grounding gates).

- [ ] **[USER] Set GitLab CI variables**
  Will be:
  - `OVH_TF_*` (Terraform creds)
  - `BOUSSOLE_DSN_PROD` (Managed Postgres DSN)
  - `HUGGING_FACE_HUB_TOKEN` (if Path A)
  - `MISTRAL_API_KEY` (if Path B)
  - `BOUSSOLE_LLM_URL` (vLLM service URL or La Plateforme URL)

### 3.6 Domain and DNS

- [ ] **[USER] Decide and register the demo domain**
  e.g. `boussole.ceres.broker` (subdomain of your existing domain) or a
  dedicated one. I'll wire it through OVH DNS in Terraform.

---

## 4. Strategic / business-arc decisions (not blocking the build)

These exist only so they don't get forgotten. They're for the months after
Phase 11 ships.

- [ ] **[USER] Decide whether to pursue SecNumCloud-qualified hosting**
  *Notes*: not a personal cert. It's a provider qualification (Outscale is
  the relevant one). Only relevant if you start landing public-sector / HDS
  workloads. CLAUDE.md says "demonstrate fluency via reference
  architectures, not a personal badge."

- [ ] **[USER] HDS (Hébergement de Données de Santé)**
  *Notes*: same shape. Provider qualification. Only triggered by a real
  health-sector mission.

- [ ] **[USER] ISO/IEC 42001 Lead Implementer (PECB)**
  *Notes*: Phase 2/3 of the business arc per CLAUDE.md, *after* you have a
  delivery track record. Don't pursue before two or three regulated-sector
  missions are landed and demonstrable.

- [ ] **[USER] IAPP AIGP**
  *Notes*: same caveat. After the cabinet positioning is concrete.

---

## 5. Things I will do without you

So you know what's NOT on this list:

- All code, schema, tests, Terraform, Helm charts, CI pipeline.
- Drafting the starter eval gold set (you review and expand).
- Drafting the French + English copy (you review and approve).
- Writing `docs/reference_architecture.md` and ADRs.
- Writing the bilingual `README.md` at Phase 11.

If you see a task slipping toward you that you think I could handle, ask.
