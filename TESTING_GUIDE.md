# Agentic AI Platform — Testing Guide

## Quick Start

**Production portal:** https://portal-hcm6dgvcaq-uc.a.run.app  
**Local portal:** http://localhost:3000 (after `docker compose up`)

---

## The UI

When you open the portal you will see:

- **Role selector** (top right) — controls what the agent is allowed to do
- **Skill selector** (top right) — activates a specialised agent persona
- **Clear button** — resets the conversation session
- **Tool call badges** — appear below each response showing which tools the agent used (e.g. `retrieve`, `format_banking_response`)

---

## Test Scenarios

### Test 1 — Basic Identity Check
**Role:** Developer | **Skill:** None

> `Hi, who are you?`

**Expected:** Agent introduces itself as an enterprise AI assistant for a Singapore bank, lists capabilities (RAG, compliance, MAS TRM), and states operating boundaries (no PII, auditable).

**Tool badges expected:** `format_banking_response`

---

### Test 2 — RAG Document Retrieval
**Role:** Developer | **Skill:** None

> `What documents do we have about cloud architecture?`

**Expected:** Agent calls `retrieve` (badge appears), returns chunked content from ingested documents with source citations and relevance scores.

**Tool badges expected:** `retrieve`, `format_banking_response`

> **Note:** Documents must be ingested first. See [Ingesting Documents](#ingesting-documents) below.

---

### Test 3 — RBAC Block (Developer → Compliance Skill)
**Role:** Developer | **Skill:** Banking Compliance

> `What are our data residency obligations under MAS?`

**Expected:** `403 Access denied — skill 'banking-compliance' requires role 'architect' (current: 'developer')`

---

### Test 4 — RBAC Allow (Architect → Compliance Skill)
**Role:** Architect | **Skill:** Banking Compliance

> `What are our data residency obligations under MAS?`

**Expected:** Agent retrieves relevant documents and answers with MAS TRM-grounded response. Source citations included.

**Tool badges expected:** `retrieve`, `format_banking_response`

---

### Test 5 — Session Continuity (Multi-turn)
**Role:** Developer | **Skill:** None

Turn 1:
> `My name is Senthil and I work in the cloud team.`

Turn 2 (same session, do NOT press Clear):
> `What did I just tell you about myself?`

**Expected:** Agent correctly recalls name and team from the previous turn.

---

### Test 6 — MAS TRM Query with RAG
**Role:** Architect | **Skill:** Banking Compliance

> `What are the MAS TRM requirements for AI model governance?`

**Expected:** Detailed response grounded in retrieved documents covering model risk, explainability, and audit requirements.

**Tool badges expected:** `retrieve`, `retrieve`, `format_banking_response`

---

### Test 7 — RBAC Block (Developer → Incident Response Skill)
**Role:** Developer | **Skill:** Incident Response

> `Help me with a production incident`

**Expected:** `403 Access denied — skill 'incident-response' requires role 'senior-engineer' (current: 'developer')`

---

### Test 8 — Audit Trail Verification
After running any of the above tests, check that audit events are flowing to Pub/Sub:

**Local:**
```bash
docker compose -f docker/docker-compose.yml logs agent-core --tail=20
```
Look for `[AUDIT]` lines with `agent.run.start` and `agent.run.complete`.

**Cloud Run:**
```bash
gcloud run services logs read agent-core \
  --region us-central1 \
  --project ai-agent-project-497604 \
  --limit 20
```

Or view in GCP Console:  
**Pub/Sub → Topics → audit-events → Messages**

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

### Via API (local)
```bash
curl -X POST http://localhost:8001/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "prefix": "docs/",
    "allowed_roles": ["developer", "architect", "admin"]
  }'
```

### Via API (Cloud Run)
```bash
curl -X POST https://rag-service-hcm6dgvcaq-uc.a.run.app/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "prefix": "docs/",
    "allowed_roles": ["developer", "architect", "admin"]
  }'
```

### Upload documents to GCS first
```bash
gsutil cp your-doc.pdf gs://ai-agent-project-497604-agentic-ai-docs/docs/
```

Supported file types: `.txt`, `.md`, `.py`, `.yaml`, `.json`

---

## API Reference

### POST /run (agent-core)

```bash
curl -X POST https://agent-core-hcm6dgvcaq-uc.a.run.app/run \
  -H "Content-Type: application/json" \
  -d '{
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

### POST /retrieve (rag-service)

```bash
curl -X POST https://rag-service-hcm6dgvcaq-uc.a.run.app/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "query": "cloud architecture best practices",
    "top_k": 5,
    "user_id": "senthil",
    "user_roles": ["architect"]
  }'
```

### POST /policy/check (governance)

```bash
curl -X POST https://governance-hcm6dgvcaq-uc.a.run.app/policy/check \
  -H "Content-Type: application/json" \
  -d '{
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

```bash
curl https://agent-core-hcm6dgvcaq-uc.a.run.app/health
curl https://rag-service-hcm6dgvcaq-uc.a.run.app/health
curl https://governance-hcm6dgvcaq-uc.a.run.app/health
curl https://llm-gateway-hcm6dgvcaq-uc.a.run.app/health/liveliness
```

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| `Error: fetch failed` | `AGENT_CORE_URL` not set in portal | `gcloud run services update portal --update-env-vars AGENT_CORE_URL=<url>` |
| `Error 500` on RAG query | Vertex AI timeout on first call (cold start) | Retry — model is now cached after first call |
| `No relevant documents found` | Nothing ingested yet | Run `/ingest` endpoint |
| Tool badges not showing | LLM answered without tools | Normal for simple queries — tools only invoked when needed |
| 403 on every query | Governance service unreachable | Check governance health endpoint |
| BOM character error | Secret stored with Windows line ending | Re-store secret using BOM-less UTF-8 (see deploy.ps1) |

---

## Local vs Cloud Run — Key Differences

| | Local (Docker Compose) | Cloud Run |
|---|---|---|
| Service discovery | Docker DNS (`http://governance:8003`) | Cloud Run URLs (`https://...run.app`) |
| GCP credentials | Mounted from `%APPDATA%/gcloud/` | Workload Identity (service account) |
| Secrets | `.env` file | Secret Manager |
| Session store | In-memory (lost on restart) | In-memory (lost on new revision) |
| Audit events | Stdout fallback if Pub/Sub unreachable | Pub/Sub `audit-events` topic |
