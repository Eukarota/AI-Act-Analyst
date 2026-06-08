# Managed Kubernetes (Kapsule) on OVH Public Cloud.

terraform {
  required_providers {
    ovh = {
      source = "ovh/ovh"
    }
  }
}

resource "ovh_cloud_project_kube" "this" {
  service_name = var.service_name
  name         = var.name
  region       = var.region
  version      = var.kapsule_version

  customization_apiserver {
    admissionplugins {
      enabled = ["NodeRestriction"]
    }
  }
}

resource "ovh_cloud_project_kube_nodepool" "default" {
  service_name  = var.service_name
  kube_id       = ovh_cloud_project_kube.this.id
  name          = "default"
  flavor_name   = var.node_pool_flavor
  min_nodes     = var.node_pool_min_nodes
  max_nodes     = var.node_pool_max_nodes
  desired_nodes = var.node_pool_min_nodes
  autoscale     = true
  anti_affinity = true
}
