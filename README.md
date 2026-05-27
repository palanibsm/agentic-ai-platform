# Agentic AI Platform

Enterprise-grade agentic AI platform for a Singapore bank, built on LangGraph, LiteLLM, Vertex AI, and GCP Cloud Run.

## Architecture

```
Browser → Portal (Next.js)
            ↓
        Agent Core (LangGraph ReAct)
         ↙        ↘         ↘
LLM Gateway    RAG Service  Governance
(LiteLLM)    (Vertex AI)    (RBAC)
     ↓              ↓
 Claude/GPT    Vector Search
                  + GCS
```

All agent actions are audited to GCP Pub/Sub (`audit-events` topic) in compliance with MAS TRM guidelines.

## Services

| Service | Description | Port |
|---|---|---|
| `portal` | Next.js chat UI with role/skill selectors | 3000 |
| `agent-core` | LangGraph ReAct orchestration (FastAPI) | 8002 |
| `llm-gateway` | LiteLLM proxy — Claude Sonnet, GPT-4o | 4000 |
| `rag-service` | RAG retrieval via Vertex AI Vector Search | 8001 |
| `governance` | RBAC policy engine (MAS TRM compliant) | 8003 |

## Skills

| Skill | Min Role |
|---|---|
| `banking-compliance` | architect |
| `incident-response` | senior-engineer |
| `terraform-iac` | senior-engineer |
| `cloud-architecture` | developer |
| `secure-coding` | developer |
| `threat-modeling` | senior-engineer |
| `data-privacy` | architect |
| `api-standards` | developer |

## Roles (RBAC hierarchy)

```
viewer < developer < senior-engineer < architect < admin
```

## Local Development

### Prerequisites
- Docker Desktop
- GCP project with Vertex AI Vector Search index deployed
- API keys: `ANTHROPIC_API_KEY`, `LITELLM_MASTER_KEY`

### Setup

```bash
cp .env.example .env
# Fill in your values
docker compose -f docker/docker-compose.yml up --build
```

Portal available at **http://localhost:3000**

### Ingest documents into RAG

```bash
curl -X POST http://localhost:8001/ingest \
  -H "Content-Type: application/json" \
  -d '{"prefix": "docs/", "allowed_roles": ["developer", "architect", "admin"]}'
```

## GCP Deployment

### First-time setup

```powershell
# Deploy all services to Cloud Run
.\infra\deploy.ps1

# Set up CI/CD trigger (after connecting GitHub repo in Cloud Build console)
.\infra\setup-cicd.ps1 -Repo agentic-ai-platform -Owner palanibsm
```

### Terraform (IaC)

```powershell
cd infra/terraform

# Create state bucket (once)
gcloud storage buckets create gs://ai-agent-project-497604-tf-state --location=us-central1

# Init and apply
terraform init
terraform plan
terraform apply
```

### CI/CD

Push to `main` triggers Cloud Build (`infra/cloudbuild.yaml`):
1. Builds all 5 Docker images in parallel
2. Pushes to Artifact Registry
3. Deploys services in dependency order
4. Rebuilds portal with live agent-core URL baked in

## Cloud Run URLs (Production)

| Service | URL |
|---|---|
| Portal | https://portal-hcm6dgvcaq-uc.a.run.app |
| Agent Core | https://agent-core-hcm6dgvcaq-uc.a.run.app |
| RAG Service | https://rag-service-hcm6dgvcaq-uc.a.run.app |
| LLM Gateway | https://llm-gateway-hcm6dgvcaq-uc.a.run.app |
| Governance | https://governance-hcm6dgvcaq-uc.a.run.app |

## Environment Variables

| Variable | Description | Required |
|---|---|---|
| `ANTHROPIC_API_KEY` | Anthropic API key | Yes |
| `LITELLM_MASTER_KEY` | LiteLLM gateway master key | Yes |
| `OPENAI_API_KEY` | OpenAI API key (fallback model) | Optional |
| `GCP_PROJECT_ID` | GCP project ID | Yes |
| `GCP_REGION` | GCP region (default: us-central1) | Yes |
| `GCS_BUCKET_NAME` | GCS bucket for RAG documents | Yes |
| `VERTEX_AI_INDEX_ID` | Vertex AI Vector Search index ID | Yes |
| `VERTEX_AI_ENDPOINT_ID` | Vertex AI index endpoint ID | Yes |
| `VERTEX_AI_DEPLOYED_INDEX_ID` | Deployed index ID | Yes |

Secrets (`ANTHROPIC_API_KEY`, `LITELLM_MASTER_KEY`, `OPENAI_API_KEY`) are stored in GCP Secret Manager in production.

## Compliance

- **MAS TRM**: All LLM calls audited to Pub/Sub; no PII in logs; conservative, auditable responses
- **RBAC**: Skills gated by role; governance service enforces policy before every agent run
- **Budget cap**: LLM spend capped at $25/month via LiteLLM gateway
- **Fallback**: Claude Sonnet falls back to GPT-4o on failure

## Project Structure

```
.
├── apps/
│   └── portal/              # Next.js chat UI
├── services/
│   ├── agent-core/          # LangGraph agent (FastAPI)
│   ├── llm-gateway/         # LiteLLM proxy
│   ├── rag-service/         # RAG retrieval (FastAPI)
│   └── governance/          # RBAC policy engine (FastAPI)
├── skills/                  # Enterprise skill SKILL.md definitions
├── infra/
│   ├── terraform/           # GCP IaC (Cloud Run, IAM, Storage, Pub/Sub)
│   ├── cloudbuild.yaml      # CI/CD pipeline
│   ├── deploy.ps1           # Manual deploy script
│   └── setup-cicd.ps1       # Cloud Build trigger setup
└── docker/
    └── docker-compose.yml   # Local dev stack
```
