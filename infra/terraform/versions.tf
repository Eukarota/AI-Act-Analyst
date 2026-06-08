terraform {
  required_version = ">= 1.7"

  required_providers {
    ovh = {
      source  = "ovh/ovh"
      version = "~> 0.50"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.30"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}
