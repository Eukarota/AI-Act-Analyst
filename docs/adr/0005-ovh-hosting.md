# 0005: Production runs on OVHcloud

Date: 2026-06-09
Status: Accepted

## Context

Boussole's positioning is that the agent itself is sovereign: a French
regulated organisation can deploy it without exposing the system
description it submits (the IP being assessed) to a Cloud-Act-exposed
jurisdiction. That posture stops mattering the moment the hosting
provider can be compelled to disclose data by a US authority. See
CLAUDE.md section 5 and section 12.

The three credible EU sovereign clouds are OVHcloud, Scaleway, and
Outscale. Scaleway and OVHcloud are both EU-incorporated with French
data centres; Outscale carries SecNumCloud qualification (Outscale's
3DS OUTSCALE is qualified, several services).

## Decision

Production runs on OVHcloud Public Cloud:

- Managed Postgres for the run-manifest table, the trace table, and
  the pgvector corpus index.
- Managed Kubernetes (Kapsule) for the backend + frontend pods.
- Object Storage for build artefacts (corpus diffs, eval reports,
  baseline JSONs).
- A region in France (GRA, SBG, or RBX) for the data plane.

The vLLM target runs on a dedicated GPU instance in the same Public
Cloud project. For client-tightest deployments, the same architecture
can be replicated on Outscale to pick up SecNumCloud qualification
without changing the agent code.

The Terraform under `infra/terraform/` codifies the project so the
deployment is reproducible. The provider variables are env-only.

## Two deployment shapes for the LLM

The `LLMProvider` port (see ADR 0003) makes the choice between a
managed Mistral endpoint and a self-hosted vLLM a config switch, not
an architecture change. We document both shapes because each one is
correct for a different buyer:

**Shape A: La Plateforme (default for the public demo at
`aiact.ceres.broker`).**

- `BOUSSOLE_LLM_URL=https://api.mistral.ai/v1`
- `BOUSSOLE_LLM_MODEL=mistral-large-latest`
- Managed Mistral endpoint, Mistral-incorporated and EU-hosted, no
  Cloud Act exposure.
- Pay-per-token; portfolio-traffic cost is order-of-magnitude tens
  of euros per month rather than a constant GPU-instance floor.
- Trade-off: the system description being assessed leaves the OVH
  envelope and enters the Mistral envelope (still EU-sovereign,
  still off-training under commercial terms). For the public demo
  this is acceptable because the operator pastes their own
  throwaway descriptions.

**Shape B: Self-hosted vLLM on an OVH GPU instance (client missions
where the system description must not leave the buyer's envelope).**

- `BOUSSOLE_LLM_URL=http://vllm.boussole.svc.cluster.local:8000`
- vLLM serves an open-weight Mistral (e.g. Mistral 7B Instruct v0.3)
  on an L4 24 GB or comparable SKU in the same OVH project.
- Cost floor is the always-on GPU instance (order-of-magnitude
  several hundred euros per month).
- Every component, including the model, stays inside the OVH project
  the buyer can audit.

Same image, same code path, same eval. The buyer picks; the
architecture absorbs.

## Consequences

Positive:

- The sovereign argument the project is sold on is true at every layer.
  No part of an assessment leaves the OVHcloud EU region under normal
  operation.
- Managed Postgres + Kapsule cuts the operations burden so a freelance
  delivery can credibly hand off to a small operator team.
- Object Storage is S3-compatible; CI integrations work out of the box.

Negative:

- pgvector availability on OVH Managed Postgres must be confirmed for
  the chosen plan and region before applying. TASKS_USER.md tracks
  this as a pre-deploy check. If pgvector is unavailable on the chosen
  plan, the fallback is self-hosted Postgres on a VM in the same
  project (Terraform branch).
- A SecNumCloud-qualified deployment (Outscale path) is in scope for
  the most sensitive clients but is a separate Terraform plan.
- Self-hosted vLLM on a GPU instance is more operations work than a
  managed Mistral La Plateforme call. The architecture supports either;
  the default is vLLM because it keeps every component in the sovereign
  envelope.
