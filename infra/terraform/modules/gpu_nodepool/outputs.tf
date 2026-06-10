output "pool_name" {
  description = "Name of the GPU node pool (use in nodeSelector / toleration values)."
  value       = ovh_cloud_project_kube_nodepool.vllm.name
}

output "taint_value" {
  description = "Taint value applied to the GPU nodes. The vLLM Deployment must tolerate this."
  value       = var.taint_value
}

output "flavor_name" {
  description = "Flavor of the GPU instances in the pool."
  value       = ovh_cloud_project_kube_nodepool.vllm.flavor_name
}
