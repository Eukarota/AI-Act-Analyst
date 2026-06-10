# Boussole - Tasks for You

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

- [ ] **[USER] Run the Phase 3 live determinism test against Ollama**

  ```bash
  BOUSSOLE_LLM_URL=http://localhost:11434 \
    BOUSSOLE_LLM_MODEL=mistral:7b-instruct \
    make integration-test
  ```

  _When_: after the two items above.
  _Why_: confirms the CLAUDE.md §12.3 contract ("extraction/classification
  LLM calls at temperature 0 ⇒ identical output") holds against your real
  local model. Without this, we're trusting the adapter on unit tests alone.

- [ ] **[USER] Bring up Postgres locally and re-run index_corpus.py against it**
  ```bash
  make up-db
  uv run python scripts/index_corpus.py --regulation ai_act --source local --target pgvector
  ```
  _When_: any time after Phase 2.
  _Why_: exercises the real `PgVectorStore`, including the HNSW and GIN
  indexes the production retrieval will use. The default test suite uses
  the in-memory store, which has slightly different scoring behaviour.

---

## 2. Mid-build decisions (review when prompted)

I'll seed defaults; you confirm or override.

- [ ] **[USER] Production model choice**
      Default I'll wire for OVH: `mistralai/Mistral-7B-Instruct-v0.3` on vLLM
      (open-weight, EU-aligned vendor, fits a single L4/L40S GPU).
      _Alternatives to consider_:
  - `mistralai/Mistral-Small-3` (24 B) - better quality, needs more VRAM
  - `mistralai/Mixtral-8x7B-Instruct-v0.1` - sparse MoE, strong but
    heavier
  - Mistral La Plateforme **managed** EU endpoint - fastest path to prod,
    no GPU to operate, still EU-resident, but a managed dependency
    _When_: before Phase 11 (deployment).
    _Why_: drives GPU sizing and the `BOUSSOLE_VLLM_MODEL` env in compose / Helm.

- [ ] **[USER] Accept the Mistral model licence on HuggingFace + create an HF token**
      `mistralai/Mistral-7B-Instruct-v0.3` is gated. Steps:
  1. Sign in at huggingface.co, accept the licence on the model page.
  2. Create a token (read-only is enough) at huggingface.co/settings/tokens.
  3. Add it to your local `.env` as `HUGGING_FACE_HUB_TOKEN=hf_...` and to
     OVH secrets the same way at deploy time.
     _When_: only when you decide to run vLLM (Phase 3 live test OR Phase 11
     deploy). You can skip entirely if you stay on Ollama locally + a managed
     API in prod.

- [ ] **[USER] Review the Phase 4 rules layer when it lands**
      _Why_: I will commit a deterministic AI-Act classification engine (Art. 5,
      Annex I, Annex III, Art. 50, Ch. V/GPAI). I'm an engineer, not a lawyer.
      Skim the rule modules under `regulations/ai_act/rules/` and flag anything
      that misreads the regulation - this is the load-bearing correctness piece.

- [ ] **[USER] Review the eval gold set (Phase 9 has landed)**
      30 cases now live at `eval/gold_set.jsonl`, every row marked `draft: true`,
      stratified across all 7 tiers and 15 domains, plus a 3-case hard slice
      (Annex III carve-out candidate, system built on GPAI, dual-use biometric)
      and a 2-case adversarial slice (prompt injection in the description).
      _Why_: I'm an engineer, not a lawyer. Skim the rows, flip `draft: false`
      on the ones you confirm, edit the labels that miss, and add more until
      you cross the §12.1 threshold of ≥ 60. The frozen baseline at
      `eval/baselines/<corpus_version>.json` rebases whenever you re-freeze
      (`uv run python eval/run_eval.py --regulation ai_act --gold --freeze-baseline`).

- [ ] **[USER] Build the LLM-as-judge calibration set**
      `eval/judge.py` runs an LLM judge on every drafted document but reports
      `calibrated_kappa: null` until a human-labelled calibration set exists.
      _How_: create `eval/judge_calibration.jsonl` with ≥ 20 rows of shape
      `{"doc_kind": "...", "criterion": "...", "judge_score": 1-4, "human_score": 1-4}`,
      scoring the same drafted documents the judge sees. Cohen's κ reports
      automatically; if κ < 0.6 the rubric in `eval/judge.py` needs recalibration
      before the judge can be cited publicly.

- [ ] **[USER] French copy review for the frontend**
      _When_: Phase 8.
      _Why_: the UI primary language is FR. I'll draft, but final brand voice
      and the "pre-assessment, not legal advice" framing should be your call.

---

## 3. Before deployment (Phase 11)

Everything below is OVH provisioning and CI plumbing. None of it blocks
earlier phases.

### 3.1 OVH account and project

- [ ] **[USER] Create / verify OVH Public Cloud project**
      _Notes_: tier matters less than the available **regions**. Pick a French
      region (GRA / SBG / RBX / WAW are EU-resident; GRA is generally the
      default for French sovereign workloads).

- [ ] **[USER] Generate OVH API credentials**
      application key + application secret + consumer key, scoped to the new
      project. Store in a password manager; I'll consume them through Terraform
      variables - never inline them in code.
      _Notes_: needed for Phase 11 `terraform apply`.

### 3.2 Managed Postgres + pgvector

- [ ] **[USER] Verify pgvector availability on OVH Managed Postgres**
      _Notes_: OVH's Managed Postgres exposes a curated list of extensions and
      `vector` is on it as of 2026. Verify before relying on it; the fallback
      is to run Postgres ourselves on a VM (slightly more ops, full extension
      control). If pgvector isn't available on the tier you picked, ping me
      and I'll switch the Terraform module to a self-hosted variant.

- [ ] **[USER] Provision Managed Postgres (or approve self-hosted)**
      _Notes_: I'll write the Terraform; you approve the apply.

### 3.3 LLM hosting (decision LOCKED 2026-06-10)

The two deployment shapes are codified in ADR 0005 and switchable by env
var via the `LLMProvider` port. No code change to switch.

**Shape A (LOCKED for the public demo `aiact.ceres.broker`): Mistral La
Plateforme.** `BOUSSOLE_LLM_URL=https://api.mistral.ai/v1`, model
`mistral-large-latest`, key in `MISTRAL_API_KEY`. EU-resident, no Cloud
Act exposure, pay-per-token. Expected cost at portfolio traffic: order
of magnitude tens of euros per month.

- [x] **[USER] Mistral La Plateforme key created and added to `.env`** (done
      2026-06-10).
- [ ] **[USER] Same key added to the OVH cluster secret at deploy time**
      via `kubectl -n boussole create secret generic boussole-backend-secrets
      --from-literal=MISTRAL_API_KEY=...` (see overlay comments in
      `infra/k8s/overlays/prod/kustomization.yaml`).

**Shape B (gated off, available for client missions): self-hosted vLLM
on an OVH GPU node pool.** Activation is documented in
`infra/k8s/components/vllm/README.md`. Steps when a paying mission
requires it:

- [ ] **[USER] Set `gpu_enabled = true` in `infra/terraform/environments/prod/main.tfvars`** and re-apply Terraform. Provisions the GPU node pool with `workload=vllm` taint. Default flavor `t1-le-7` (L4 24 GB, roughly €0.75/hr).
- [ ] **[USER] Accept the Mistral 7B Instruct licence on HuggingFace** and create a read-only token. Store in cluster as `kubectl -n boussole create secret generic vllm-secrets --from-literal=HF_TOKEN=...`.
- [ ] **[USER] Install the NVIDIA device plugin DaemonSet** so the GPU shows up as a schedulable resource (`kubectl apply -f` the upstream manifest).
- [ ] **[USER] Include the vLLM component in the overlay** (`components: [../../components/vllm]`) and update `boussole-backend-secrets` to point `BOUSSOLE_LLM_URL` at `http://vllm.boussole.svc.cluster.local:8000`.

### 3.4 Kubernetes / orchestration

- [ ] **[USER] Provision OVH Managed Kubernetes (Kapsule)**
      _Notes_: Terraform module is in place
      (`infra/terraform/modules/kapsule/`). Defaults to a 2-4 node pool of
      `b3-8` instances. A GPU node pool is wired but gated off
      (`gpu_enabled = false`); flip to `true` only when Shape B is active.

- [ ] **[USER] Install the nginx ingress controller and cert-manager**
      _Notes_: needed before the prod overlay's Ingress resolves. Standard
      Helm installs (commands in `infra/k8s/components/vllm/README.md`
      activation checklist; same idea applies to the base overlay).

- [ ] **[USER] Configure OVH Object Storage**
      For raw corpus snapshots and eval report archives.

### 3.5 GitLab CI

- [ ] **[USER] Create GitLab project (self-hosted or gitlab.com)**
      _Notes_: the `.gitlab-ci.yml` I shipped expects a Docker executor with
      Python 3.11. gitlab.com's shared runners work for everything except the
      integration tests (no Docker-in-Docker needed for unit + grounding gates).

- [ ] **[USER] Set GitLab CI variables**
      All masked, all scoped to protected branches (`main`):
  - `OVH_APPLICATION_KEY`, `OVH_APPLICATION_SECRET`, `OVH_CONSUMER_KEY` (Terraform)
  - `OVH_PROJECT_ID` (the Public Cloud project UUID, alias `service_name`)
  - `KUBE_CONFIG` (base64 of the kubeconfig output by `terraform output -raw kapsule_kubeconfig`)
  - `REGISTRY_USER`, `REGISTRY_PASSWORD` (a GitLab deploy token works)
  - `MISTRAL_API_KEY` (Shape A; the active path)
  - `HF_TOKEN` (only when activating Shape B)

### 3.6 Domain and DNS (decision LOCKED 2026-06-10)

Public demo subdomain: **`aiact.ceres.broker`**. Single host, with the
prod Ingress doing path-based routing (`/api/*` to backend, everything
else to frontend).

- [ ] **[USER] Add A record `aiact.ceres.broker` pointing at the cluster's
      LoadBalancer IP** (printed by
      `kubectl -n ingress-nginx get svc ingress-nginx-controller`).
      _Notes_: DNS propagation is usually the longest step; start it early.
      cert-manager's ACME challenge cannot resolve until the record is
      live; use the Let's Encrypt staging issuer first to avoid the
      rate-limit lock-out, then swap to prod.

---

## 4. Strategic / business-arc decisions (not blocking the build)

These exist only so they don't get forgotten. They're for the months after
Phase 11 ships.

- [ ] **[USER] Decide whether to pursue SecNumCloud-qualified hosting**
      _Notes_: not a personal cert. It's a provider qualification (Outscale is
      the relevant one). Only relevant if you start landing public-sector / HDS
      workloads. CLAUDE.md says "demonstrate fluency via reference
      architectures, not a personal badge."

- [ ] **[USER] HDS (Hébergement de Données de Santé)**
      _Notes_: same shape. Provider qualification. Only triggered by a real
      health-sector mission.

- [ ] **[USER] ISO/IEC 42001 Lead Implementer (PECB)**
      _Notes_: Phase 2/3 of the business arc per CLAUDE.md, _after_ you have a
      delivery track record. Don't pursue before two or three regulated-sector
      missions are landed and demonstrable.

- [ ] **[USER] IAPP AIGP**
      _Notes_: same caveat. After the cabinet positioning is concrete.

---

## 5. Things I will do without you

So you know what's NOT on this list:

- All code, schema, tests, Terraform, Helm charts, CI pipeline.
- Drafting the starter eval gold set (you review and expand).
- Drafting the French + English copy (you review and approve).
- Writing `docs/reference_architecture.md` and ADRs.
- Writing the bilingual `README.md` at Phase 11.

If you see a task slipping toward you that you think I could handle, ask.
