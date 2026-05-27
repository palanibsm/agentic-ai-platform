"""
governance — FastAPI entry point.
Provides policy checking, audit log querying, and usage reporting.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Query
from pydantic import BaseModel

try:
    from dotenv import load_dotenv
    load_dotenv(override=False)
except ImportError:
    pass

from src.policy.engine import check_access, PolicyResult
from src.audit.store import record_event, query_events, event_count
from src.usage.tracker import record_llm_call, get_report

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ── Schemas ──────────────────────────────────────────────────────────────────

class PolicyCheckRequest(BaseModel):
    user_role: str = "developer"
    skill: str | None = None
    model: str | None = None
    prompt: str | None = None


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
    input_tokens: int = 0
    output_tokens: int = 0


# ── App ──────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("governance service starting up")
    yield
    logger.info("governance service shutting down")


app = FastAPI(
    title="governance",
    description="Policy, audit, and usage governance for Agentic AI Platform",
    version="0.1.0",
    lifespan=lifespan,
)


# ── Routes ───────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "governance", "audit_events_stored": event_count()}


# Policy

@app.post("/policy/check", response_model=PolicyCheckResponse)
async def policy_check(req: PolicyCheckRequest):
    """Check whether a request is permitted under governance rules."""
    result: PolicyResult = check_access(
        user_role=req.user_role,
        skill=req.skill,
        model=req.model,
        prompt=req.prompt,
    )
    return PolicyCheckResponse(
        allowed=result.allowed,
        reason=result.reason,
        violations=result.violations,
    )


# Audit

@app.post("/audit/events", status_code=201)
async def ingest_audit_event(req: AuditEventRequest):
    """Ingest an audit event (called by agent-core or llm-gateway)."""
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
    """Query stored audit events."""
    return {"events": query_events(event_type=event_type, user_id=user_id, limit=limit)}


# Usage

@app.post("/usage/record", status_code=201)
async def record_usage(req: UsageRecordRequest):
    """Record token usage for a completed LLM call."""
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
    """Return aggregated token and cost usage report."""
    return get_report()
