# ── Cloud Monitoring — Agentic AI Platform ────────────────────────────────────
# Resources:
#   - Email notification channel
#   - Uptime checks for all Cloud Run services
#   - Alert policies: service down, high error rate, high latency, scaling spike
#   - Log-based metrics: skill invocations, policy violations, RAG failures
#   - Monitoring dashboard

locals {
  # Strip https:// from Cloud Run URIs to get plain hostnames for uptime checks
  agent_core_host  = replace(google_cloud_run_v2_service.agent_core.uri, "https://", "")
  rag_host         = replace(google_cloud_run_v2_service.rag_service.uri, "https://", "")
  governance_host  = replace(google_cloud_run_v2_service.governance.uri, "https://", "")
  llm_gateway_host = replace(google_cloud_run_v2_service.llm_gateway.uri, "https://", "")
}

# ── Notification channel ──────────────────────────────────────────────────────

resource "google_monitoring_notification_channel" "email" {
  display_name = "Agentic AI Platform Alerts"
  type         = "email"
  project      = var.project_id

  labels = {
    email_address = var.alert_email
  }

  depends_on = [google_project_service.apis]
}

# ── Uptime checks ─────────────────────────────────────────────────────────────

resource "google_monitoring_uptime_check_config" "agent_core" {
  display_name = "agent-core /health"
  timeout      = "10s"
  period       = "60s"
  project      = var.project_id

  http_check {
    path         = "/health"
    port         = 443
    use_ssl      = true
    validate_ssl = true
  }

  monitored_resource {
    type = "uptime_url"
    labels = {
      project_id = var.project_id
      host       = local.agent_core_host
    }
  }

  depends_on = [google_project_service.apis]
}

resource "google_monitoring_uptime_check_config" "rag_service" {
  display_name = "rag-service /health"
  timeout      = "10s"
  period       = "60s"
  project      = var.project_id

  http_check {
    path         = "/health"
    port         = 443
    use_ssl      = true
    validate_ssl = true
  }

  monitored_resource {
    type = "uptime_url"
    labels = {
      project_id = var.project_id
      host       = local.rag_host
    }
  }

  depends_on = [google_project_service.apis]
}

resource "google_monitoring_uptime_check_config" "governance" {
  display_name = "governance /health"
  timeout      = "10s"
  period       = "60s"
  project      = var.project_id

  http_check {
    path         = "/health"
    port         = 443
    use_ssl      = true
    validate_ssl = true
  }

  monitored_resource {
    type = "uptime_url"
    labels = {
      project_id = var.project_id
      host       = local.governance_host
    }
  }

  depends_on = [google_project_service.apis]
}

resource "google_monitoring_uptime_check_config" "llm_gateway" {
  display_name = "llm-gateway /health"
  timeout      = "10s"
  period       = "60s"
  project      = var.project_id

  http_check {
    path         = "/health"
    port         = 443
    use_ssl      = true
    validate_ssl = true
  }

  monitored_resource {
    type = "uptime_url"
    labels = {
      project_id = var.project_id
      host       = local.llm_gateway_host
    }
  }

  depends_on = [google_project_service.apis]
}

# ── Alert: service down ───────────────────────────────────────────────────────

resource "google_monitoring_alert_policy" "service_down" {
  display_name = "Service Down — Agentic AI Platform"
  combiner     = "OR"
  project      = var.project_id
  enabled      = true

  conditions {
    display_name = "agent-core uptime check failing"
    condition_threshold {
      filter          = "resource.type=\"uptime_url\" AND metric.type=\"monitoring.googleapis.com/uptime_check/check_passed\" AND resource.labels.host=\"${local.agent_core_host}\""
      duration        = "120s"
      comparison      = "COMPARISON_LT"
      threshold_value = 1
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_NEXT_OLDER"
        cross_series_reducer = "REDUCE_COUNT_TRUE"
      }
    }
  }

  conditions {
    display_name = "rag-service uptime check failing"
    condition_threshold {
      filter          = "resource.type=\"uptime_url\" AND metric.type=\"monitoring.googleapis.com/uptime_check/check_passed\" AND resource.labels.host=\"${local.rag_host}\""
      duration        = "120s"
      comparison      = "COMPARISON_LT"
      threshold_value = 1
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_NEXT_OLDER"
        cross_series_reducer = "REDUCE_COUNT_TRUE"
      }
    }
  }

  conditions {
    display_name = "governance uptime check failing"
    condition_threshold {
      filter          = "resource.type=\"uptime_url\" AND metric.type=\"monitoring.googleapis.com/uptime_check/check_passed\" AND resource.labels.host=\"${local.governance_host}\""
      duration        = "120s"
      comparison      = "COMPARISON_LT"
      threshold_value = 1
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_NEXT_OLDER"
        cross_series_reducer = "REDUCE_COUNT_TRUE"
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.email.id]

  alert_strategy {
    auto_close = "1800s"
  }

  documentation {
    content   = "One or more Agentic AI Platform services failed health checks for 2+ minutes. Check Cloud Run logs and service status."
    mime_type = "text/markdown"
  }
}

# ── Alert: high error rate on agent-core ─────────────────────────────────────

resource "google_monitoring_alert_policy" "agent_core_error_rate" {
  display_name = "agent-core High Error Rate (5xx)"
  combiner     = "OR"
  project      = var.project_id
  enabled      = true

  conditions {
    display_name = "5xx error rate > 5%"
    condition_threshold {
      filter     = "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"agent-core\" AND metric.type=\"run.googleapis.com/request_count\" AND metric.labels.response_code_class=\"5xx\""
      duration   = "300s"
      comparison = "COMPARISON_GT"
      threshold_value = 5
      aggregations {
        alignment_period     = "60s"
        per_series_aligner   = "ALIGN_RATE"
        cross_series_reducer = "REDUCE_SUM"
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.email.id]

  alert_strategy {
    auto_close = "1800s"
  }

  documentation {
    content   = "agent-core is returning more than 5 HTTP 5xx errors per minute. Check agent-core logs for stack traces."
    mime_type = "text/markdown"
  }
}

# ── Alert: high latency on agent-core ────────────────────────────────────────

resource "google_monitoring_alert_policy" "agent_core_latency" {
  display_name = "agent-core High Latency (p95 > 30s)"
  combiner     = "OR"
  project      = var.project_id
  enabled      = true

  conditions {
    display_name = "p95 latency > 30s"
    condition_threshold {
      filter     = "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"agent-core\" AND metric.type=\"run.googleapis.com/request_latencies\""
      duration   = "300s"
      comparison = "COMPARISON_GT"
      threshold_value = 30000  # milliseconds
      aggregations {
        alignment_period     = "60s"
        per_series_aligner   = "ALIGN_PERCENTILE_95"
        cross_series_reducer = "REDUCE_MAX"
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.email.id]

  alert_strategy {
    auto_close = "3600s"
  }

  documentation {
    content   = "agent-core p95 latency exceeded 30 seconds. LLM calls or RAG retrieval may be slow. Check LLM gateway and rag-service logs."
    mime_type = "text/markdown"
  }
}

# ── Alert: instance count spike ───────────────────────────────────────────────

resource "google_monitoring_alert_policy" "instance_spike" {
  display_name = "Cloud Run Instance Spike (> 10 instances)"
  combiner     = "OR"
  project      = var.project_id
  enabled      = true

  conditions {
    display_name = "agent-core instances > 10"
    condition_threshold {
      filter     = "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"agent-core\" AND metric.type=\"run.googleapis.com/container/instance_count\""
      duration   = "120s"
      comparison = "COMPARISON_GT"
      threshold_value = 10
      aggregations {
        alignment_period     = "60s"
        per_series_aligner   = "ALIGN_MAX"
        cross_series_reducer = "REDUCE_MAX"
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.email.id]

  alert_strategy {
    auto_close = "3600s"
  }

  documentation {
    content   = "agent-core scaled beyond 10 instances. Possible traffic spike or runaway loop. Review request patterns."
    mime_type = "text/markdown"
  }
}

# ── Alert: governance policy violations spike ─────────────────────────────────

resource "google_monitoring_alert_policy" "policy_violations" {
  display_name = "Governance Policy Violations Spike"
  combiner     = "OR"
  project      = var.project_id
  enabled      = true

  conditions {
    display_name = "Policy violations > 10/min"
    condition_threshold {
      filter          = "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"agent-core\" AND metric.type=\"logging.googleapis.com/user/${google_logging_metric.policy_violations.name}\""
      duration        = "120s"
      comparison      = "COMPARISON_GT"
      threshold_value = 10
      aggregations {
        alignment_period     = "60s"
        per_series_aligner   = "ALIGN_RATE"
        cross_series_reducer = "REDUCE_SUM"
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.email.id]

  alert_strategy {
    auto_close = "1800s"
  }

  documentation {
    content   = "Unusually high governance policy violations detected. Possible security probe or misconfigured client. Check governance logs."
    mime_type = "text/markdown"
  }
}

# ── Log-based metrics ─────────────────────────────────────────────────────────

resource "google_logging_metric" "skill_invocations" {
  name    = "agentic_ai/skill_invocations"
  project = var.project_id

  filter = "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"agent-core\" AND jsonPayload.event_type=\"agent.run.start\" AND jsonPayload.skill!=\"\""

  metric_descriptor {
    metric_kind = "DELTA"
    value_type  = "INT64"
    unit        = "1"
    display_name = "Skill Invocations"
    labels {
      key         = "skill"
      value_type  = "STRING"
      description = "Name of the skill invoked"
    }
  }

  label_extractors = {
    "skill" = "EXTRACT(jsonPayload.skill)"
  }
}

resource "google_logging_metric" "policy_violations" {
  name    = "agentic_ai/policy_violations"
  project = var.project_id

  filter = "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"agent-core\" AND textPayload=~\"Access denied\""

  metric_descriptor {
    metric_kind  = "DELTA"
    value_type   = "INT64"
    unit         = "1"
    display_name = "Governance Policy Violations"
  }
}

resource "google_logging_metric" "rag_ingestion_failures" {
  name    = "agentic_ai/rag_ingestion_failures"
  project = var.project_id

  filter = "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"rag-service\" AND severity=ERROR"

  metric_descriptor {
    metric_kind  = "DELTA"
    value_type   = "INT64"
    unit         = "1"
    display_name = "RAG Ingestion Failures"
  }
}

# ── Monitoring dashboard ──────────────────────────────────────────────────────

resource "google_monitoring_dashboard" "platform" {
  project        = var.project_id
  dashboard_json = jsonencode({
    displayName = "Agentic AI Platform"
    mosaicLayout = {
      columns = 12
      tiles = [
        # ── Request rate — agent-core ──
        {
          width  = 6
          height = 4
          widget = {
            title = "agent-core — Request Rate"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"agent-core\" AND metric.type=\"run.googleapis.com/request_count\""
                    aggregation = {
                      alignmentPeriod    = "60s"
                      perSeriesAligner   = "ALIGN_RATE"
                      crossSeriesReducer = "REDUCE_SUM"
                      groupByFields      = ["metric.labels.response_code_class"]
                    }
                  }
                }
                plotType = "LINE"
              }]
            }
          }
        },
        # ── Latency — agent-core ──
        {
          xPos   = 6
          width  = 6
          height = 4
          widget = {
            title = "agent-core — Latency (p50 / p95)"
            xyChart = {
              dataSets = [
                {
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"agent-core\" AND metric.type=\"run.googleapis.com/request_latencies\""
                      aggregation = {
                        alignmentPeriod  = "60s"
                        perSeriesAligner = "ALIGN_PERCENTILE_50"
                        crossSeriesReducer = "REDUCE_MAX"
                      }
                    }
                  }
                  plotType    = "LINE"
                  legendTemplate = "p50"
                },
                {
                  timeSeriesQuery = {
                    timeSeriesFilter = {
                      filter = "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"agent-core\" AND metric.type=\"run.googleapis.com/request_latencies\""
                      aggregation = {
                        alignmentPeriod  = "60s"
                        perSeriesAligner = "ALIGN_PERCENTILE_95"
                        crossSeriesReducer = "REDUCE_MAX"
                      }
                    }
                  }
                  plotType    = "LINE"
                  legendTemplate = "p95"
                }
              ]
            }
          }
        },
        # ── Instance count ──
        {
          yPos   = 4
          width  = 6
          height = 4
          widget = {
            title = "Cloud Run — Active Instances"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "resource.type=\"cloud_run_revision\" AND metric.type=\"run.googleapis.com/container/instance_count\""
                    aggregation = {
                      alignmentPeriod    = "60s"
                      perSeriesAligner   = "ALIGN_MAX"
                      crossSeriesReducer = "REDUCE_MAX"
                      groupByFields      = ["resource.labels.service_name"]
                    }
                  }
                }
                plotType = "LINE"
              }]
            }
          }
        },
        # ── Skill invocations ──
        {
          xPos   = 6
          yPos   = 4
          width  = 6
          height = 4
          widget = {
            title = "Skill Invocations by Skill"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "resource.type=\"cloud_run_revision\" AND metric.type=\"logging.googleapis.com/user/${google_logging_metric.skill_invocations.name}\""
                    aggregation = {
                      alignmentPeriod    = "60s"
                      perSeriesAligner   = "ALIGN_RATE"
                      crossSeriesReducer = "REDUCE_SUM"
                      groupByFields      = ["metric.labels.skill"]
                    }
                  }
                }
                plotType = "STACKED_BAR"
              }]
            }
          }
        },
        # ── Policy violations ──
        {
          yPos   = 8
          width  = 6
          height = 4
          widget = {
            title = "Governance Policy Violations"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "resource.type=\"cloud_run_revision\" AND metric.type=\"logging.googleapis.com/user/${google_logging_metric.policy_violations.name}\""
                    aggregation = {
                      alignmentPeriod    = "60s"
                      perSeriesAligner   = "ALIGN_RATE"
                      crossSeriesReducer = "REDUCE_SUM"
                    }
                  }
                }
                plotType = "LINE"
              }]
            }
          }
        },
        # ── RAG ingestion failures ──
        {
          xPos   = 6
          yPos   = 8
          width  = 6
          height = 4
          widget = {
            title = "RAG Ingestion Failures"
            xyChart = {
              dataSets = [{
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "resource.type=\"cloud_run_revision\" AND metric.type=\"logging.googleapis.com/user/${google_logging_metric.rag_ingestion_failures.name}\""
                    aggregation = {
                      alignmentPeriod    = "60s"
                      perSeriesAligner   = "ALIGN_RATE"
                      crossSeriesReducer = "REDUCE_SUM"
                    }
                  }
                }
                plotType = "LINE"
              }]
            }
          }
        }
      ]
    }
  })

  depends_on = [
    google_project_service.apis,
    google_logging_metric.skill_invocations,
    google_logging_metric.policy_violations,
    google_logging_metric.rag_ingestion_failures,
  ]
}
