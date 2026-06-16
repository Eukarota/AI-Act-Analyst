variable "service_name" {
  description = "OVH Public Cloud project ID."
  type        = string
}

variable "name" {
  description = "Display name for the cluster."
  type        = string
}

variable "region" {
  description = "OVH region."
  type        = string
}

variable "plan" {
  description = "Managed Postgres plan (discovery, essential, business, enterprise, production). discovery is the cheapest tier and is the cost-minimum default for the public demo."
  type        = string
  default     = "discovery"
}

variable "flavor" {
  description = "Compute flavor. b3-8 is the cheapest flavor available on the discovery plan."
  type        = string
  default     = "b3-8"
}

variable "engine_version" {
  description = "PostgreSQL major version. Pinned, not auto-upgraded by OVH."
  type        = string
  default     = "17"
}

variable "disk_size" {
  description = "Disk size in GB. 160 is the discovery plan default and is sufficient for the corpus + traces."
  type        = number
  default     = 160
}

variable "allowed_ingress_cidrs" {
  description = "IP allowlist for direct connections (operators, CI). Empty = closed."
  type        = list(string)
  default     = []
}
