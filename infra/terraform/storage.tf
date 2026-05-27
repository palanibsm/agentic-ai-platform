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

# State bucket for Terraform — created once manually, referenced here for docs
# gcloud storage buckets create gs://${var.project_id}-tf-state --location=${var.region}
