# OVH API credentials are read from env (preferred) or terraform.tfvars.
# Required env vars:
#   OVH_ENDPOINT="ovh-eu"
#   OVH_APPLICATION_KEY=...
#   OVH_APPLICATION_SECRET=...
#   OVH_CONSUMER_KEY=...

provider "ovh" {
  endpoint = var.ovh_endpoint
}

# The kubernetes provider is configured from the Kapsule module's kubeconfig
# output via the root module's outputs file.
provider "kubernetes" {
  host                   = module.kapsule.kubeconfig_host
  client_certificate     = module.kapsule.kubeconfig_client_certificate
  client_key             = module.kapsule.kubeconfig_client_key
  cluster_ca_certificate = module.kapsule.kubeconfig_cluster_ca_certificate
}
