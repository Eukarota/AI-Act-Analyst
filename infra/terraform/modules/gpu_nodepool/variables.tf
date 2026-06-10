variable "service_name" {
  description = "OVH Public Cloud project ID."
  type        = string
}

variable "kube_id" {
  description = "Kapsule cluster ID this pool attaches to."
  type        = string
}

variable "name" {
  description = "Node pool name."
  type        = string
  default     = "vllm-gpu"
}

variable "flavor_name" {
  description = "OVH GPU flavor. L4 24 GB (e.g. t1-le-7) is the cost-minimum target for Mistral 7B."
  type        = string
  default     = "t1-le-7"
}

variable "min_nodes" {
  description = "Minimum pool size. 0 means the pool can scale to zero when no vLLM pod is scheduled (idle cost = 0)."
  type        = number
  default     = 0
}

variable "max_nodes" {
  description = "Maximum pool size."
  type        = number
  default     = 1
}

variable "desired_nodes" {
  description = "Initial node count when the pool is created."
  type        = number
  default     = 0
}

variable "taint_value" {
  description = "Taint applied to nodes so only tolerating pods (vLLM) land here. Backend/frontend pods stay on the default pool."
  type        = string
  default     = "vllm"
}
