# GCP Deployment Variables for Consoul API

# =============================================================================
# Required Variables
# =============================================================================

variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP region for deployment"
  type        = string
  default     = "us-central1"
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
  description = "Container image URL (gcr.io/PROJECT/IMAGE:TAG)"
  type        = string
  default     = ""
}

# =============================================================================
# Scaling Configuration
# =============================================================================

variable "min_instances" {
  description = "Minimum number of Cloud Run instances (0 for scale-to-zero)"
  type        = number
  default     = 0
}

variable "max_instances" {
  description = "Maximum number of Cloud Run instances"
  type        = number
  default     = 10
}

variable "cpu" {
  description = "CPU allocation per instance"
  type        = string
  default     = "1"
}

variable "memory" {
  description = "Memory allocation per instance"
  type        = string
  default     = "512Mi"
}

variable "concurrency" {
  description = "Maximum concurrent requests per instance"
  type        = number
  default     = 80
}

# =============================================================================
# Redis Configuration
# =============================================================================

variable "redis_tier" {
  description = "Memorystore Redis tier (BASIC or STANDARD_HA)"
  type        = string
  default     = "BASIC"
}

variable "redis_memory_gb" {
  description = "Redis memory size in GB"
  type        = number
  default     = 1
}

variable "redis_version" {
  description = "Redis version"
  type        = string
  default     = "REDIS_7_0"
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

variable "google_api_key" {
  description = "Google AI API key (optional)"
  type        = string
  default     = ""
  sensitive   = true
}
