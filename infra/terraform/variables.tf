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

# ── IAP / Load Balancer ───────────────────────────────────────────────────────

variable "alert_email" {
  description = "Email address for Cloud Monitoring alert notifications"
  type        = string
  default     = "stels.karthik@gmail.com"
}

variable "iap_support_email" {
  description = "Support email shown on the IAP OAuth consent screen (must be a Google account or group)"
  type        = string
  default     = ""
}

variable "iap_portal_client_id" {
  description = "OAuth2 client ID for portal IAP (create manually in GCP Console → Credentials)"
  type        = string
  sensitive   = true
}

variable "iap_portal_client_secret" {
  description = "OAuth2 client secret for portal IAP"
  type        = string
  sensitive   = true
}

variable "iap_ide_chat_client_id" {
  description = "OAuth2 client ID for ide-chat IAP (create manually in GCP Console → Credentials)"
  type        = string
  sensitive   = true
}

variable "iap_ide_chat_client_secret" {
  description = "OAuth2 client secret for ide-chat IAP"
  type        = string
  sensitive   = true
}

variable "iap_allowed_users" {
  description = "IAM members allowed through IAP (e.g. [\"user:alice@example.com\", \"group:devs@example.com\"])"
  type        = list(string)
  default     = []
}

variable "portal_domain" {
  description = "Custom domain for the portal (e.g. portal.ai.example.com). Used for managed SSL cert."
  type        = string
}

variable "ide_chat_domain" {
  description = "Custom domain for IDE chat (e.g. ide.ai.example.com). Used for managed SSL cert."
  type        = string
}
