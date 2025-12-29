# Azure Deployment Variables for Consoul API

# =============================================================================
# Required Variables
# =============================================================================

variable "location" {
  description = "Azure region for deployment"
  type        = string
  default     = "eastus"
}

variable "api_keys" {
  description = "List of API keys for authentication"
  type        = list(string)
  sensitive   = true
}

# =============================================================================
# Application Configuration
# =============================================================================

variable "app_name" {
  description = "Application name (used for resource naming)"
  type        = string
  default     = "consoul-api"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "prod"
}

variable "image_url" {
  description = "Container image URL (ACR or Docker Hub)"
  type        = string
  default     = ""
}

# =============================================================================
# Container Apps Configuration
# =============================================================================

variable "cpu" {
  description = "CPU cores per container (0.25, 0.5, 1, 2, 4)"
  type        = number
  default     = 0.5
}

variable "memory" {
  description = "Memory in GB per container"
  type        = string
  default     = "1Gi"
}

variable "min_replicas" {
  description = "Minimum number of replicas (0 for scale to zero)"
  type        = number
  default     = 0
}

variable "max_replicas" {
  description = "Maximum number of replicas"
  type        = number
  default     = 10
}

# =============================================================================
# Redis Configuration
# =============================================================================

variable "redis_sku" {
  description = "Azure Cache SKU (Basic, Standard, Premium)"
  type        = string
  default     = "Basic"
}

variable "redis_family" {
  description = "Azure Cache family (C for Basic/Standard, P for Premium)"
  type        = string
  default     = "C"
}

variable "redis_capacity" {
  description = "Azure Cache capacity (0-6 for C family)"
  type        = number
  default     = 0
}

# =============================================================================
# Consoul Configuration
# =============================================================================

variable "cors_origins" {
  description = "CORS allowed origins (comma-separated)"
  type        = string
  default     = "*"
}

variable "rate_limits" {
  description = "Rate limit configuration"
  type        = string
  default     = "30/minute;500/hour"
}

variable "session_ttl" {
  description = "Session TTL in seconds"
  type        = number
  default     = 3600
}

variable "prometheus_enabled" {
  description = "Enable Prometheus metrics"
  type        = bool
  default     = true
}

# =============================================================================
# Optional: LLM API Keys
# =============================================================================

variable "openai_api_key" {
  description = "OpenAI API key (optional)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "anthropic_api_key" {
  description = "Anthropic API key (optional)"
  type        = string
  default     = ""
  sensitive   = true
}
