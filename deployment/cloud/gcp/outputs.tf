# GCP Deployment Outputs

output "service_url" {
  description = "Cloud Run service URL"
  value       = google_cloud_run_v2_service.api.uri
}

output "service_name" {
  description = "Cloud Run service name"
  value       = google_cloud_run_v2_service.api.name
}

output "redis_host" {
  description = "Memorystore Redis host"
  value       = google_redis_instance.cache.host
}

output "redis_port" {
  description = "Memorystore Redis port"
  value       = google_redis_instance.cache.port
}

output "vpc_connector" {
  description = "VPC Access Connector name"
  value       = google_vpc_access_connector.connector.name
}

output "project_id" {
  description = "GCP Project ID"
  value       = var.project_id
}

output "region" {
  description = "Deployment region"
  value       = var.region
}

output "health_check_command" {
  description = "Command to test the health endpoint"
  value       = "curl ${google_cloud_run_v2_service.api.uri}/health"
}

output "test_command" {
  description = "Command to test the API (replace YOUR_API_KEY)"
  value       = "curl -H 'X-API-Key: YOUR_API_KEY' ${google_cloud_run_v2_service.api.uri}/health"
}
