# ── Cloud Run services ────────────────────────────────────────────────────────
# All services are set to allow-unauthenticated for simplicity in this POC.
# Qdrant persists vector data to a GCS bucket via Cloud Run's native GCS volume mount.
# Inter-service calls use Cloud Run service URLs.

# ── Qdrant (vector store) ─────────────────────────────────────────────────────
resource "google_cloud_run_v2_service" "qdrant" {
  name     = "qdrant"
  location = var.region
  project  = var.project_id

  ingress = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = local.sa_email

    containers {
      image = "qdrant/qdrant:v1.9.2"

      ports {
        container_port = 6333
      }

      env {
        name  = "QDRANT__STORAGE__STORAGE_PATH"
        value = "/qdrant/storage"
      }

      volume_mounts {
        name       = "qdrant-storage"
        mount_path = "/qdrant/storage"
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "1Gi"
        }
      }

      startup_probe {
        http_get {
          path = "/healthz"
          port = 6333
        }
        initial_delay_seconds = 10
        period_seconds        = 10
        failure_threshold     = 5
      }
    }

    volumes {
      name = "qdrant-storage"
      gcs {
        bucket    = google_storage_bucket.qdrant_storage.name
        read_only = false
      }
    }
  }

  depends_on = [
    google_project_service.apis,
    google_storage_bucket.qdrant_storage,
    google_storage_bucket_iam_member.qdrant_storage_admin,
  ]
}

resource "google_cloud_run_v2_service_iam_member" "qdrant_public" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.qdrant.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# ── Governance ────────────────────────────────────────────────────────────────
resource "google_cloud_run_v2_service" "governance" {
  name     = "governance"
  location = var.region
  project  = var.project_id

  ingress = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = local.sa_email

    containers {
      image = "${local.image_base}/governance:${var.image_tag}"

      ports {
        container_port = 8003
      }

      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }
      env {
        name  = "GCP_REGION"
        value = var.region
      }
      env {
        name  = "DATABASE_URL"
        value = "sqlite+aiosqlite:////app/data/governance.db"
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }

      startup_probe {
        http_get {
          path = "/health"
          port = 8003
        }
        initial_delay_seconds = 10
        period_seconds        = 10
        failure_threshold     = 5
      }
    }
  }

  depends_on = [google_project_service.apis]
}

resource "google_cloud_run_v2_service_iam_member" "governance_public" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.governance.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# ── LLM Gateway ───────────────────────────────────────────────────────────────
resource "google_cloud_run_v2_service" "llm_gateway" {
  name     = "llm-gateway"
  location = var.region
  project  = var.project_id

  ingress = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = local.sa_email

    containers {
      image = "${local.image_base}/llm-gateway:${var.image_tag}"

      ports {
        container_port = 4000
      }

      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }

      env {
        name = "ANTHROPIC_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.anthropic_api_key.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "LITELLM_MASTER_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.litellm_master_key.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "OPENAI_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.openai_api_key.secret_id
            version = "latest"
          }
        }
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "1Gi"
        }
      }
    }
  }

  depends_on = [
    google_project_service.apis,
    google_secret_manager_secret.anthropic_api_key,
    google_secret_manager_secret.litellm_master_key,
    google_secret_manager_secret.openai_api_key,
  ]
}

resource "google_cloud_run_v2_service_iam_member" "llm_gateway_public" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.llm_gateway.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# ── RAG Service ───────────────────────────────────────────────────────────────
resource "google_cloud_run_v2_service" "rag_service" {
  name     = "rag-service"
  location = var.region
  project  = var.project_id

  ingress = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = local.sa_email

    containers {
      image = "${local.image_base}/rag-service:${var.image_tag}"

      ports {
        container_port = 8001
      }

      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }
      env {
        name  = "GCP_REGION"
        value = var.region
      }
      env {
        name  = "GCS_BUCKET_NAME"
        value = var.gcs_bucket_name
      }
      env {
        name  = "QDRANT_URL"
        value = google_cloud_run_v2_service.qdrant.uri
      }
      env {
        name  = "QDRANT_COLLECTION"
        value = var.qdrant_collection
      }

      resources {
        limits = {
          cpu    = "2"
          memory = "2Gi"   # sentence-transformers model needs headroom
        }
      }

      startup_probe {
        http_get {
          path = "/health"
          port = 8001
        }
        initial_delay_seconds = 30
        period_seconds        = 10
        failure_threshold     = 6
      }
    }
  }

  depends_on = [
    google_project_service.apis,
    google_cloud_run_v2_service.qdrant,
  ]
}

resource "google_cloud_run_v2_service_iam_member" "rag_service_public" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.rag_service.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# ── Memory Service ────────────────────────────────────────────────────────────
resource "google_cloud_run_v2_service" "memory_service" {
  name     = "memory-service"
  location = var.region
  project  = var.project_id

  ingress = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = local.sa_email

    containers {
      image = "${local.image_base}/memory-service:${var.image_tag}"

      ports {
        container_port = 8004
      }

      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }
      env {
        name  = "LONGTERM_DB_PATH"
        value = "/app/data/memory.db"
      }
      # REDIS_URL left unset for prototype — falls back to in-memory session store.
      # For production: set to redis://redis-host:6379 via Cloud Memorystore.

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }

      startup_probe {
        http_get {
          path = "/health"
          port = 8004
        }
        initial_delay_seconds = 10
        period_seconds        = 10
        failure_threshold     = 5
      }
    }
  }

  depends_on = [google_project_service.apis]
}

resource "google_cloud_run_v2_service_iam_member" "memory_service_public" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.memory_service.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# ── Agent Core ────────────────────────────────────────────────────────────────
resource "google_cloud_run_v2_service" "agent_core" {
  name     = "agent-core"
  location = var.region
  project  = var.project_id

  ingress = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = local.sa_email
    timeout         = "300s"

    containers {
      image = "${local.image_base}/agent-core:${var.image_tag}"

      ports {
        container_port = 8002
      }

      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }
      env {
        name  = "GCP_REGION"
        value = var.region
      }
      env {
        name  = "LLM_GATEWAY_URL"
        value = google_cloud_run_v2_service.llm_gateway.uri
      }
      env {
        name  = "RAG_SERVICE_URL"
        value = google_cloud_run_v2_service.rag_service.uri
      }
      env {
        name  = "GOVERNANCE_URL"
        value = google_cloud_run_v2_service.governance.uri
      }
      env {
        name  = "MEMORY_SERVICE_URL"
        value = google_cloud_run_v2_service.memory_service.uri
      }
      env {
        name  = "AGENT_DEFAULT_MODEL"
        value = var.agent_default_model
      }

      env {
        name = "ANTHROPIC_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.anthropic_api_key.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "LITELLM_MASTER_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.litellm_master_key.secret_id
            version = "latest"
          }
        }
      }

      resources {
        limits = {
          cpu    = "2"
          memory = "1Gi"
        }
      }
    }
  }

  depends_on = [
    google_cloud_run_v2_service.governance,
    google_cloud_run_v2_service.llm_gateway,
    google_cloud_run_v2_service.rag_service,
    google_cloud_run_v2_service.memory_service,
  ]
}

resource "google_cloud_run_v2_service_iam_member" "agent_core_public" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.agent_core.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# ── Portal ────────────────────────────────────────────────────────────────────
resource "google_cloud_run_v2_service" "portal" {
  name     = "portal"
  location = var.region
  project  = var.project_id

  # Public — auth handled by NextAuth.js inside the Next.js app (Google OAuth).
  # Swap to INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER + IAP for production.
  ingress = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = local.sa_email
    scaling {
      max_instance_count = 1  # prevents OAuth state mismatch with NextAuth
    }

    containers {
      image = "${local.image_base}/portal:${var.image_tag}"

      ports {
        container_port = 3000
      }

      env {
        name  = "AGENT_CORE_URL"
        value = google_cloud_run_v2_service.agent_core.uri
      }
      env {
        name  = "NEXT_PUBLIC_AGENT_URL"
        value = google_cloud_run_v2_service.agent_core.uri
      }
      env {
        name  = "GOVERNANCE_URL"
        value = google_cloud_run_v2_service.governance.uri
      }
      env {
        name  = "RAG_SERVICE_URL"
        value = google_cloud_run_v2_service.rag_service.uri
      }
      env {
        name  = "LLM_GATEWAY_URL"
        value = google_cloud_run_v2_service.llm_gateway.uri
      }
      env {
        name  = "MEMORY_SERVICE_URL"
        value = google_cloud_run_v2_service.memory_service.uri
      }
      env {
        name  = "NEXT_PUBLIC_MEMORY_SERVICE_URL"
        value = google_cloud_run_v2_service.memory_service.uri
      }
      env {
        name  = "NEXTAUTH_URL"
        value = var.portal_url != "" ? var.portal_url : "https://placeholder.run.app"
      }
      env {
        name = "GOOGLE_CLIENT_ID"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.google_client_id.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "GOOGLE_CLIENT_SECRET"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.google_client_secret.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "NEXTAUTH_SECRET"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.nextauth_secret.secret_id
            version = "latest"
          }
        }
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }
    }
  }

  depends_on = [
    google_cloud_run_v2_service.agent_core,
    google_secret_manager_secret.google_client_id,
    google_secret_manager_secret.google_client_secret,
    google_secret_manager_secret.nextauth_secret,
  ]
}

resource "google_cloud_run_v2_service_iam_member" "portal_public" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.portal.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# ── IDE Chat ──────────────────────────────────────────────────────────────────
resource "google_cloud_run_v2_service" "ide_chat" {
  name     = "ide-chat"
  location = var.region
  project  = var.project_id

  ingress = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = local.sa_email

    containers {
      image = "${local.image_base}/ide-chat:${var.image_tag}"

      ports {
        container_port = 3001
      }

      env {
        name  = "AGENT_CORE_URL"
        value = google_cloud_run_v2_service.agent_core.uri
      }
      env {
        name  = "NEXT_PUBLIC_AGENT_URL"
        value = google_cloud_run_v2_service.agent_core.uri
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }
    }
  }

  depends_on = [google_cloud_run_v2_service.agent_core]
}

resource "google_cloud_run_v2_service_iam_member" "ide_chat_public" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.ide_chat.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
