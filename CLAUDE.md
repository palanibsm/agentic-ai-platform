# Agentic AI Platform — Claude Instructions

## Project Overview
Enterprise agentic AI platform for a Singapore bank built on LangGraph, Claude Agent SDK, LiteLLM, and GCP.

## Repo Structure
- `apps/` — Frontend (Next.js portal, IDE chat UI)
- `services/` — Backend microservices (agent-core, llm-gateway, rag-service, governance)
- `skills/` — Claude Code Skills (one folder per enterprise skill)
- `infra/` — Terraform (GCP) + Cloud Workflows YAMLs
- `docker/` — docker-compose for local dev
- `docs/` — Architecture docs and runbooks

## Key Conventions
- All Python services use `pyproject.toml` with `uv` or `pip`
- All services expose health check at `GET /health`
- Secrets via `.env` locally; GCP Secret Manager in Cloud Run
- Every agent action must emit an audit event to `audit-events` Pub/Sub topic
- PII/DLP checks must run before any LLM call involving user data
- All skills must have a `SKILL.md` as the entry point

## Skills Usage
Load a skill by reading its `SKILL.md` before executing the task.
Skills are in `skills/<skill-name>/SKILL.md`.

## Running Locally
```bash
cp .env.example .env
# fill in values
docker compose -f docker/docker-compose.yml up
```
