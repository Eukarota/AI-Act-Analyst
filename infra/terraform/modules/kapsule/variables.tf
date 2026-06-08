variable "service_name" {
  type = string
}

variable "name" {
  type = string
}

variable "region" {
  type = string
}

variable "kapsule_version" {
  type    = string
  default = "1.30"
}

variable "node_pool_flavor" {
  type    = string
  default = "b3-8"
}

variable "node_pool_min_nodes" {
  type    = number
  default = 2
}

variable "node_pool_max_nodes" {
  type    = number
  default = 4
}
