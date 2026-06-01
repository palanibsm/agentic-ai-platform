resource "google_project_service" "apis" {
  for_each = toset([
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "secretmanager.googleapis.com",
    "pubsub.googleapis.com",
    "storage.googleapis.com",
    "iam.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
    "workflows.googleapis.com",
    "cloudscheduler.googleapis.com",
    "compute.googleapis.com",         # Load Balancer (IAP frontend)
    "iap.googleapis.com",             # Identity-Aware Proxy
    "sqladmin.googleapis.com",        # Cloud SQL
    "monitoring.googleapis.com",      # Cloud Monitoring
    "logging.googleapis.com",         # Cloud Logging (already enabled, explicit here)
  ])

  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}
