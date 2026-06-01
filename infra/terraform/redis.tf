# ── Redis on Cloud Run ────────────────────────────────────────────────────────
# Used by: memory-service (session memory, working memory, TTL-based caching)
#
# Running Redis in Cloud Run (not Memorystore) to keep costs low for prototype.
# Data is ephemeral — session memory is cleared on instance restart.
# For production: replace with Cloud Memorystore for Redis.

resource "google_cloud_run_v2_service" "redis" {
  name     = "redis"
  location = var.region
  project  = var.project_id

  ingress = "INGRESS_TRAFFIC_INTERNAL_ONLY"

  template {
    service_account = local.sa_email

    containers {
      image = "redis:7-alpine"

      ports {
        container_port = 6379
      }

      args = [
        "redis-server",
        "--maxmemory", "256mb",
        "--maxmemory-policy", "allkeys-lru",
        "--save", "",           # disable RDB persistence (ephemeral)
        "--appendonly", "no",   # disable AOF persistence
      ]

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }

      startup_probe {
        tcp_socket {
          port = 6379
        }
        initial_delay_seconds = 5
        period_seconds        = 5
        failure_threshold     = 3
      }
    }
  }

  depends_on = [google_project_service.apis]
}

# Internal-only — no public invoker
resource "google_cloud_run_v2_service_iam_member" "redis_invoker" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.redis.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${local.sa_email}"
}
