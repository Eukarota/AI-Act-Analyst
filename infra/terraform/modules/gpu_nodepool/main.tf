# GPU node pool for Shape B (self-hosted vLLM).
#
# This module is gated by `count = var.gpu_enabled ? 1 : 0` at the root.
# When disabled, nothing is provisioned and the bill is unaffected.
#
# When enabled, an OVH GPU node pool is attached to the existing Kapsule
# cluster. The pool carries a taint so only vLLM pods (which tolerate it)
# can schedule there; the backend and frontend stay on the default CPU
# pool. min_nodes defaults to 0 so the pool scales to zero when no vLLM
# pod is scheduled, but in production with a Deployment requesting GPU,
# the autoscaler will keep one node up.

terraform {
  required_providers {
    ovh = {
      source = "ovh/ovh"
    }
  }
}

resource "ovh_cloud_project_kube_nodepool" "vllm" {
  service_name  = var.service_name
  kube_id       = var.kube_id
  name          = var.name
  flavor_name   = var.flavor_name
  min_nodes     = var.min_nodes
  max_nodes     = var.max_nodes
  desired_nodes = var.desired_nodes
  autoscale     = true
  anti_affinity = false

  template {
    metadata {
      labels = {
        "workload" = "vllm"
      }
    }
    spec {
      taints = [
        {
          effect = "NoSchedule"
          key    = "workload"
          value  = var.taint_value
        }
      ]
      unschedulable = false
    }
  }
}
