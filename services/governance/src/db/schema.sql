-- Agentic AI Platform — Governance DB Schema (SQLite)
-- Idempotent: uses CREATE TABLE IF NOT EXISTS throughout
-- Migration to PostgreSQL: change UUID DEFAULT to gen_random_uuid(),
--   TEXT dates to TIMESTAMPTZ, and ? params to $1/$2 in routers.

-- ── Teams ─────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS teams (
    id           TEXT PRIMARY KEY,
    name         TEXT UNIQUE NOT NULL,
    display_name TEXT NOT NULL,
    description  TEXT,
    team_type    TEXT NOT NULL CHECK (team_type IN ('ai-devops','app-devops','business','platform')),
    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_teams_name ON teams(name);

-- ── Users ─────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id           TEXT PRIMARY KEY,
    email        TEXT UNIQUE NOT NULL,
    display_name TEXT,
    role         TEXT NOT NULL CHECK (role IN (
                     'ai-architect','ai-devops','app-devops',
                     'business-ops','ba','business-user'
                 )),
    team_id      TEXT REFERENCES teams(id) ON DELETE SET NULL,
    is_active    INTEGER NOT NULL DEFAULT 1,
    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_users_email   ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_team_id ON users(team_id);

-- ── Agent registrations ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS agent_registrations (
    id            TEXT PRIMARY KEY,
    team_id       TEXT NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    agent_name    TEXT NOT NULL,
    display_name  TEXT NOT NULL,
    description   TEXT,
    skills        TEXT NOT NULL DEFAULT '[]',  -- JSON array stored as TEXT
    model         TEXT NOT NULL DEFAULT 'claude-sonnet',
    service_url   TEXT,
    is_public     INTEGER NOT NULL DEFAULT 0,
    is_active     INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at    TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(team_id, agent_name)
);

CREATE INDEX IF NOT EXISTS idx_agents_team_id   ON agent_registrations(team_id);
CREATE INDEX IF NOT EXISTS idx_agents_is_public ON agent_registrations(is_public);

-- ── A2A whitelist ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS a2a_whitelist (
    id                TEXT PRIMARY KEY,
    requester_team_id TEXT NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    target_agent_id   TEXT NOT NULL REFERENCES agent_registrations(id) ON DELETE CASCADE,
    granted_by        TEXT NOT NULL,
    created_at        TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(requester_team_id, target_agent_id)
);

CREATE INDEX IF NOT EXISTS idx_a2a_requester ON a2a_whitelist(requester_team_id);
CREATE INDEX IF NOT EXISTS idx_a2a_target    ON a2a_whitelist(target_agent_id);

-- ── Audit log ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS audit_log (
    id            TEXT PRIMARY KEY,
    event_type    TEXT NOT NULL,
    user_email    TEXT,
    user_role     TEXT,
    team_id       TEXT,
    resource_type TEXT,
    resource_id   TEXT,
    details       TEXT,  -- JSON stored as TEXT
    ip_address    TEXT,
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_audit_event_type ON audit_log(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_created_at ON audit_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_user_email ON audit_log(user_email);
