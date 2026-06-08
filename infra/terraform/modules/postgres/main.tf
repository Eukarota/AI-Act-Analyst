# Managed Postgres on OVH.
#
# pgvector is the load-bearing extension for the corpus index. Verify
# availability for the chosen plan + region before applying. See
# TASKS_USER.md > "Verify pgvector availability on OVH Managed Postgres".

terraform {
  required_providers {
    ovh = {
      source = "ovh/ovh"
    }
    random = {
      source = "hashicorp/random"
    }
  }
}

resource "random_password" "app_password" {
  length      = 32
  special     = true
  min_lower   = 4
  min_upper   = 4
  min_numeric = 4
  min_special = 2
}

resource "ovh_cloud_project_database" "this" {
  service_name = var.service_name
  description  = var.name
  engine       = "postgresql"
  version      = "16"
  plan         = var.plan
  flavor       = var.flavor

  nodes {
    region = var.region
  }
}

resource "ovh_cloud_project_database_postgresql_user" "app" {
  service_name = var.service_name
  cluster_id   = ovh_cloud_project_database.this.id
  name         = "boussole_app"
  password     = random_password.app_password.result
}

resource "ovh_cloud_project_database_database" "main" {
  service_name = var.service_name
  cluster_id   = ovh_cloud_project_database.this.id
  name         = "boussole"
}

resource "ovh_cloud_project_database_ip_restriction" "operators" {
  for_each = toset(var.allowed_ingress_cidrs)

  service_name = var.service_name
  engine       = "postgresql"
  cluster_id   = ovh_cloud_project_database.this.id
  ip           = each.value
  description  = "operator-allowlist"
}
