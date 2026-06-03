"""
governance — FastAPI entry point.
Provides policy checking, team/user management, A2A access control,
audit log querying, and usage reporting.
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

try:
    from dotenv import load_dotenv
    load_dotenv(override=False)
except ImportError:
    pass

from src.policy.engine import check_access, PolicyResult
from src.audit.store import record_event, query_events, event_count
from src.usage.tracker import record_llm_call, get_report
from src.db.connection import init_pool, close_pool
from src.teams.router import router as teams_router
from src.users.router import router as users_router
from src.a2a.router import router as a2a_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_ENABLED = bool(os.getenv("DATABASE_URL"))


# ── Schemas ───────────────────────────────────────────────────────────────────

class PolicyCheckRequest(BaseModel):
    user_role: str = "business-user"
    skill: str | None = None
    model: str | None = None
    prompt: str | None = None
    operation: str | None = None
    team_id: str | None = None
    target_team_id: str | None = None


class PolicyCheckResponse(BaseModel):
    allowed: bool
    reason: str
    violations: list[str]


class AuditEventRequest(BaseModel):
    event_type: str
    user_id: str
    session_id: str
    payload: dict = {}


class UsageRecordRequest(BaseModel):
    user_id: str
    model: str
    skill: str | None = None
    team_id: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0


# ── App lifecycle ─────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("governance service starting up")
    if DB_ENABLED:
        try:
            await init_pool()
            logger.info("PostgreSQL connected")
        except Exception as e:
            logger.warning("PostgreSQL unavailable — DB features disabled: %s", e)
    else:
        logger.info("DATABASE_URL not set — running without PostgreSQL (policy-only mode)")
    yield
    if DB_ENABLED:
        await close_pool()
    logger.info("governance service shutting down")


app = FastAPI(
    title="governance",
    description="Policy, RBAC, team management, A2A access control, audit and usage for Agentic AI Platform",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(teams_router)
app.include_router(users_router)
app.include_router(a2a_router)


# ── Core routes ───────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "governance",
        "version": "0.2.0",
        "db_enabled": DB_ENABLED,
        "audit_events_stored": event_count(),
    }


@app.post("/policy/check", response_model=PolicyCheckResponse)
async def policy_check(req: PolicyCheckRequest):
    """Check whether a request is permitted under governance rules."""
    result: PolicyResult = check_access(
        user_role=req.user_role,
        skill=req.skill,
        model=req.model,
        prompt=req.prompt,
        operation=req.operation,
        team_id=req.team_id,
        target_team_id=req.target_team_id,
    )
    return PolicyCheckResponse(
        allowed=result.allowed,
        reason=result.reason,
        violations=result.violations,
    )


@app.post("/audit/events", status_code=201)
async def ingest_audit_event(req: AuditEventRequest):
    record_event({
        "event_type": req.event_type,
        "user_id": req.user_id,
        "session_id": req.session_id,
        **req.payload,
    })
    return {"status": "recorded"}


@app.get("/audit/events")
async def get_audit_events(
    event_type: str | None = Query(None),
    user_id: str | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
):
    return {"events": query_events(event_type=event_type, user_id=user_id, limit=limit)}


@app.post("/usage/record", status_code=201)
async def record_usage(req: UsageRecordRequest):
    record_llm_call(
        user_id=req.user_id,
        model=req.model,
        skill=req.skill,
        input_tokens=req.input_tokens,
        output_tokens=req.output_tokens,
    )
    return {"status": "recorded"}


@app.get("/usage/report")
async def usage_report():
    return get_report()
