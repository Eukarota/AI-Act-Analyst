locals {
  primary_endpoint = [for ep in ovh_cloud_project_database.this.endpoints : ep if ep.component == "postgresql"][0]
}

output "dsn" {
  description = "Postgres connection string. Wire into BOUSSOLE_DATABASE_URL."
  value = format(
    "postgresql://%s:%s@%s:%d/%s?sslmode=require",
    ovh_cloud_project_database_postgresql_user.app.name,
    ovh_cloud_project_database_postgresql_user.app.password,
    local.primary_endpoint.domain,
    local.primary_endpoint.port,
    ovh_cloud_project_database_database.main.name,
  )
  sensitive = true
}

output "cluster_id" {
  description = "Internal cluster identifier."
  value       = ovh_cloud_project_database.this.id
}
