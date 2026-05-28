resource "google_service_account" "runner" {
  account_id   = "agentic-ai-runner"
  display_name = "Agentic AI Platform Runner"
  project      = var.project_id
}

locals {
  runner_roles = [
    "roles/pubsub.publisher",
    "roles/secretmanager.secretAccessor",
    "roles/storage.objectAdmin",    # covers viewer+creator+deleter (needed for Qdrant GCS volume)
    "roles/logging.logWriter",
    "roles/cloudtrace.agent",
    "roles/monitoring.metricWriter",
  ]
}

resource "google_project_iam_member" "runner_roles" {
  for_each = toset(local.runner_roles)

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.runner.email}"
}

# Allow Cloud Build SA to deploy to Cloud Run and push to Artifact Registry
resource "google_project_iam_member" "cloudbuild_run_admin" {
  project = var.project_id
  role    = "roles/run.admin"
  member  = "serviceAccount:${data.google_project.project.number}@cloudbuild.gserviceaccount.com"
}

resource "google_project_iam_member" "cloudbuild_sa_user" {
  project = var.project_id
  role    = "roles/iam.serviceAccountUser"
  member  = "serviceAccount:${data.google_project.project.number}@cloudbuild.gserviceaccount.com"
}

resource "google_project_iam_member" "cloudbuild_ar_writer" {
  project = var.project_id
  role    = "roles/artifactregistry.writer"
  member  = "serviceAccount:${data.google_project.project.number}@cloudbuild.gserviceaccount.com"
}

data "google_project" "project" {
  project_id = var.project_id
}
