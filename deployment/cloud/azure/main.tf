# Consoul API - Azure Container Apps Deployment
# Deploys Container Apps with Azure Cache for Redis and Key Vault

terraform {
  required_version = ">= 1.5"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
}

# =============================================================================
# Provider Configuration
# =============================================================================

provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy = true
    }
  }
}

# =============================================================================
# Data Sources
# =============================================================================

data "azurerm_client_config" "current" {}

# =============================================================================
# Local Values
# =============================================================================

locals {
  name_prefix = "${var.app_name}-${var.environment}"
  # Azure resource names have restrictions, ensure compliance
  resource_name = replace(local.name_prefix, "-", "")

  tags = {
    App         = var.app_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# =============================================================================
# Resource Group
# =============================================================================

resource "azurerm_resource_group" "main" {
  name     = "${local.name_prefix}-rg"
  location = var.location

  tags = local.tags
}

# =============================================================================
# Log Analytics Workspace (for Container Apps)
# =============================================================================

resource "azurerm_log_analytics_workspace" "main" {
  name                = "${local.name_prefix}-logs"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "PerGB2018"
  retention_in_days   = 30

  tags = local.tags
}

# =============================================================================
# Azure Cache for Redis
# =============================================================================

resource "azurerm_redis_cache" "main" {
  name                = "${local.resource_name}redis"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  capacity            = var.redis_capacity
  family              = var.redis_family
  sku_name            = var.redis_sku
  enable_non_ssl_port = true
  minimum_tls_version = "1.2"

  redis_configuration {
    maxmemory_policy = "volatile-lru"
  }

  tags = local.tags
}

# =============================================================================
# Key Vault
# =============================================================================

resource "azurerm_key_vault" "main" {
  name                        = "${local.resource_name}kv"
  location                    = azurerm_resource_group.main.location
  resource_group_name         = azurerm_resource_group.main.name
  enabled_for_disk_encryption = false
  tenant_id                   = data.azurerm_client_config.current.tenant_id
  soft_delete_retention_days  = 7
  purge_protection_enabled    = false
  sku_name                    = "standard"

  # Access policy for Terraform user
  access_policy {
    tenant_id = data.azurerm_client_config.current.tenant_id
    object_id = data.azurerm_client_config.current.object_id

    secret_permissions = [
      "Get", "List", "Set", "Delete", "Purge"
    ]
  }

  tags = local.tags
}

# Secrets
resource "azurerm_key_vault_secret" "api_keys" {
  name         = "consoul-api-keys"
  value        = join(",", var.api_keys)
  key_vault_id = azurerm_key_vault.main.id
}

resource "azurerm_key_vault_secret" "redis_connection" {
  name         = "redis-connection"
  value        = "redis://:${azurerm_redis_cache.main.primary_access_key}@${azurerm_redis_cache.main.hostname}:${azurerm_redis_cache.main.port}"
  key_vault_id = azurerm_key_vault.main.id
}

resource "azurerm_key_vault_secret" "openai_key" {
  count        = var.openai_api_key != "" ? 1 : 0
  name         = "openai-api-key"
  value        = var.openai_api_key
  key_vault_id = azurerm_key_vault.main.id
}

resource "azurerm_key_vault_secret" "anthropic_key" {
  count        = var.anthropic_api_key != "" ? 1 : 0
  name         = "anthropic-api-key"
  value        = var.anthropic_api_key
  key_vault_id = azurerm_key_vault.main.id
}

# =============================================================================
# Container Registry
# =============================================================================

resource "azurerm_container_registry" "main" {
  name                = "${local.resource_name}acr"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "Basic"
  admin_enabled       = true

  tags = local.tags
}

# =============================================================================
# Container Apps Environment
# =============================================================================

resource "azurerm_container_app_environment" "main" {
  name                       = "${local.name_prefix}-env"
  location                   = azurerm_resource_group.main.location
  resource_group_name        = azurerm_resource_group.main.name
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id

  tags = local.tags
}

# =============================================================================
# Container App
# =============================================================================

locals {
  image_url = var.image_url != "" ? var.image_url : "${azurerm_container_registry.main.login_server}/${var.app_name}:latest"
}

resource "azurerm_container_app" "main" {
  name                         = local.name_prefix
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"

  # Registry credentials
  registry {
    server               = azurerm_container_registry.main.login_server
    username             = azurerm_container_registry.main.admin_username
    password_secret_name = "acr-password"
  }

  # Secrets
  secret {
    name  = "acr-password"
    value = azurerm_container_registry.main.admin_password
  }

  secret {
    name  = "api-keys"
    value = join(",", var.api_keys)
  }

  secret {
    name  = "redis-url"
    value = "redis://:${azurerm_redis_cache.main.primary_access_key}@${azurerm_redis_cache.main.hostname}:${azurerm_redis_cache.main.ssl_port}?ssl=true"
  }

  dynamic "secret" {
    for_each = var.openai_api_key != "" ? [1] : []
    content {
      name  = "openai-key"
      value = var.openai_api_key
    }
  }

  dynamic "secret" {
    for_each = var.anthropic_api_key != "" ? [1] : []
    content {
      name  = "anthropic-key"
      value = var.anthropic_api_key
    }
  }

  # Ingress configuration
  ingress {
    external_enabled = true
    target_port      = 8000
    transport        = "http"

    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }

  # Container template
  template {
    min_replicas = var.min_replicas
    max_replicas = var.max_replicas

    container {
      name   = var.app_name
      image  = local.image_url
      cpu    = var.cpu
      memory = var.memory

      # Environment variables
      env {
        name        = "REDIS_URL"
        secret_name = "redis-url"
      }

      env {
        name        = "CONSOUL_API_KEYS"
        secret_name = "api-keys"
      }

      env {
        name  = "CONSOUL_CORS_ORIGINS"
        value = var.cors_origins
      }

      env {
        name  = "CONSOUL_DEFAULT_LIMITS"
        value = var.rate_limits
      }

      env {
        name  = "CONSOUL_SESSION_TTL"
        value = tostring(var.session_ttl)
      }

      env {
        name  = "CONSOUL_OBSERVABILITY_PROMETHEUS_ENABLED"
        value = tostring(var.prometheus_enabled)
      }

      dynamic "env" {
        for_each = var.openai_api_key != "" ? [1] : []
        content {
          name        = "OPENAI_API_KEY"
          secret_name = "openai-key"
        }
      }

      dynamic "env" {
        for_each = var.anthropic_api_key != "" ? [1] : []
        content {
          name        = "ANTHROPIC_API_KEY"
          secret_name = "anthropic-key"
        }
      }

      # Health probes
      liveness_probe {
        transport = "HTTP"
        path      = "/health"
        port      = 8000

        initial_delay    = 10
        interval_seconds = 30
        timeout          = 10
        failure_count_threshold = 3
      }

      readiness_probe {
        transport = "HTTP"
        path      = "/ready"
        port      = 8000

        interval_seconds = 10
        timeout          = 5
        failure_count_threshold = 3
      }
    }

    # HTTP scaling rule
    http_scale_rule {
      name                = "http-scaling"
      concurrent_requests = 80
    }
  }

  tags = local.tags
}
