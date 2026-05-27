"""
agent-core — FastAPI entry point.
Exposes /run (agent execution) and /health endpoints.
"""

import logging
import uuid
import os
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Load .env for local dev
try:
    from dotenv import load_dotenv
    load_dotenv(override=False)
except ImportError:
    pass

from src.graph.agent import run_agent

GOVERNANCE_URL = os.getenv("GOVERNANCE_URL", "http://localhost:8003")


async def _policy_check(user_role: str, skill: str | None, query: str) -> None:
    """Call governance service to enforce RBAC. Raises 403 if blocked."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"{GOVERNANCE_URL}/policy/check",
                json={"user_role": user_role, "skill": skill, "prompt": query},
            )
            if resp.status_code == 200:
                data = resp.json()
                if not data.get("allowed", True):
                    violations = "; ".join(data.get("violations", []))
                    raise HTTPException(status_code=403, detail=f"Access denied: {violations}")
    except HTTPException:
        raise
    except Exception as exc:
        # Governance unreachable — log and allow (fail-open for resilience)
        logging.getLogger(__name__).warning("Governance check failed (fail-open): %s", exc)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ── Schemas ──────────────────────────────────────────────────────────────────

class RunRequest(BaseModel):
    query: str
    user_id: str = "anon"
    user_role: str = "developer"       # developer | senior-engineer | architect | admin
    skill: str | None = None
    session_id: str | None = None      # if None, a new session is created


class RunResponse(BaseModel):
    answer: str
    session_id: str
    tool_calls_made: list[str]


# ── App ──────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("agent-core starting up")
    yield
    logger.info("agent-core shutting down")


app = FastAPI(
    title="agent-core",
    description="LangGraph orchestration service for Agentic AI Platform",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routes ───────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "agent-core"}


@app.post("/run", response_model=RunResponse)
async def run(req: RunRequest):
    """Execute the agent graph for a single user query."""
    session_id = req.session_id or str(uuid.uuid4())

    # Governance policy check — enforces RBAC before any LLM call
    await _policy_check(req.user_role, req.skill, req.query)

    try:
        result = await run_agent(
            query=req.query,
            user_id=req.user_id,
            user_role=req.user_role,
            skill=req.skill,
            session_id=session_id,
        )
    except Exception as exc:
        logger.exception("Agent run failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))

    return RunResponse(**result)
