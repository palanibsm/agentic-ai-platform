# Agentic AI Platform — Continuation Context

> **Purpose:** Paste this file into a new chat to resume development with full context.  
> **Last updated:** 2026-06-04 | **Current status:** Phase 2 complete, Phase 3 next.

---

## 1. Who You Are Talking To

- **Name:** Senthil (AI Architect, Singapore bank)
- **Email:** stels.karthik@gmail.com / senthilbaskaran@ocbc.com
- **Stack preference:** Python (experienced), concise responses only

---

## 2. Project Summary

Enterprise Agentic AI Platform for a Singapore bank. Built on LangGraph, Claude Agent SDK, LiteLLM, and GCP Cloud Run. Six-role RBAC model. Multi-tenant (one agent-core per App DevOps team). Prototype-grade infra (~$2–5/month).

**Repo location:** `C:\code\agentic-ai\AI Platform`

---

## 3. GCP Project Details

| Key | Value |
|-----|-------|
| Project ID | `ai-agent-project-497604` |
| Project Number | `588333972270` |
| Region | `us-central1` |
| Artifact Registry | `us-central1-docker.pkg.dev/ai-agent-project-497604/agentic-ai` |
| TF State Bucket | `gs://ai-agent-project-497604-tf-state/agentic-ai/state/` |
| Service Account | `agentic-ai-runner@ai-agent-project-497604.iam.gserviceaccount.com` |

**PowerShell env vars to set at start of every session:**
```powershell
$PROJECT = "ai-agent-project-497604"
$REG     = "us-central1-docker.pkg.dev/ai-agent-project-497604/agentic-ai"
```

---

## 4. Live Service URLs (Terraform outputs)

| Service | URL |
|---------|-----|
| Portal (Next.js) | https://portal-hcm6dgvcaq-uc.a.run.app |
| Agent Core | https://agent-core-hcm6dgvcaq-uc.a.run.app |
| Governance | https://governance-hcm6dgvcaq-uc.a.run.app |
| LLM Gateway | https://llm-gateway-hcm6dgvcaq-uc.a.run.app |
| RAG Service | https://rag-service-hcm6dgvcaq-uc.a.run.app |
| Qdrant | https://qdrant-hcm6dgvcaq-uc.a.run.app |
| IDE Chat | https://ide-chat-hcm6dgvcaq-uc.a.run.app |

---

## 5. Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              UNIFIED PORTAL (Next.js 14 + shadcn/ui)        │
│   Role-based sidebar, Dashboard, Chat, Marketplace,         │
│   Admin, Observability                                       │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTPS + NextAuth.js (Google OAuth)
┌────────────────────────▼────────────────────────────────────┐
│                  SHARED CORE PLATFORM                        │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ LLM Gateway │  │  Governance  │  │  Agent Registry  │   │
│  │ (LiteLLM)   │  │  + RBAC      │  │  + Marketplace   │   │
│  └─────────────┘  └──────────────┘  └──────────────────┘   │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ RAG Service │  │ Memory Svc   │  │   MCP Hub        │   │
│  │ (Qdrant)    │  │ (Redis +     │  │ (Confluence,     │   │
│  │             │  │  Firestore)  │  │  Jira, GitHub,   │   │
│  └─────────────┘  └──────────────┘  │  DB, REST)       │   │
│                                      └──────────────────┘   │
│  ┌─────────────┐  ┌──────────────┐                          │
│  │  Trace Svc  │  │  Workflow    │                          │
│  │ (ClickHouse)│  │  Engine      │                          │
│  └─────────────┘  └──────────────┘                          │
└─────────────────────────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│            ISOLATED AGENT ENVIRONMENTS                       │
│   one agent-core Cloud Run service per App DevOps team       │
│   named: agent-core-{team-name}, TEAM_ID env var set        │
└─────────────────────────────────────────────────────────────┘
```

---

## 6. Technology Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14 + shadcn/ui + Tailwind CSS |
| Auth | NextAuth.js with Google OAuth |
| API services | FastAPI (Python 3.11) |
| Agent runtime | LangGraph + Claude Agent SDK |
| LLM models | Claude, GPT-4o, Gemini, Llama via LiteLLM |
| Vector store | Qdrant on Cloud Run (GCS volume) |
| Session memory | Redis on Cloud Run |
| Long-term memory + Registry + Workflows | SQLite on Cloud Run (prototype) |
| Traces + Cost | ClickHouse on Cloud Run (Phase 7) |
| MCP hub | FastAPI + MCP protocol adapters |
| Infra | GCP Cloud Run + Terraform |
| CI/CD | GitHub Actions + Cloud Build |

---

## 7. Repo Structure

```
AI Platform/
├── apps/
│   ├── portal/          # Next.js 14 unified portal
│   │   └── src/
│   │       ├── app/     # pages: /, /chat, /marketplace, /admin, /observability, /agents
│   │       ├── components/  # sidebar.tsx, header.tsx, user-context.tsx, providers.tsx
│   │       └── lib/     # roles.ts (UserProfile, UserRole, NavItem), api.ts, auth.ts
│   └── ide-chat/        # Developer chat UI
├── services/
│   ├── governance/      # RBAC, policy engine, teams, users, A2A, audit
│   │   └── src/
│   │       ├── main.py
│   │       ├── policy/engine.py   # 6-role RBAC, MAS TRM content scanning
│   │       ├── db/connection.py   # asyncpg / SQLite pool
│   │       ├── teams/router.py    # GET/POST/PUT/DELETE /teams
│   │       ├── users/router.py    # GET/POST /users, PUT /users/{id}/role
│   │       └── a2a/router.py      # marketplace, register, check, whitelist
│   ├── agent-core/      # LangGraph orchestration
│   │   └── src/
│   │       ├── main.py            # /run, /health, /skills endpoints
│   │       ├── graph/agent.py     # LangGraph graph
│   │       └── skills/registry.py
│   ├── llm-gateway/     # LiteLLM proxy
│   └── rag-service/     # Qdrant ingestion + search
├── infra/
│   └── terraform/
│       ├── cloud_run.tf   # all Cloud Run services
│       ├── variables.tf   # project_id, region, secrets
│       ├── outputs.tf     # all service URLs
│       ├── cloudsql.tf    # PostgreSQL 16 (Cloud SQL)
│       ├── redis.tf       # Redis on Cloud Run
│       ├── secrets.tf     # Secret Manager entries
│       ├── pubsub.tf      # audit-events topic
│       └── workflows.tf   # approval-gate, rag-ingestion Cloud Workflows
├── docker/
│   └── docker-compose.yml
├── CLAUDE.md
└── CONTEXT.md           # ← this file
```

---

## 8. Six-Role RBAC Model

Defined in `services/governance/src/policy/engine.py`. Must stay in sync with `apps/portal/src/lib/roles.ts`.

| Role | Level | What they can do |
|------|-------|-----------------|
| `business-user` | 0 | Chat with agents, view own history |
| `ba` | 1 | Submit requirements via structured forms, view capabilities |
| `business-ops` | 2 | Configure/run workflows, trigger automations, advanced chat |
| `app-devops` | 3 | Deploy/manage their team's agents, consume MCPs, A2A requests |
| `ai-devops` | 4 | Full platform: services, models, MCPs, governance, RBAC |
| `ai-architect` | 5 | Read-only across everything (cannot mutate) |

**Key rules:**
- `ai-architect` is level 5 but read-only — no mutations
- `app-devops` is team-scoped — cannot access other teams' resources
- Cross-team access denied unless `ai-devops` or `ai-architect`
- MAS TRM content scanning runs on every prompt (jailbreak, PII, credential leak patterns)

**Model access:**
- `claude-sonnet`, `claude-haiku`, `gpt-4o-mini`, `gemini-flash` → all roles
- `gpt-4o`, `gemini-pro` → `app-devops`+
- `claude-opus`, `llama3` → `ai-devops` only

---

## 9. Key API Contracts

### Governance service (`https://governance-hcm6dgvcaq-uc.a.run.app`)

```
GET  /health
POST /policy/check          { user_role, skill?, model?, prompt?, operation?, team_id?, target_team_id? }
POST /audit/events          { event_type, user_id, session_id, payload }
GET  /audit/events?event_type=&user_id=&limit=
POST /usage/record          { user_id, model, skill?, team_id?, input_tokens, output_tokens }
GET  /usage/report

# Teams
GET    /teams
POST   /teams               { name, description? }
PUT    /teams/{id}
DELETE /teams/{id}

# Users
GET  /users
POST /users                 { email, role, team_id? }
PUT  /users/{id}/role       { role }
GET  /users/by-email/{email}

# A2A / Agent Registry
GET    /a2a/marketplace                        list all registered agents
POST   /a2a/agents          { name, team_id, description, capabilities[], endpoint_url }
POST   /a2a/check           { caller_team_id, target_agent_id }
POST   /a2a/whitelist       { caller_team_id, target_agent_id }
DELETE /a2a/whitelist/{caller_team_id}/{target_agent_id}
```

### Agent Core (`https://agent-core-hcm6dgvcaq-uc.a.run.app`)

```
GET  /health
GET  /skills
POST /run   { query, user_id, user_role, team_id?, skill?, session_id? }
            → { answer, session_id, tool_calls_made, team_id }
```

---

## 10. Portal Pages (Phase 2)

| Route | Roles | Description |
|-------|-------|-------------|
| `/` | all | Role-adapted dashboard |
| `/chat` | all | Agent chat with skill selector |
| `/marketplace` | all | Browse registered agents |
| `/agents` | ai-architect, ai-devops, app-devops | Agent management |
| `/admin` | ai-devops | Teams + users management |
| `/observability` | ai-architect, ai-devops, app-devops | Audit events + metrics |
| `/workflows` | business-ops | Workflow management (placeholder) |
| `/requirements` | ba | Requirements submission (placeholder) |
| `/costs` | ai-architect, ai-devops | Cost & usage (placeholder) |
| `/models` | ai-devops | Model management (placeholder) |
| `/mcp` | ai-devops, app-devops | MCP hub (placeholder) |

**Sidebar navigation** is role-adapted via `getNavItems(role)` in `lib/roles.ts`.  
**Auth:** NextAuth.js Google OAuth. Session email is resolved to `UserProfile` via `GET /users/by-email/{email}` on governance service.

---

## 11. UserProfile Type (portal)

```typescript
// apps/portal/src/lib/roles.ts
export interface UserProfile {
  email: string;
  role: UserRole;
  team_id: string | null;
  team_name: string | null;
  display_name: string | null;
  registered: boolean;
}
```
Note: No `image` field. Avatar is always an initial letter fallback.

---

## 12. Infrastructure Notes

- **All services:** Cloud Run, allow-unauthenticated (auth handled at app layer)
- **Portal:** max 1 instance (prevents NextAuth OAuth state mismatch)
- **Governance DB:** SQLite on Cloud Run (`sqlite+aiosqlite:////app/data/governance.db`) — prototype only
- **Qdrant storage:** GCS volume mount at `/qdrant/storage`
- **Secrets in Secret Manager:** `anthropic-api-key`, `litellm-master-key`, `openai-api-key`, `google-client-id`, `google-client-secret`, `nextauth-secret`
- **Pub/Sub topic:** `audit-events` — all agent actions must emit here
- **Cloud Workflows:** `approval-gate`, `rag-ingestion`

**Build commands:**
```powershell
# Build and push a service image
gcloud builds submit apps/portal --tag="$REG/portal:latest" --project=$PROJECT
gcloud builds submit services/governance --tag="$REG/governance:latest" --project=$PROJECT
gcloud builds submit services/agent-core --tag="$REG/agent-core:latest" --project=$PROJECT

# Apply Terraform
cd infra/terraform
terraform apply                                         # all resources
terraform apply -target="google_cloud_run_v2_service.portal"  # single service

# Force-unlock stale TF state lock
terraform force-unlock <LOCK_ID>
```

---

## 13. Phase Progress

| Phase | What | Status |
|-------|------|--------|
| Phase 1 | 6-role RBAC, governance service, PostgreSQL/SQLite schema, team isolation, A2A access control | ✅ Done |
| Phase 2 | Unified portal (Next.js + shadcn/ui), role-based sidebar, dashboard, chat, marketplace, admin, observability | ✅ Done |
| Phase 3 | Agent registry + marketplace UI + A2A whitelist approval flow | ⏳ Next |
| Phase 4 | Memory service (Redis session + Firestore/SQLite long-term + shared team memory) | Pending |
| Phase 5 | MCP hub (Confluence, Jira, GitHub, REST, DB connectors) | Pending |
| Phase 6 | Workflow engine + Business Ops form builder + approval flows | Pending |
| Phase 7 | Trace service + cost tracking + ClickHouse + observability dashboard | Pending |
| Phase 8 | Multi-model support (Gemini, Llama) + model lifecycle UI | Pending |

---

## 14. Phase 3 — What Needs to Be Built

**Goal:** Fully functional agent registry and marketplace with A2A access request/approval flow.

### Backend (governance — APIs already exist, may need polish)
- `POST /a2a/agents` — register an agent
- `GET /a2a/marketplace` — list agents with capabilities
- `POST /a2a/whitelist` / `DELETE /a2a/whitelist` — grant/revoke A2A access
- `POST /a2a/check` — runtime access check (called by agent-core before agent-to-agent call)

### Portal changes
1. **`/marketplace`** — upgrade to card grid:
   - Agent cards: name, team, description, capability badges, model
   - Filters: by skill, model, team
   - "Request A2A Access" button → calls `POST /a2a/whitelist` → pending approval
2. **`/agents`** (App DevOps only) — full CRUD:
   - List team's registered agents
   - Register new agent form: name, description, capabilities[], endpoint_url
   - Calls `POST /a2a/agents`
3. **`/admin`** (AI DevOps) — add "Pending A2A Requests" section:
   - List pending whitelist requests
   - Approve / Deny buttons

### Agent Core change
- Before invoking another agent, call `POST /a2a/check` on governance
- Emit audit event on every A2A call with `event_type: "a2a_call"`

### Suggested build order
1. Enhance `/marketplace` UI
2. Add `/agents` page with registration form
3. Wire "Request A2A Access" → whitelist API
4. Add pending approvals to `/admin`
5. Add `a2a/check` in agent-core's inter-agent call path

---

## 15. Common Issues & Fixes Encountered

| Issue | Fix |
|-------|-----|
| `$PROJECT` / `$REG` empty in PowerShell | Set them manually: `$PROJECT = "ai-agent-project-497604"` |
| Terraform state lock (conditionNotMet) | `terraform force-unlock <LOCK_ID>` |
| Artifact Registry "not found" on first push | Create first: `gcloud artifacts repositories create agentic-ai --repository-format=docker --location=asia-southeast1 --project=$PROJECT` |
| TypeScript build error: `Property 'image' does not exist on UserProfile` | Removed `profile.image` branch in `sidebar.tsx` — use initial letter avatar only |

---

## 16. Conventions

- Every Python service: `GET /health` endpoint
- Every agent action: emit to `audit-events` Pub/Sub topic with `team_id`
- PII/DLP check via governance `/policy/check` before every LLM call
- Secrets: `.env` locally, GCP Secret Manager on Cloud Run
- All skills: `SKILL.md` as entry point in `skills/<skill-name>/SKILL.md`
- Governance policy engine and portal `roles.ts` must stay in sync
