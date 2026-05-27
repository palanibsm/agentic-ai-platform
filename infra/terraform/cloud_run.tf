# ── Cloud Run services ────────────────────────────────────────────────────────
# All internal services (governance, llm-gateway, rag-service) are private.
# agent-core is private. Only portal is public.
# Inter-service calls use Cloud Run service URLs with the runner SA identity.

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
        initial_delay_seconds = 5
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
        name  = "VERTEX_AI_INDEX_ID"
        value = var.vertex_ai_index_id
      }
      env {
        name  = "VERTEX_AI_ENDPOINT_ID"
        value = var.vertex_ai_endpoint_id
      }
      env {
        name  = "VERTEX_AI_DEPLOYED_INDEX_ID"
        value = var.vertex_ai_deployed_index_id
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "1Gi"
        }
      }
    }
  }

  depends_on = [google_project_service.apis]
}

resource "google_cloud_run_v2_service_iam_member" "rag_service_public" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.rag_service.name
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
    timeout         = "120s"

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

  ingress = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = local.sa_email

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

resource "google_cloud_run_v2_service_iam_member" "portal_public" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.portal.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
