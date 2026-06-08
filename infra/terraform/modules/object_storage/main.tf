# Object Storage container for build / eval artefacts (corpus diffs,
# baseline JSONs, gold reports). S3-compatible API.

terraform {
  required_providers {
    ovh = {
      source = "ovh/ovh"
    }
  }
}

resource "ovh_cloud_project_user" "artifacts" {
  service_name = var.service_name
  description  = "${var.container}-rw"
  role_name    = "objectstore_operator"
}

resource "ovh_cloud_project_user_s3_credential" "artifacts" {
  service_name = var.service_name
  user_id      = ovh_cloud_project_user.artifacts.id
}

resource "ovh_cloud_project_storage" "artifacts" {
  service_name = var.service_name
  region_name  = var.region
  name         = var.container
}
