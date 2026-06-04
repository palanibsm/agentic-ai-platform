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
from src.skills.registry import list_skills

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


async def _a2a_check(caller_team_id: str, target_agent_id: str) -> None:
    """
    Enforce A2A access control before one agent invokes another.
    Raises 403 if the calling team is not whitelisted for the target agent.
    Fail-open if governance is unreachable (logged).
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"{GOVERNANCE_URL}/a2a/check",
                json={"requester_team_id": caller_team_id, "target_agent_id": target_agent_id},
            )
            if resp.status_code == 200:
                data = resp.json()
                if not data.get("allowed", True):
                    raise HTTPException(
                        status_code=403,
                        detail=f"A2A access denied: {data.get('reason', 'not_whitelisted')}",
                    )
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("A2A governance check failed (fail-open): %s", exc)


# ── Schemas ──────────────────────────────────────────────────────────────────

class RunRequest(BaseModel):
    query: str
    user_id: str = "anon"
    user_role: str = "business-user"
    team_id: str | None = None         # team the user belongs to (used for isolation)
    skill: str | None = None
    session_id: str | None = None      # if None, a new session is created


class A2ARunRequest(BaseModel):
    """Used when one agent invokes another agent (A2A call)."""
    query: str
    caller_team_id: str                # team of the calling agent
    target_agent_id: str               # registry ID of the target agent
    user_id: str = "system"
    user_role: str = "app-devops"
    skill: str | None = None
    session_id: str | None = None


class RunResponse(BaseModel):
    answer: str
    session_id: str
    tool_calls_made: list[str]
    team_id: str | None = None


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
    team_id = os.getenv("TEAM_ID", "platform")
    return {"status": "ok", "service": "agent-core", "team_id": team_id}


@app.get("/skills")
async def skills():
    """Return available skills for the UI skill selector."""
    return {"skills": list_skills()}


@app.post("/run", response_model=RunResponse)
async def run(req: RunRequest):
    """Execute the agent graph for a single user query."""
    session_id = req.session_id or str(uuid.uuid4())

    # Governance policy check — enforces RBAC before any LLM call
    await _policy_check(req.user_role, req.skill, req.query)

    # Team isolation: use team_id from request or fall back to TEAM_ID env var
    # Cloud Run services are named agent-core-{team-name} per team
    effective_team_id = req.team_id or os.getenv("TEAM_ID", "platform")

    try:
        result = await run_agent(
            query=req.query,
            user_id=req.user_id,
            user_role=req.user_role,
            skill=req.skill,
            session_id=session_id,
            team_id=effective_team_id,
        )
    except Exception as exc:
        logger.exception("Agent run failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))

    return RunResponse(**result, team_id=effective_team_id)


@app.post("/a2a/invoke", response_model=RunResponse)
async def a2a_invoke(req: A2ARunRequest):
    """
    Agent-to-Agent invocation endpoint.
    The calling agent must pass its team_id and the target agent's registry ID.
    Governance A2A check is enforced before execution.
    An audit event is emitted for every A2A call.
    """
    session_id = req.session_id or str(uuid.uuid4())

    # A2A access check — raises 403 if caller is not whitelisted
    await _a2a_check(req.caller_team_id, req.target_agent_id)

    # Emit audit event for A2A call
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            await client.post(
                f"{GOVERNANCE_URL}/audit/events",
                json={
                    "event_type": "a2a_call",
                    "user_id": req.user_id,
                    "session_id": session_id,
                    "payload": {
                        "caller_team_id": req.caller_team_id,
                        "target_agent_id": req.target_agent_id,
                        "skill": req.skill,
                    },
                },
            )
    except Exception as exc:
        logger.warning("Failed to emit A2A audit event: %s", exc)

    try:
        result = await run_agent(
            query=req.query,
            user_id=req.user_id,
            user_role=req.user_role,
            skill=req.skill,
            session_id=session_id,
            team_id=req.caller_team_id,
        )
    except Exception as exc:
        logger.exception("A2A agent run failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))

    return RunResponse(**result, team_id=req.caller_team_id)
