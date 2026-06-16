# Object Storage credentials for build / eval artefacts (corpus diffs,
# baseline JSONs, gold reports). S3-compatible API.
#
# Note: the OVH Terraform provider (0.51) does NOT manage S3 buckets as
# resources. Container creation happens out of band, either via:
#   - The OVH manager UI (Public Cloud > Object Storage > Add a container)
#   - aws-cli against the S3 endpoint:
#       aws --endpoint-url=https://s3.${region}.io.cloud.ovh.net s3 mb s3://${container}
# What this module DOES manage:
#   - An OVH user with the objectstore_operator role
#   - S3 credentials (access key + secret) bound to that user, exposed
#     as sensitive outputs for injection into CI / cluster secrets
# Both are reproducible and rotatable.

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
