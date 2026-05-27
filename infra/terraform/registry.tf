resource "google_artifact_registry_repository" "images" {
  provider = google

  location      = var.region
  repository_id = "agentic-ai"
  format        = "DOCKER"
  description   = "Agentic AI Platform Docker images"
  project       = var.project_id

  depends_on = [google_project_service.apis]
}
