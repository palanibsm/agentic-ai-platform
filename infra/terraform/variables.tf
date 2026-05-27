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
  description = "GCS bucket for RAG documents and chunk metadata"
  type        = string
}

variable "vertex_ai_index_id" {
  description = "Existing Vertex AI Vector Search index ID"
  type        = string
}

variable "vertex_ai_endpoint_id" {
  description = "Existing Vertex AI Vector Search endpoint ID"
  type        = string
}

variable "vertex_ai_deployed_index_id" {
  description = "Deployed index ID within the endpoint"
  type        = string
  default     = "deployed_index"
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
