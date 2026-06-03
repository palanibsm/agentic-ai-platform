# Secret Manager — secrets are declared here but values are set outside Terraform
# (via deploy.ps1 or manually) to avoid storing secrets in state.

resource "google_secret_manager_secret" "anthropic_api_key" {
  secret_id = "anthropic-api-key"
  project   = var.project_id

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret" "litellm_master_key" {
  secret_id = "litellm-master-key"
  project   = var.project_id

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret" "openai_api_key" {
  secret_id = "openai-api-key"
  project   = var.project_id

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis]
}

# ── NextAuth.js secrets ───────────────────────────────────────────────────────

resource "google_secret_manager_secret" "google_client_id" {
  secret_id = "google-client-id"
  project   = var.project_id
  replication {
    auto {}
  }
  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret" "google_client_secret" {
  secret_id = "google-client-secret"
  project   = var.project_id
  replication {
    auto {}
  }
  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret" "nextauth_secret" {
  secret_id = "nextauth-secret"
  project   = var.project_id
  replication {
    auto {}
  }
  depends_on = [google_project_service.apis]
}
