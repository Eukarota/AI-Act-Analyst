# Copy to main.tfvars and fill in. Never commit the populated file.
project_name = "boussole"
environment  = "prod"
service_name = "1ee01274e6114afe913deccd3a50d92a"
region       = "GRA11"

# Managed Postgres on the discovery plan (cost-minimum tier with
# pgvector). The module auto-strips the "11" to "GRA" since Managed
# Postgres uses the region group, not the datacenter code.
postgres_plan      = "discovery"
postgres_flavor    = "b3-8"
postgres_version   = "17"
postgres_disk_size = 160

# Kapsule worker nodes (separate SKU family from Postgres above).
node_pool_flavor = "b3-8"

backend_image  = "registry.gitlab.com/ceres-broker/boussole/backend:latest"
frontend_image = "registry.gitlab.com/ceres-broker/boussole/frontend:latest"

allowed_ingress_cidrs = [
  # Operator IPs for setup phase (psql, scripts/index_corpus.py).
  # Remove once corpus is indexed and the prod loop is settled.
  "128.79.194.237/32",                          # IPv4 operator
  "2001:861:8d70:76b0:dd19:3ec3:4c9:f371/128",  # IPv6 operator
]

# Shape selection for the LLM layer (ADR 0005).
# Public demo at aiact.ceres.broker = Shape A (Mistral La Plateforme) =
# gpu_enabled = false. No GPU bill.
#
# To activate Shape B (self-hosted vLLM) for a client mission, flip the
# flag and apply the infra/k8s/components/vllm/ kustomize component:
#   gpu_enabled        = true
#   gpu_flavor         = "t1-le-7"   # L4 24 GB
#   gpu_pool_min_nodes = 0           # scale-to-zero when no vLLM pod is scheduled
#   gpu_pool_max_nodes = 1
gpu_enabled = false
