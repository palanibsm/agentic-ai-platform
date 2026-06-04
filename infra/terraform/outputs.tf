output "qdrant_url" {
  description = "URL of the Qdrant vector store service"
  value       = google_cloud_run_v2_service.qdrant.uri
}

output "portal_url" {
  description = "Public URL of the portal (NextAuth.js Google login)"
  value       = google_cloud_run_v2_service.portal.uri
}

output "ide_chat_url" {
  description = "URL of the IDE Chat developer interface"
  value       = google_cloud_run_v2_service.ide_chat.uri
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

output "approval_gate_workflow" {
  description = "Name of the approval-gate Cloud Workflow"
  value       = google_workflows_workflow.approval_gate.name
}

output "rag_ingestion_workflow" {
  description = "Name of the rag-ingestion Cloud Workflow"
  value       = google_workflows_workflow.rag_ingestion.name
}

output "service_account_email" {
  description = "Runner service account email"
  value       = google_service_account.runner.email
}

output "memory_service_url" {
  description = "URL of the memory service"
  value       = google_cloud_run_v2_service.memory_service.uri
}

output "artifact_registry" {
  description = "Artifact Registry image base path"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/agentic-ai"
}
