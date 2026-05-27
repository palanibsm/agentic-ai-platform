resource "google_pubsub_topic" "audit_events" {
  name    = "audit-events"
  project = var.project_id

  message_retention_duration = "604800s" # 7 days

  depends_on = [google_project_service.apis]
}

# Dead-letter topic for failed audit events
resource "google_pubsub_topic" "audit_events_dlq" {
  name    = "audit-events-dlq"
  project = var.project_id

  depends_on = [google_project_service.apis]
}

# Subscription for audit log consumers (e.g. SIEM, compliance dashboards)
resource "google_pubsub_subscription" "audit_events_sub" {
  name    = "audit-events-sub"
  topic   = google_pubsub_topic.audit_events.name
  project = var.project_id

  ack_deadline_seconds       = 60
  message_retention_duration = "604800s" # 7 days
  retain_acked_messages      = true

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.audit_events_dlq.id
    max_delivery_attempts = 5
  }

  expiration_policy {
    ttl = "" # never expire
  }
}
