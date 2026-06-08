# Root module wiring the three sub-modules.
#
# Decision: a single Public Cloud project hosts the Managed Postgres, the
# Kapsule cluster, and the Object Storage container. Mixing tenants would
# break the sovereign argument: every resource here must live inside the
# same EU-resident project the client signs off on.

locals {
  name_prefix = "${var.project_name}-${var.environment}"
}

module "postgres" {
  source = "./modules/postgres"

  service_name          = var.service_name
  region                = var.region
  name                  = "${local.name_prefix}-pg"
  plan                  = var.postgres_plan
  flavor                = var.postgres_flavor
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
  region       = var.region
  container    = "${local.name_prefix}-artifacts"
}
