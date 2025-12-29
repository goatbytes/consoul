# AWS Deployment Variables for Consoul API

# =============================================================================
# Required Variables
# =============================================================================

variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
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
  description = "Container image URL (ECR or Docker Hub)"
  type        = string
  default     = ""
}

# =============================================================================
# Networking
# =============================================================================

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "List of availability zones"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]
}

# =============================================================================
# ECS Configuration
# =============================================================================

variable "cpu" {
  description = "Fargate CPU units (256, 512, 1024, 2048, 4096)"
  type        = number
  default     = 512
}

variable "memory" {
  description = "Fargate memory in MB"
  type        = number
  default     = 1024
}

variable "desired_count" {
  description = "Desired number of tasks"
  type        = number
  default     = 1
}

variable "min_capacity" {
  description = "Minimum number of tasks for auto-scaling"
  type        = number
  default     = 1
}

variable "max_capacity" {
  description = "Maximum number of tasks for auto-scaling"
  type        = number
  default     = 10
}

variable "cpu_target" {
  description = "Target CPU utilization for auto-scaling"
  type        = number
  default     = 70
}

# =============================================================================
# Redis Configuration
# =============================================================================

variable "redis_node_type" {
  description = "ElastiCache node type"
  type        = string
  default     = "cache.t3.micro"
}

variable "redis_num_cache_nodes" {
  description = "Number of cache nodes"
  type        = number
  default     = 1
}

variable "redis_engine_version" {
  description = "Redis engine version"
  type        = string
  default     = "7.0"
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
