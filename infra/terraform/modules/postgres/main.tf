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
  }
}

resource "ovh_cloud_project_database" "this" {
  service_name = var.service_name
  description  = var.name
  engine       = "postgresql"
  version      = var.engine_version
  plan         = var.plan
  flavor       = var.flavor
  disk_size    = var.disk_size

  nodes {
    region = var.region
  }

  # Inline IP allowlist. The standalone ovh_cloud_project_database_ip_restriction
  # resource is deprecated in provider 0.51+.
  dynamic "ip_restrictions" {
    for_each = toset(var.allowed_ingress_cidrs)
    content {
      ip          = ip_restrictions.value
      description = "operator-allowlist"
    }
  }
}

resource "ovh_cloud_project_database_postgresql_user" "app" {
  service_name = var.service_name
  cluster_id   = ovh_cloud_project_database.this.id
  name         = "boussole_app"
  # The provider generates and rotates the password; we read it from the
  # resource attribute below in outputs.tf.
}

resource "ovh_cloud_project_database_database" "main" {
  service_name = var.service_name
  cluster_id   = ovh_cloud_project_database.this.id
  engine       = "postgresql"
  name         = "boussole"
}
