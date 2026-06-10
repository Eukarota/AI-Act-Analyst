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

output "gpu_pool_name" {
  description = "Name of the GPU node pool when Shape B is active, else null. The vLLM Deployment's nodeSelector / toleration must match this."
  value       = var.gpu_enabled ? module.gpu_nodepool[0].pool_name : null
}

output "gpu_taint_value" {
  description = "Taint value the vLLM pods must tolerate when Shape B is active, else null."
  value       = var.gpu_enabled ? module.gpu_nodepool[0].taint_value : null
}
