terraform {
  required_version = ">= 1.6"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }

  # Remote state in GCS.
  # Create the bucket once before first init:
  #   gcloud storage buckets create gs://ai-agent-project-497604-tf-state --location=us-central1
  backend "gcs" {
    bucket = "ai-agent-project-497604-tf-state"
    prefix = "agentic-ai/state"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

locals {
  image_base = "${var.region}-docker.pkg.dev/${var.project_id}/agentic-ai"
  sa_email   = google_service_account.runner.email
  # database_url and db_connection_name removed — using SQLite for prototype
}
