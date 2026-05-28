output "qdrant_url" {
  description = "URL of the Qdrant vector store service"
  value       = google_cloud_run_v2_service.qdrant.uri
}

output "portal_url" {
  description = "Public URL of the portal"
  value       = google_cloud_run_v2_service.portal.uri
}

output "agent_core_url" {
  description = "URL of the agent-core service"
  value       = google_cloud_run_v2_service.agent_core.uri
}

output "rag_service_url" {
  description = "URL of the RAG service"
  value       = google_cloud_run_v2_service.rag_service.uri
}

output "llm_gateway_url" {
  description = "URL of the LLM gateway"
  value       = google_cloud_run_v2_service.llm_gateway.uri
}

output "governance_url" {
  description = "URL of the governance service"
  value       = google_cloud_run_v2_service.governance.uri
}

output "service_account_email" {
  description = "Runner service account email"
  value       = google_service_account.runner.email
}

output "artifact_registry" {
  description = "Artifact Registry image base path"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/agentic-ai"
}
