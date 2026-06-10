variable "project_name" {
  description = "Short slug used to name OVH resources for this environment."
  type        = string
  default     = "boussole"
}

variable "environment" {
  description = "prod | staging | dev. Used as a suffix on resource names."
  type        = string
}

variable "ovh_endpoint" {
  description = "OVH API endpoint. Use 'ovh-eu' for the EU API."
  type        = string
  default     = "ovh-eu"
}

variable "service_name" {
  description = "OVH Public Cloud service_name (the project ID, not the display name)."
  type        = string
}

variable "region" {
  description = "OVH region for Public Cloud workloads."
  type        = string
  default     = "GRA11"

  validation {
    condition     = can(regex("^(GRA|SBG|RBX|WAW|DE|UK)[0-9]*$", var.region))
    error_message = "Region must be an OVH EU-resident code (GRA*, SBG*, RBX*, WAW*, DE*, UK*)."
  }
}

variable "postgres_plan" {
  description = "OVH Managed Postgres plan. Confirm pgvector availability before changing."
  type        = string
  default     = "essential"
}

variable "postgres_flavor" {
  description = "Compute flavor for the Managed Postgres instance."
  type        = string
  default     = "db1-7"
}

variable "kapsule_version" {
  description = "Managed Kubernetes (Kapsule) version."
  type        = string
  default     = "1.30"
}

variable "node_pool_flavor" {
  description = "Node pool instance flavor."
  type        = string
  default     = "b3-8"
}

variable "node_pool_min_nodes" {
  description = "Minimum number of nodes in the default pool."
  type        = number
  default     = 2
}

variable "node_pool_max_nodes" {
  description = "Maximum number of nodes in the default pool."
  type        = number
  default     = 4
}

variable "backend_image" {
  description = "Container image reference for the backend deployment."
  type        = string
}

variable "frontend_image" {
  description = "Container image reference for the frontend deployment."
  type        = string
}

variable "allowed_ingress_cidrs" {
  description = "CIDRs allowed to reach the Managed Postgres (operator IPs)."
  type        = list(string)
  default     = []
}

variable "gpu_enabled" {
  description = "Provision the GPU node pool for self-hosted vLLM (Shape B). Default false so the bill is unaffected for the public demo, which runs on Mistral La Plateforme (Shape A, ADR 0005)."
  type        = bool
  default     = false
}

variable "gpu_flavor" {
  description = "OVH GPU flavor for the vLLM node pool. Ignored when gpu_enabled = false."
  type        = string
  default     = "t1-le-7"
}

variable "gpu_pool_min_nodes" {
  description = "Minimum GPU nodes. 0 means scale-to-zero when no vLLM pod is scheduled."
  type        = number
  default     = 0
}

variable "gpu_pool_max_nodes" {
  description = "Maximum GPU nodes."
  type        = number
  default     = 1
}

variable "tags" {
  description = "Free-form tags applied where the provider supports them."
  type        = map(string)
  default = {
    project    = "boussole"
    regulation = "ai_act"
    sovereign  = "eu"
  }
}
