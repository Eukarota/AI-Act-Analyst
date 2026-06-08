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
