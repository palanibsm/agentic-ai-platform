resource "google_storage_bucket" "rag_store" {
  name          = var.gcs_bucket_name
  location      = var.region
  project       = var.project_id
  force_destroy = false

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      num_newer_versions = 3
    }
  }

  depends_on = [google_project_service.apis]
}

# ── Qdrant persistent storage bucket ─────────────────────────────────────────
resource "google_storage_bucket" "qdrant_storage" {
  name          = "${var.project_id}-qdrant-storage"
  location      = var.region
  project       = var.project_id
  force_destroy = true   # vector data can be re-indexed

  uniform_bucket_level_access = true

  depends_on = [google_project_service.apis]
}

# Give the runner SA full object admin on the Qdrant bucket (Qdrant needs
# create/read/update/delete on its storage files via the GCS FUSE mount)
resource "google_storage_bucket_iam_member" "qdrant_storage_admin" {
  bucket = google_storage_bucket.qdrant_storage.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${local.sa_email}"

  depends_on = [google_service_account.runner]
}

# State bucket for Terraform — created once manually, referenced here for docs
# gcloud storage buckets create gs://${var.project_id}-tf-state --location=${var.region}
