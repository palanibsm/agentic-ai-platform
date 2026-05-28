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
