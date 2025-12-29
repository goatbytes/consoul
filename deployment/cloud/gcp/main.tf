# Consoul API - GCP Cloud Run Deployment
# Deploys Cloud Run service with Memorystore Redis and Secret Manager

terraform {
  required_version = ">= 1.5"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

# =============================================================================
# Provider Configuration
# =============================================================================

provider "google" {
  project = var.project_id
  region  = var.region
}

# =============================================================================
# Local Values
# =============================================================================

locals {
  service_name = "${var.app_name}-${var.environment}"
  image_url    = var.image_url != "" ? var.image_url : "gcr.io/${var.project_id}/${var.app_name}:latest"

  labels = {
    app         = var.app_name
    environment = var.environment
    managed_by  = "terraform"
  }
}

# =============================================================================
# Enable Required APIs
# =============================================================================

resource "google_project_service" "apis" {
  for_each = toset([
    "run.googleapis.com",
    "redis.googleapis.com",
    "secretmanager.googleapis.com",
    "vpcaccess.googleapis.com",
    "compute.googleapis.com",
  ])

  service            = each.value
  disable_on_destroy = false
}

# =============================================================================
# VPC Network for Redis Access
# =============================================================================

resource "google_compute_network" "vpc" {
  name                    = "${local.service_name}-vpc"
  auto_create_subnetworks = false

  depends_on = [google_project_service.apis]
}

resource "google_compute_subnetwork" "subnet" {
  name          = "${local.service_name}-subnet"
  ip_cidr_range = "10.0.0.0/24"
  region        = var.region
  network       = google_compute_network.vpc.id
}

# VPC Connector for Cloud Run to access Redis
resource "google_vpc_access_connector" "connector" {
  name          = "${var.app_name}-connector"
  region        = var.region
  ip_cidr_range = "10.8.0.0/28"
  network       = google_compute_network.vpc.name

  depends_on = [google_project_service.apis]
}

# =============================================================================
# Memorystore Redis
# =============================================================================

resource "google_redis_instance" "cache" {
  name           = "${local.service_name}-redis"
  tier           = var.redis_tier
  memory_size_gb = var.redis_memory_gb
  region         = var.region
  redis_version  = var.redis_version

  authorized_network = google_compute_network.vpc.id

  labels = local.labels

  depends_on = [google_project_service.apis]
}

# =============================================================================
# Secret Manager - API Keys
# =============================================================================

resource "google_secret_manager_secret" "api_keys" {
  secret_id = "${local.service_name}-api-keys"

  replication {
    auto {}
  }

  labels = local.labels

  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_version" "api_keys" {
  secret      = google_secret_manager_secret.api_keys.id
  secret_data = join(",", var.api_keys)
}

# Optional: OpenAI API Key
resource "google_secret_manager_secret" "openai_key" {
  count     = var.openai_api_key != "" ? 1 : 0
  secret_id = "${local.service_name}-openai-key"

  replication {
    auto {}
  }

  labels     = local.labels
  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_version" "openai_key" {
  count       = var.openai_api_key != "" ? 1 : 0
  secret      = google_secret_manager_secret.openai_key[0].id
  secret_data = var.openai_api_key
}

# Optional: Anthropic API Key
resource "google_secret_manager_secret" "anthropic_key" {
  count     = var.anthropic_api_key != "" ? 1 : 0
  secret_id = "${local.service_name}-anthropic-key"

  replication {
    auto {}
  }

  labels     = local.labels
  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_version" "anthropic_key" {
  count       = var.anthropic_api_key != "" ? 1 : 0
  secret      = google_secret_manager_secret.anthropic_key[0].id
  secret_data = var.anthropic_api_key
}

# =============================================================================
# Cloud Run Service
# =============================================================================

resource "google_cloud_run_v2_service" "api" {
  name     = local.service_name
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    scaling {
      min_instance_count = var.min_instances
      max_instance_count = var.max_instances
    }

    vpc_access {
      connector = google_vpc_access_connector.connector.id
      egress    = "PRIVATE_RANGES_ONLY"
    }

    containers {
      image = local.image_url

      resources {
        limits = {
          cpu    = var.cpu
          memory = var.memory
        }
        cpu_idle = var.min_instances == 0
      }

      # Port configuration
      ports {
        container_port = 8000
      }

      # Redis connection
      env {
        name  = "REDIS_URL"
        value = "redis://${google_redis_instance.cache.host}:${google_redis_instance.cache.port}"
      }

      # API Keys from Secret Manager
      env {
        name = "CONSOUL_API_KEYS"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.api_keys.secret_id
            version = "latest"
          }
        }
      }

      # Optional: OpenAI API Key
      dynamic "env" {
        for_each = var.openai_api_key != "" ? [1] : []
        content {
          name = "OPENAI_API_KEY"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.openai_key[0].secret_id
              version = "latest"
            }
          }
        }
      }

      # Optional: Anthropic API Key
      dynamic "env" {
        for_each = var.anthropic_api_key != "" ? [1] : []
        content {
          name = "ANTHROPIC_API_KEY"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.anthropic_key[0].secret_id
              version = "latest"
            }
          }
        }
      }

      # Consoul configuration
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

      # Startup and liveness probes
      startup_probe {
        http_get {
          path = "/health"
          port = 8000
        }
        initial_delay_seconds = 5
        period_seconds        = 10
        failure_threshold     = 3
      }

      liveness_probe {
        http_get {
          path = "/health"
          port = 8000
        }
        period_seconds    = 30
        failure_threshold = 3
      }
    }

    labels = local.labels
  }

  labels = local.labels

  depends_on = [
    google_project_service.apis,
    google_secret_manager_secret_version.api_keys,
  ]
}

# =============================================================================
# IAM - Allow Public Access
# =============================================================================

resource "google_cloud_run_v2_service_iam_member" "public" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.api.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# IAM - Allow Cloud Run to access secrets
resource "google_secret_manager_secret_iam_member" "api_keys_access" {
  secret_id = google_secret_manager_secret.api_keys.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_cloud_run_v2_service.api.template[0].service_account}"
}

resource "google_secret_manager_secret_iam_member" "openai_key_access" {
  count     = var.openai_api_key != "" ? 1 : 0
  secret_id = google_secret_manager_secret.openai_key[0].secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_cloud_run_v2_service.api.template[0].service_account}"
}

resource "google_secret_manager_secret_iam_member" "anthropic_key_access" {
  count     = var.anthropic_api_key != "" ? 1 : 0
  secret_id = google_secret_manager_secret.anthropic_key[0].secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_cloud_run_v2_service.api.template[0].service_account}"
}
