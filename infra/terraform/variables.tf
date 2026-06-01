variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "us-central1"
}

variable "image_tag" {
  description = "Docker image tag to deploy"
  type        = string
  default     = "latest"
}

variable "gcs_bucket_name" {
  description = "GCS bucket for RAG source documents"
  type        = string
}

variable "qdrant_collection" {
  description = "Qdrant collection name for the knowledge base"
  type        = string
  default     = "knowledge-base"
}

variable "agent_default_model" {
  description = "Default LLM model alias"
  type        = string
  default     = "claude-sonnet"
}

variable "llm_budget_usd" {
  description = "Monthly LLM spend cap in USD"
  type        = number
  default     = 25
}

variable "alert_email" {
  description = "Email address for Cloud Monitoring alert notifications"
  type        = string
  default     = "stels.karthik@gmail.com"
}

# ── NextAuth.js Google OAuth ───────────────────────────────────────────────────
# Used by portal for Google login (replaces IAP for prototype).
# Create OAuth client at: GCP Console → APIs & Services → Credentials
# Authorized redirect URI: https://<portal-cloud-run-url>/api/auth/callback/google

variable "google_client_id" {
  description = "Google OAuth client ID for NextAuth.js portal login"
  type        = string
  sensitive   = true
}

variable "google_client_secret" {
  description = "Google OAuth client secret for NextAuth.js portal login"
  type        = string
  sensitive   = true
}

variable "nextauth_secret" {
  description = "Random secret for NextAuth.js session encryption (generate with: openssl rand -base64 32)"
  type        = string
  sensitive   = true
}

variable "portal_url" {
  description = "Public URL of the portal Cloud Run service (used as NEXTAUTH_URL)"
  type        = string
  default     = ""
}
