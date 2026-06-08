output "postgres_dsn" {
  description = "DSN for the Managed Postgres instance. Inject as BOUSSOLE_DATABASE_URL."
  value       = module.postgres.dsn
  sensitive   = true
}

output "kapsule_kubeconfig" {
  description = "kubeconfig YAML for the Kapsule cluster."
  value       = module.kapsule.kubeconfig
  sensitive   = true
}

output "object_storage_endpoint" {
  description = "S3-compatible endpoint for the artifacts bucket."
  value       = module.object_storage.endpoint
}

output "object_storage_container" {
  description = "Container name for artefacts (eval reports, corpus diffs)."
  value       = module.object_storage.container_name
}
