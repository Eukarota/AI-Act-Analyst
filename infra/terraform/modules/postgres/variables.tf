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
  description = "Managed Postgres plan (essential, business, enterprise, production)."
  type        = string
  default     = "essential"
}

variable "flavor" {
  description = "Compute flavor."
  type        = string
  default     = "db1-7"
}

variable "allowed_ingress_cidrs" {
  description = "IP allowlist for direct connections (operators, CI). Empty = closed."
  type        = list(string)
  default     = []
}
