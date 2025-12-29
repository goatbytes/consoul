# Azure Deployment Outputs

output "service_url" {
  description = "Container App FQDN"
  value       = "https://${azurerm_container_app.main.ingress[0].fqdn}"
}

output "container_app_name" {
  description = "Container App name"
  value       = azurerm_container_app.main.name
}

output "acr_login_server" {
  description = "Azure Container Registry login server"
  value       = azurerm_container_registry.main.login_server
}

output "acr_admin_username" {
  description = "ACR admin username"
  value       = azurerm_container_registry.main.admin_username
}

output "acr_admin_password" {
  description = "ACR admin password"
  value       = azurerm_container_registry.main.admin_password
  sensitive   = true
}

output "redis_hostname" {
  description = "Azure Cache for Redis hostname"
  value       = azurerm_redis_cache.main.hostname
}

output "redis_ssl_port" {
  description = "Azure Cache for Redis SSL port"
  value       = azurerm_redis_cache.main.ssl_port
}

output "resource_group_name" {
  description = "Resource group name"
  value       = azurerm_resource_group.main.name
}

output "key_vault_name" {
  description = "Key Vault name"
  value       = azurerm_key_vault.main.name
}

output "log_analytics_workspace" {
  description = "Log Analytics workspace name"
  value       = azurerm_log_analytics_workspace.main.name
}

output "location" {
  description = "Azure region"
  value       = var.location
}

output "health_check_command" {
  description = "Command to test the health endpoint"
  value       = "curl https://${azurerm_container_app.main.ingress[0].fqdn}/health"
}

output "test_command" {
  description = "Command to test the API (replace YOUR_API_KEY)"
  value       = "curl -H 'X-API-Key: YOUR_API_KEY' https://${azurerm_container_app.main.ingress[0].fqdn}/health"
}

output "docker_push_commands" {
  description = "Commands to build and push Docker image"
  value       = <<-EOT
    az acr login --name ${azurerm_container_registry.main.name}
    docker build -f deployment/cloud/shared/Dockerfile -t ${azurerm_container_registry.main.login_server}/${var.app_name}:latest .
    docker push ${azurerm_container_registry.main.login_server}/${var.app_name}:latest
  EOT
}
