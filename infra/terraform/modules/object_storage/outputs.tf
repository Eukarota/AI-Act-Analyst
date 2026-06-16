output "endpoint" {
  description = "S3-compatible endpoint host. OVH uses the lowercase region group, e.g. s3.gra.io.cloud.ovh.net."
  value       = "s3.${lower(var.region)}.io.cloud.ovh.net"
}

output "container_name" {
  description = "Intended bucket name. Create out of band (OVH manager or aws-cli mb) using the credentials this module returns."
  value       = var.container
}

output "access_key_id" {
  value     = ovh_cloud_project_user_s3_credential.artifacts.access_key_id
  sensitive = true
}

output "secret_access_key" {
  value     = ovh_cloud_project_user_s3_credential.artifacts.secret_access_key
  sensitive = true
}
