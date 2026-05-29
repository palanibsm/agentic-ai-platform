output "qdrant_url" {
  description = "URL of the Qdrant vector store service"
  value       = google_cloud_run_v2_service.qdrant.uri
}

output "portal_url" {
  description = "Internal Cloud Run URL of the portal (not directly accessible — use portal_iap_url)"
  value       = google_cloud_run_v2_service.portal.uri
}

output "ide_chat_url" {
  description = "Internal Cloud Run URL of ide-chat (not directly accessible — use ide_chat_iap_url)"
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

output "artifact_registry" {
  description = "Artifact Registry image base path"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/agentic-ai"
}

output "portal_lb_ip" {
  description = "Global LB IP for portal — point portal_domain DNS A record here"
  value       = google_compute_global_address.portal_ip.address
}

output "ide_chat_lb_ip" {
  description = "Global LB IP for ide-chat — point ide_chat_domain DNS A record here"
  value       = google_compute_global_address.ide_chat_ip.address
}

output "portal_iap_url" {
  description = "IAP-secured portal URL (live once DNS A record set + managed SSL cert provisioned ~15 min)"
  value       = "https://${var.portal_domain}"
}

output "ide_chat_iap_url" {
  description = "IAP-secured IDE chat URL (live once DNS A record set + managed SSL cert provisioned ~15 min)"
  value       = "https://${var.ide_chat_domain}"
}
