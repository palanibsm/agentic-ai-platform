# Agentic AI Platform

Enterprise-grade agentic AI platform for a Singapore bank, built on LangGraph, LiteLLM, Qdrant, and GCP Cloud Run.

> **Testing & Usage Guide:** See [TESTING_GUIDE.md](./TESTING_GUIDE.md) for step-by-step test scenarios, API reference, role matrix, ingestion instructions, and troubleshooting tips.

## Architecture

```
Browser → Portal (Next.js)          IDE Chat (Next.js, dark theme)
            ↓                                  ↓
        Agent Core (LangGraph ReAct) ──────────┘
         ↙        ↘         ↘
LLM Gateway    RAG Service  Governance
(LiteLLM)    (sentence-     (RBAC/MAS TRM)
     ↓        transformers)
 Claude/GPT       ↓
              Qdrant (vector store)
                  + GCS (source docs)
```

All agent actions are audited to GCP Pub/Sub (`audit-events` topic) in compliance with MAS TRM guidelines.

## Services

| Service | Description | Port |
|---|---|---|
| `portal` | Next.js chat UI — business users | 3000 |
| `ide-chat` | Next.js IDE-style chat — developers (dark theme, code highlighting, session history) | 3001 |
| `agent-core` | LangGraph ReAct orchestration (FastAPI) | 8002 |
| `llm-gateway` | LiteLLM proxy — Claude Sonnet, GPT-4o fallback | 4000 |
| `rag-service` | RAG retrieval with sentence-transformers + Qdrant | 8001 |
| `governance` | RBAC policy engine (MAS TRM compliant) | 8003 |
| `qdrant` | Vector store with RBAC payload filtering | 6333 |

## Skills

| Skill | Min Role |
|---|---|
| `banking-compliance` | architect |
| `data-privacy` | architect |
| `incident-response` | senior-engineer |
| `terraform-iac` | senior-engineer |
| `threat-modeling` | senior-engineer |
| `cloud-architecture` | developer |
| `secure-coding` | developer |
| `api-standards` | developer |

## Roles (RBAC hierarchy)

```
viewer < developer < senior-engineer < architect < admin
```

## Local Development

### Prerequisites
- Docker Desktop
- GCP project with a GCS bucket for RAG source documents
- API keys: `ANTHROPIC_API_KEY`, `LITELLM_MASTER_KEY`
- GCP application default credentials (`gcloud auth application-default login`)

### Setup

```powershell
cp .env.example .env
# Fill in your values
docker compose -f docker/docker-compose.yml up --build
```

| UI | URL |
|---|---|
| Portal | http://localhost:3000 |
| IDE Chat | http://localhost:3001 |
| Qdrant dashboard | http://localhost:6333/dashboard |

### Ingest documents into Qdrant

Upload source docs to GCS first, then call the ingest endpoint:

```powershell
# Upload a document
gcloud storage cp "C:\path\to\your\doc.md" gs://ai-agent-project-497604-agentic-ai-docs/

# Ingest into Qdrant
Invoke-RestMethod -Method POST `
  -Uri "http://localhost:8001/ingest" `
  -ContentType "application/json" `
  -Body '{"prefix": "", "allowed_roles": ["developer", "admin"]}'
```

Supported file types: `.txt`, `.md`, `.py`, `.yaml`, `.json`

Re-ingesting the same document is safe — chunks are identified by a deterministic ID (md5 of source path + chunk index) so re-runs overwrite rather than duplicate.

## GCP Deployment

### First-time setup

```powershell
# Deploy all services to Cloud Run
.\infra\deploy.ps1

# Set up CI/CD trigger (after connecting GitHub repo in Cloud Build console)
.\infra\setup-cicd.ps1
```

### Terraform (IaC)

```powershell
cd infra/terraform

# Create state bucket (one-time)
gcloud storage buckets create gs://ai-agent-project-497604-tf-state --location=us-central1

# Init and apply
terraform init
terraform plan
terraform apply
```

Terraform manages: Cloud Run services, Artifact Registry, GCS buckets, Pub/Sub, Secret Manager, IAM.

### CI/CD

Push to `main` triggers Cloud Build (`infra/cloudbuild.yaml`):
1. Builds all 6 Docker images in parallel (governance, llm-gateway, rag-service, agent-core, portal, ide-chat)
2. Pushes to Artifact Registry (tagged with commit SHA + `latest`)
3. Deploys services to Cloud Run in dependency order
4. Rebuilds portal and ide-chat with live agent-core URL baked in as a build arg

Monitor builds: https://console.cloud.google.com/cloud-build/builds?project=ai-agent-project-497604

## Cloud Run URLs (Production)

| Service | URL |
|---|---|
| Portal | https://portal-hcm6dgvcaq-uc.a.run.app |
| IDE Chat | https://ide-chat-hcm6dgvcaq-uc.a.run.app |
| Agent Core | https://agent-core-hcm6dgvcaq-uc.a.run.app |
| RAG Service | https://rag-service-hcm6dgvcaq-uc.a.run.app |
| LLM Gateway | https://llm-gateway-hcm6dgvcaq-uc.a.run.app |
| Governance | https://governance-hcm6dgvcaq-uc.a.run.app |
| Qdrant | https://qdrant-hcm6dgvcaq-uc.a.run.app |

## Environment Variables

| Variable | Description | Required |
|---|---|---|
| `ANTHROPIC_API_KEY` | Anthropic API key | Yes |
| `LITELLM_MASTER_KEY` | LiteLLM gateway master key | Yes |
| `OPENAI_API_KEY` | OpenAI API key (GPT-4o fallback) | Optional |
| `GCP_PROJECT_ID` | GCP project ID | Yes |
| `GCP_REGION` | GCP region (default: us-central1) | Yes |
| `GCS_BUCKET_NAME` | GCS bucket for RAG source documents | Yes |
| `QDRANT_URL` | Qdrant service URL | Yes (set automatically in Cloud Run) |
| `QDRANT_COLLECTION` | Qdrant collection name (default: knowledge-base) | Optional |

Secrets (`ANTHROPIC_API_KEY`, `LITELLM_MASTER_KEY`, `OPENAI_API_KEY`) are stored in GCP Secret Manager in production.

## Embeddings & Vector Store

- **Embedding model:** `all-MiniLM-L6-v2` (sentence-transformers, 384 dims, runs locally inside the container — no external API call)
- **Vector store:** Qdrant with payload-based RBAC filtering (`allowed_roles` field)
- **Persistence:** GCS volume mount on Cloud Run; named Docker volume locally
- **Cost:** ~$0/month for Qdrant on Cloud Run (scales to zero) vs ~$97/month for Vertex AI Vector Search

## Compliance

- **MAS TRM**: All LLM calls audited to Pub/Sub; no PII in logs; conservative, auditable responses
- **RBAC**: Skills gated by role; governance service enforces policy before every agent run
- **Budget cap**: LLM spend capped via LiteLLM gateway
- **Fallback**: Claude Sonnet falls back to GPT-4o on failure
- **Idempotent ingestion**: Re-ingesting docs overwrites chunks, no duplicates

## Project Structure

```
.
├── apps/
│   ├── portal/              # Next.js chat UI (business users, port 3000)
│   └── ide-chat/            # Next.js IDE chat (developers, port 3001, dark theme)
├── services/
│   ├── agent-core/          # LangGraph ReAct agent (FastAPI)
│   ├── llm-gateway/         # LiteLLM proxy (Claude + GPT-4o)
│   ├── rag-service/         # RAG ingestion + retrieval (sentence-transformers + Qdrant)
│   └── governance/          # RBAC policy engine (FastAPI)
├── skills/                  # Enterprise skill SKILL.md definitions (8 skills)
├── infra/
│   ├── terraform/           # GCP IaC (Cloud Run, IAM, GCS, Pub/Sub, Secret Manager)
│   ├── cloud-workflows/     # GCP Cloud Workflows (approval-gate, rag-ingestion)
│   ├── cloudbuild.yaml      # CI/CD pipeline (6 services, parallel builds)
│   ├── deploy.ps1           # Manual deploy script (PowerShell)
│   └── setup-cicd.ps1       # Cloud Build GitHub trigger setup
└── docker/
    └── docker-compose.yml   # Local dev stack (7 services including Qdrant)
```
