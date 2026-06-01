# ── Cloud SQL ─────────────────────────────────────────────────────────────────
# DISABLED for prototype — using SQLite embedded in governance service instead.
# Re-enable for production by restoring Cloud SQL resources.
#
# SQLite DB file is stored at /app/data/governance.db inside the container.
# Data is ephemeral (resets on Cloud Run restart) — acceptable for prototype.
# Migration path to Cloud SQL: change DATABASE_URL env var, no code changes needed.
