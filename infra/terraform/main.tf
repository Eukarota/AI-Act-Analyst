# Root module wiring the three sub-modules.
#
# Decision: a single Public Cloud project hosts the Managed Postgres, the
# Kapsule cluster, and the Object Storage container. Mixing tenants would
# break the sovereign argument: every resource here must live inside the
# same EU-resident project the client signs off on.

locals {
  name_prefix = "${var.project_name}-${var.environment}"

  # Managed Postgres and Object Storage accept the region group
  # (e.g. "GRA"), not the specific datacenter code (e.g. "GRA11").
  # Kapsule wants the datacenter code. Strip the trailing digits.
  region_group = regex("^[A-Z]+", var.region)
}

module "postgres" {
  source = "./modules/postgres"

  service_name          = var.service_name
  region                = local.region_group
  name                  = "${local.name_prefix}-pg"
  plan                  = var.postgres_plan
  flavor                = var.postgres_flavor
  engine_version        = var.postgres_version
  disk_size             = var.postgres_disk_size
  allowed_ingress_cidrs = var.allowed_ingress_cidrs
}

module "kapsule" {
  source = "./modules/kapsule"

  service_name        = var.service_name
  region              = var.region
  name                = "${local.name_prefix}-k8s"
  kapsule_version     = var.kapsule_version
  node_pool_flavor    = var.node_pool_flavor
  node_pool_min_nodes = var.node_pool_min_nodes
  node_pool_max_nodes = var.node_pool_max_nodes
}

module "object_storage" {
  source = "./modules/object_storage"

  service_name = var.service_name
  region       = local.region_group
  container    = "${local.name_prefix}-artifacts"
}

# Shape B (vLLM auto-hebergeable). Gated off by default so the public
# demo, which runs on Mistral La Plateforme, has zero GPU bill.
# Activate by setting `gpu_enabled = true` in tfvars + applying the
# `infra/k8s/components/vllm/` kustomize component on the cluster.
module "gpu_nodepool" {
  source = "./modules/gpu_nodepool"
  count  = var.gpu_enabled ? 1 : 0

  service_name  = var.service_name
  kube_id       = module.kapsule.kube_id
  name          = "${local.name_prefix}-vllm"
  flavor_name   = var.gpu_flavor
  min_nodes     = var.gpu_pool_min_nodes
  max_nodes     = var.gpu_pool_max_nodes
  desired_nodes = var.gpu_pool_min_nodes
}
