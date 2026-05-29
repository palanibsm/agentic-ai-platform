# ── Cloud Workflows ───────────────────────────────────────────────────────────
# approval-gate  : routes agent actions through policy check + risk-based approval
# rag-ingestion  : triggers RAG service /ingest with retry + audit trail
#
# Both workflows run as the platform runner service account and use OIDC auth
# to call internal Cloud Run services.

# ── approval-gate workflow ────────────────────────────────────────────────────
resource "google_workflows_workflow" "approval_gate" {
  name            = "approval-gate"
  region          = var.region
  project         = var.project_id
  description     = "Routes agent actions through governance policy check and risk-based approval"
  service_account = local.sa_email

  user_env_vars = {
    GOVERNANCE_URL = google_cloud_run_v2_service.governance.uri
    GCP_PROJECT_ID = var.project_id
  }

  source_contents = file("${path.module}/../cloud-workflows/approval-gate.yaml")

  labels = {
    platform = "agentic-ai"
    env      = "production"
  }

  depends_on = [
    google_project_service.apis,
    google_cloud_run_v2_service.governance,
  ]
}

# ── rag-ingestion workflow ────────────────────────────────────────────────────
resource "google_workflows_workflow" "rag_ingestion" {
  name            = "rag-ingestion"
  region          = var.region
  project         = var.project_id
  description     = "Triggers RAG service /ingest with retry and publishes result to audit-events"
  service_account = local.sa_email

  user_env_vars = {
    RAG_SERVICE_URL = google_cloud_run_v2_service.rag_service.uri
    GCP_PROJECT_ID  = var.project_id
  }

  source_contents = file("${path.module}/../cloud-workflows/rag-ingestion.yaml")

  labels = {
    platform = "agentic-ai"
    env      = "production"
  }

  depends_on = [
    google_project_service.apis,
    google_cloud_run_v2_service.rag_service,
  ]
}

# ── Cloud Scheduler: run rag-ingestion nightly at 2am SGT (18:00 UTC) ─────────
resource "google_cloud_scheduler_job" "rag_ingestion_nightly" {
  name        = "rag-ingestion-nightly"
  description = "Nightly re-ingestion of GCS documents into Qdrant"
  schedule    = "0 18 * * *"   # 02:00 SGT = 18:00 UTC
  time_zone   = "Asia/Singapore"
  region      = var.region
  project     = var.project_id

  http_target {
    http_method = "POST"
    uri         = "https://workflowexecutions.googleapis.com/v1/projects/${var.project_id}/locations/${var.region}/workflows/${google_workflows_workflow.rag_ingestion.name}/executions"

    body = base64encode(jsonencode({
      argument = jsonencode({
        prefix        = ""
        allowed_roles = ["developer", "admin"]
      })
    }))

    headers = {
      "Content-Type" = "application/json"
    }

    oauth_token {
      service_account_email = local.sa_email
    }
  }

  depends_on = [
    google_project_service.apis,
    google_workflows_workflow.rag_ingestion,
  ]
}

# ── Grant runner SA permission to create workflow executions ──────────────────
resource "google_project_iam_member" "runner_workflows_invoker" {
  project = var.project_id
  role    = "roles/workflows.invoker"
  member  = "serviceAccount:${local.sa_email}"

  depends_on = [google_service_account.runner]
}
