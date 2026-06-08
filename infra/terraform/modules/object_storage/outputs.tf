output "endpoint" {
  description = "S3-compatible endpoint host."
  value       = "s3.${var.region}.io.cloud.ovh.net"
}

output "container_name" {
  value = ovh_cloud_project_storage.artifacts.name
}

output "access_key_id" {
  value     = ovh_cloud_project_user_s3_credential.artifacts.access_key_id
  sensitive = true
}

output "secret_access_key" {
  value     = ovh_cloud_project_user_s3_credential.artifacts.secret_access_key
  sensitive = true
}
