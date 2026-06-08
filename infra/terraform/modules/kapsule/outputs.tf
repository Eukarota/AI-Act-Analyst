output "kubeconfig" {
  description = "kubeconfig YAML for the cluster."
  value       = ovh_cloud_project_kube.this.kubeconfig
  sensitive   = true
}

output "kubeconfig_host" {
  value     = ovh_cloud_project_kube.this.kubeconfig_attributes[0].host
  sensitive = true
}

output "kubeconfig_client_certificate" {
  value     = ovh_cloud_project_kube.this.kubeconfig_attributes[0].client_certificate
  sensitive = true
}

output "kubeconfig_client_key" {
  value     = ovh_cloud_project_kube.this.kubeconfig_attributes[0].client_key
  sensitive = true
}

output "kubeconfig_cluster_ca_certificate" {
  value     = ovh_cloud_project_kube.this.kubeconfig_attributes[0].cluster_ca_certificate
  sensitive = true
}

output "kube_id" {
  value = ovh_cloud_project_kube.this.id
}
