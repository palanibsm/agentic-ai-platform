# Agentic AI Platform — Testing Guide

## Quick Start

| Interface | Production | Local |
|---|---|---|
| **Portal** (business users) | https://portal-hcm6dgvcaq-uc.a.run.app | http://localhost:3000 |
| **IDE Chat** (developers) | https://ide-chat-hcm6dgvcaq-uc.a.run.app | http://localhost:3001 |

---

## The Interfaces

### Portal
- **Role selector** — controls what the agent is allowed to do
- **Skill selector** — activates a specialised agent persona
- **Clear button** — resets the conversation session
- **Tool call badges** — appear below each response (e.g. `retrieve`, `format_banking_response`)

### IDE Chat (Developer Interface)
- **Dark IDE theme** — VS Code-style layout
- **Session history sidebar** — past conversations grouped by date, stored in browser
- **Code highlighting** — syntax-highlighted code blocks with copy button
- **Role + Skill selectors** — same as portal, in the top bar
- **Prompt suggestion chips** — quick-start prompts on the empty state
- **Keyboard shortcut** — Enter to send, Shift+Enter for new line

---

## Test Scenarios

### Test 1 — Basic Identity Check
**Interface:** Either | **Role:** Developer | **Skill:** None

> `Hi, who are you?`

**Expected:** Agent introduces itself as an enterprise AI assistant for a Singapore bank, lists capabilities (RAG, compliance, MAS TRM), and states operating boundaries (no PII, auditable).

**Tool badges expected:** `format_banking_response`

---

### Test 2 — RAG Document Retrieval
**Interface:** Either | **Role:** Developer | **Skill:** None

> `What documents do we have about cloud architecture?`

**Expected:** Agent calls `retrieve` (badge appears), returns chunked content from ingested Qdrant documents with source citations and relevance scores.

**Tool badges expected:** `retrieve`, `format_banking_response`

> **Note:** Documents must be ingested first. See [Ingesting Documents](#ingesting-documents) below.

---

### Test 3 — RBAC Block (Developer → Compliance Skill)
**Interface:** Either | **Role:** Developer | **Skill:** Banking Compliance

> `What are our data residency obligations under MAS?`

**Expected:** `403 Access denied — skill 'banking-compliance' requires role 'architect' (current: 'developer')`

---

### Test 4 — RBAC Allow (Architect → Compliance Skill)
**Interface:** Either | **Role:** Architect | **Skill:** Banking Compliance

> `What are our data residency obligations under MAS?`

**Expected:** Agent retrieves relevant documents and answers with MAS TRM-grounded response. Source citations included.

**Tool badges expected:** `retrieve`, `format_banking_response`

---

### Test 5 — Session Continuity (Multi-turn)
**Interface:** Either | **Role:** Developer | **Skill:** None

Turn 1:
> `My name is Senthil and I work in the cloud team.`

Turn 2 (same session — do NOT press Clear or start a new chat):
> `What did I just tell you about myself?`

**Expected:** Agent correctly recalls name and team from the previous turn.

---

### Test 6 — MAS TRM Query with RAG
**Interface:** Either | **Role:** Architect | **Skill:** Banking Compliance

> `What are the MAS TRM requirements for AI model governance?`

**Expected:** Detailed response grounded in retrieved documents covering model risk, explainability, and audit requirements.

**Tool badges expected:** `retrieve`, `retrieve`, `format_banking_response`

---

### Test 7 — RBAC Block (Developer → Incident Response Skill)
**Interface:** Either | **Role:** Developer | **Skill:** Incident Response

> `Help me with a production incident`

**Expected:** `403 Access denied — skill 'incident-response' requires role 'senior-engineer' (current: 'developer')`

---

### Test 8 — Code Highlighting (IDE Chat specific)
**Interface:** IDE Chat only | **Role:** Developer | **Skill:** Secure Coding

> `Show me a Python example of how to hash a password securely`

**Expected:** Response contains a syntax-highlighted Python code block with a copy button. Hovering the code block reveals the "copy" button in the top-right corner.

---

### Test 9 — Session History (IDE Chat specific)
**Interface:** IDE Chat only

1. Send a few messages in one session
2. Click **New Chat** in the top bar
3. Send messages in the new session
4. Click the first session in the left sidebar

**Expected:** The sidebar shows both sessions grouped under "Today". Clicking a past session restores its full message history. The session ID shown at the bottom of the input area changes.

---

### Test 10 — Audit Trail Verification
After running any of the above tests, verify audit events are flowing to Pub/Sub:

**Cloud Run logs:**
```powershell
gcloud run services logs read agent-core `
  --region us-central1 `
  --project ai-agent-project-497604 `
  --limit 20
```

Look for `[AUDIT]` lines with `agent.run.start` and `agent.run.complete`.

**GCP Console:** Pub/Sub → Topics → `audit-events` → Messages

**Local (Docker Compose):**
```powershell
docker compose -f docker/docker-compose.yml logs agent-core --tail=20
```

---

## Role Reference

| Role | Can Use Skills |
|---|---|
| `viewer` | None |
| `developer` | cloud-architecture, secure-coding, api-standards |
| `senior-engineer` | + incident-response, terraform-iac, threat-modeling |
| `architect` | + banking-compliance, data-privacy |
| `admin` | All skills |

---

## Ingesting Documents

### Step 1 — Upload source docs to GCS

```powershell
# Single file
gcloud storage cp "C:\path\to\doc.md" `
  gs://ai-agent-project-497604-agentic-ai-docs/

# Entire folder
gcloud storage cp -r "C:\path\to\docs\" `
  gs://ai-agent-project-497604-agentic-ai-docs/docs/
```

Supported file types: `.txt`, `.md`, `.py`, `.yaml`, `.json`

### Step 2 — Trigger ingestion

**Cloud Run:**
```powershell
Invoke-RestMethod -Method POST `
  -Uri "https://rag-service-hcm6dgvcaq-uc.a.run.app/ingest" `
  -ContentType "application/json" `
  -Body '{"prefix": "", "allowed_roles": ["developer", "admin"]}'
```

**Local:**
```powershell
Invoke-RestMethod -Method POST `
  -Uri "http://localhost:8001/ingest" `
  -ContentType "application/json" `
  -Body '{"prefix": "", "allowed_roles": ["developer", "admin"]}'
```

**Response:**
```json
{ "ingested": 8, "skipped": 0, "prefix": "" }
```

Re-ingesting the same documents is safe — chunks use deterministic IDs so they overwrite rather than duplicate.

### Step 3 — Verify Qdrant collection

```powershell
# Check vector count
Invoke-RestMethod -Uri "https://qdrant-hcm6dgvcaq-uc.a.run.app/collections/knowledge-base"

# Local
Invoke-RestMethod -Uri "http://localhost:6333/collections/knowledge-base"
```

Look for `"vectors_count"` > 0 in the response.

---

## API Reference

### POST /run (agent-core)

```powershell
Invoke-RestMethod -Method POST `
  -Uri "https://agent-core-hcm6dgvcaq-uc.a.run.app/run" `
  -ContentType "application/json" `
  -Body '{
    "query": "What are the MAS TRM requirements for cloud hosting?",
    "user_id": "senthil",
    "user_role": "architect",
    "skill": "banking-compliance",
    "session_id": "optional-uuid-for-multi-turn"
  }'
```

**Response:**
```json
{
  "answer": "...",
  "session_id": "uuid",
  "tool_calls_made": ["retrieve", "format_banking_response"]
}
```

### POST /ingest (rag-service)

```powershell
Invoke-RestMethod -Method POST `
  -Uri "https://rag-service-hcm6dgvcaq-uc.a.run.app/ingest" `
  -ContentType "application/json" `
  -Body '{"prefix": "docs/", "allowed_roles": ["developer", "architect", "admin"]}'
```

### POST /retrieve (rag-service)

```powershell
Invoke-RestMethod -Method POST `
  -Uri "https://rag-service-hcm6dgvcaq-uc.a.run.app/retrieve" `
  -ContentType "application/json" `
  -Body '{
    "query": "cloud architecture best practices",
    "top_k": 5,
    "user_id": "senthil",
    "user_roles": ["architect"]
  }'
```

### POST /policy/check (governance)

```powershell
Invoke-RestMethod -Method POST `
  -Uri "https://governance-hcm6dgvcaq-uc.a.run.app/policy/check" `
  -ContentType "application/json" `
  -Body '{
    "user_role": "developer",
    "skill": "banking-compliance",
    "prompt": "test query"
  }'
```

**Response (blocked):**
```json
{
  "allowed": false,
  "violations": ["skill 'banking-compliance' requires role 'architect'"]
}
```

### GET /health (all services)

```powershell
Invoke-RestMethod -Uri "https://agent-core-hcm6dgvcaq-uc.a.run.app/health"
Invoke-RestMethod -Uri "https://rag-service-hcm6dgvcaq-uc.a.run.app/health"
Invoke-RestMethod -Uri "https://governance-hcm6dgvcaq-uc.a.run.app/health"
Invoke-RestMethod -Uri "https://llm-gateway-hcm6dgvcaq-uc.a.run.app/health/liveliness"
Invoke-RestMethod -Uri "https://qdrant-hcm6dgvcaq-uc.a.run.app/healthz"
```

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| `Error: fetch failed` on portal/ide-chat | `AGENT_CORE_URL` not set | `gcloud run services update portal --update-env-vars AGENT_CORE_URL=<url>` |
| `No relevant documents found` | Nothing ingested yet, or Qdrant cold start | Run `/ingest` endpoint; retry after ~30s on cold start |
| Duplicate chunks in Qdrant | Old version of vector_store.py | Re-ingest after updating — deterministic IDs will overwrite |
| Tool badges not showing | LLM answered without tools | Normal for simple queries — tools only invoked when needed |
| `403` on every query | Governance service unreachable | Check governance health endpoint |
| BOM character error in secrets | PowerShell UTF-8 encoding | Re-store secret using BOM-less UTF-8 (see deploy.ps1 Set-Secret function) |
| IDE Chat sessions lost on refresh | localStorage cleared or private mode | Use regular browser window; sessions persist in localStorage |
| Qdrant `vectors_count` is 0 | Ingestion not run yet | Upload docs to GCS then call `/ingest` |
| rag-service build fails (ModuleNotFoundError) | pyproject.toml missing sentence-transformers | Ensure pyproject.toml has `sentence-transformers==3.0.1` and `qdrant-client==1.9.1` |

---

## Local vs Cloud Run — Key Differences

| | Local (Docker Compose) | Cloud Run |
|---|---|---|
| Service discovery | Docker DNS (`http://qdrant:6333`) | Cloud Run URLs (`https://...run.app`) |
| GCP credentials | Mounted from `%APPDATA%/gcloud/` | Workload Identity (service account) |
| Secrets | `.env` file | Secret Manager |
| Qdrant persistence | Named Docker volume (`qdrant_storage`) | GCS FUSE volume mount |
| Session store | In-memory (lost on restart) | In-memory (lost on new revision) |
| Audit events | Stdout fallback if Pub/Sub unreachable | Pub/Sub `audit-events` topic |
| IDE Chat history | localStorage (per browser) | localStorage (per browser) |
