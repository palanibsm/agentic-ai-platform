# ── Cloud SQL — PostgreSQL 16 ─────────────────────────────────────────────────
# Used by: governance service (teams, users, agent registry, A2A whitelist, audit log)
#
# Instance is private (no public IP) — governance Cloud Run connects via
# Cloud SQL Auth Proxy sidecar or the built-in Cloud Run Cloud SQL connector.

resource "google_sql_database_instance" "postgres" {
  name             = "agentic-ai-postgres"
  database_version = "POSTGRES_16"
  region           = var.region
  project          = var.project_id

  settings {
    tier              = "db-f1-micro"   # cheapest tier — fine for prototype
    availability_type = "ZONAL"         # single zone — upgrade to REGIONAL for prod
    disk_autoresize   = true
    disk_size         = 10              # GB

    backup_configuration {
      enabled            = true
      start_time         = "02:00"
      binary_log_enabled = false        # not supported on PostgreSQL
    }

    ip_configuration {
      ipv4_enabled = true               # required for Cloud Run connector
      # In production: set to false and use private IP + VPC
    }

    database_flags {
      name  = "max_connections"
      value = "100"
    }
  }

  deletion_protection = false           # set to true in production

  depends_on = [google_project_service.apis]
}

resource "google_sql_database" "governance_db" {
  name     = "governance"
  instance = google_sql_database_instance.postgres.name
  project  = var.project_id
}

resource "google_sql_user" "governance_user" {
  name     = "governance"
  instance = google_sql_database_instance.postgres.name
  password = random_password.db_password.result
  project  = var.project_id
}

resource "random_password" "db_password" {
  length  = 32
  special = false
}

# Store DB password in Secret Manager
resource "google_secret_manager_secret" "db_password" {
  secret_id = "governance-db-password"
  project   = var.project_id

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_version" "db_password" {
  secret      = google_secret_manager_secret.db_password.id
  secret_data = random_password.db_password.result
}

# Grant runner SA access to the DB secret
resource "google_secret_manager_secret_iam_member" "db_password_accessor" {
  project   = var.project_id
  secret_id = google_secret_manager_secret.db_password.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${local.sa_email}"
}

# Grant runner SA Cloud SQL client role
resource "google_project_iam_member" "cloudsql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${local.sa_email}"

  depends_on = [google_service_account.runner]
}

# ── Outputs ───────────────────────────────────────────────────────────────────

locals {
  # Cloud Run DATABASE_URL using Cloud SQL connector
  # Format: postgresql://user:password@/dbname?host=/cloudsql/project:region:instance
  db_connection_name = google_sql_database_instance.postgres.connection_name
  database_url       = "postgresql://governance:${random_password.db_password.result}@/governance?host=/cloudsql/${local.db_connection_name}"
}
