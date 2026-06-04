"""Agent-to-Agent (A2A) access control API."""

import uuid
import json
import logging
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
from src.db import connection as db
from src.policy.engine import can_manage_platform, can_manage_team_agents

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/a2a", tags=["a2a"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class AgentRegister(BaseModel):
    team_id: str
    agent_name: str
    display_name: str
    description: Optional[str] = None
    skills: list[str] = []
    model: str = "claude-sonnet"
    service_url: Optional[str] = None
    is_public: bool = False


class A2AAccessRequest(BaseModel):
    requester_team_id: str
    target_agent_id: str
    requested_by: str          # email of the requester


class A2ACheckRequest(BaseModel):
    requester_team_id: str
    target_agent_id: str


class A2ADecision(BaseModel):
    granted_by: str            # email of the ai-devops approving/denying


# ── Marketplace ───────────────────────────────────────────────────────────────

@router.get("/marketplace")
async def get_marketplace():
    rows = await db.fetch(
        """
        SELECT ar.id, ar.agent_name, ar.display_name, ar.description,
               ar.skills, ar.model, ar.service_url, ar.is_active,
               t.name as team_name, t.display_name as team_display_name
        FROM agent_registrations ar
        JOIN teams t ON t.id=ar.team_id
        WHERE ar.is_public=1 AND ar.is_active=1
        ORDER BY t.name, ar.agent_name
        """
    )
    return {"agents": rows}


# ── Agent registration ────────────────────────────────────────────────────────

@router.get("/agents")
async def list_all_agents():
    rows = await db.fetch(
        """
        SELECT ar.id, ar.agent_name, ar.display_name, ar.description,
               ar.skills, ar.model, ar.service_url, ar.is_public, ar.is_active,
               ar.created_at, t.name as team_name, t.display_name as team_display_name
        FROM agent_registrations ar
        JOIN teams t ON t.id=ar.team_id
        ORDER BY t.name, ar.agent_name
        """
    )
    return {"agents": rows}


@router.get("/agents/team/{team_id}")
async def list_team_agents(team_id: str):
    rows = await db.fetch(
        """
        SELECT id, agent_name, display_name, description, skills, model,
               service_url, is_public, is_active, created_at
        FROM agent_registrations
        WHERE team_id=?
        ORDER BY agent_name
        """,
        team_id,
    )
    return {"agents": rows}


@router.post("/agents", status_code=201)
async def register_agent(body: AgentRegister, x_user_role: str = Header(default="business-user")):
    if not can_manage_team_agents(x_user_role):
        raise HTTPException(status_code=403, detail="app-devops or above required")
    agent_id = str(uuid.uuid4())
    try:
        await db.execute(
            """INSERT INTO agent_registrations
               (id, team_id, agent_name, display_name, description, skills, model, service_url, is_public)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            agent_id, body.team_id, body.agent_name, body.display_name,
            body.description, json.dumps(body.skills), body.model,
            body.service_url, 1 if body.is_public else 0,
        )
    except Exception as e:
        if "unique" in str(e).lower():
            raise HTTPException(status_code=409, detail="Agent already registered for this team")
        raise HTTPException(status_code=500, detail=str(e))
    logger.info("Agent registered: %s / %s", body.team_id, body.agent_name)
    return {"id": agent_id, "agent_name": body.agent_name, "status": "registered"}


@router.put("/agents/{agent_id}")
async def update_agent(agent_id: str, body: AgentRegister, x_user_role: str = Header(default="business-user")):
    if not can_manage_team_agents(x_user_role):
        raise HTTPException(status_code=403, detail="app-devops or above required")
    await db.execute(
        """UPDATE agent_registrations
           SET display_name=?, description=?, skills=?, model=?, service_url=?,
               is_public=?, updated_at=datetime('now')
           WHERE id=?""",
        body.display_name, body.description, json.dumps(body.skills),
        body.model, body.service_url, 1 if body.is_public else 0, agent_id,
    )
    return {"message": "Agent updated"}


@router.delete("/agents/{agent_id}", status_code=204)
async def deregister_agent(agent_id: str, x_user_role: str = Header(default="business-user")):
    if not can_manage_team_agents(x_user_role):
        raise HTTPException(status_code=403, detail="app-devops or above required")
    await db.execute(
        "UPDATE agent_registrations SET is_active=0, updated_at=datetime('now') WHERE id=?",
        agent_id,
    )


# ── A2A runtime check ─────────────────────────────────────────────────────────

@router.post("/check")
async def check_a2a_access(body: A2ACheckRequest):
    """Called by agent-core before one agent invokes another."""
    row = await db.fetchrow(
        """SELECT w.id FROM a2a_whitelist w
           JOIN agent_registrations ar ON ar.id=w.target_agent_id
           WHERE w.requester_team_id=? AND w.target_agent_id=?
             AND w.status='approved' AND ar.is_active=1""",
        body.requester_team_id, body.target_agent_id,
    )
    if row:
        return {"allowed": True, "reason": "whitelisted"}
    public = await db.fetchrow(
        "SELECT id FROM agent_registrations WHERE id=? AND is_public=1 AND is_active=1",
        body.target_agent_id,
    )
    if public:
        return {"allowed": True, "reason": "public_agent"}
    return {"allowed": False, "reason": "not_whitelisted"}


# ── A2A access request flow ───────────────────────────────────────────────────

@router.post("/requests", status_code=201)
async def request_a2a_access(body: A2AAccessRequest, x_user_role: str = Header(default="business-user")):
    """App DevOps requests access to a private agent. Creates a pending entry."""
    if not can_manage_team_agents(x_user_role):
        raise HTTPException(status_code=403, detail="app-devops or above required")
    agent = await db.fetchrow(
        "SELECT id, is_public FROM agent_registrations WHERE id=? AND is_active=1",
        body.target_agent_id,
    )
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found or inactive")
    if agent["is_public"]:
        return {"message": "Agent is public — no request needed", "status": "public"}
    req_id = str(uuid.uuid4())
    try:
        await db.execute(
            """INSERT INTO a2a_whitelist
               (id, requester_team_id, target_agent_id, requested_by, status)
               VALUES (?,?,?,?,'pending')""",
            req_id, body.requester_team_id, body.target_agent_id, body.requested_by,
        )
    except Exception as e:
        if "unique" in str(e).lower():
            existing = await db.fetchrow(
                "SELECT status FROM a2a_whitelist WHERE requester_team_id=? AND target_agent_id=?",
                body.requester_team_id, body.target_agent_id,
            )
            return {"message": "Request already exists", "status": existing["status"] if existing else "unknown"}
        raise HTTPException(status_code=500, detail=str(e))
    logger.info("A2A access requested: team %s → agent %s by %s",
                body.requester_team_id, body.target_agent_id, body.requested_by)
    return {"id": req_id, "status": "pending", "message": "Request submitted for approval"}


@router.get("/requests/pending")
async def list_pending_requests(x_user_role: str = Header(default="business-user")):
    if not can_manage_platform(x_user_role):
        raise HTTPException(status_code=403, detail="ai-devops required")
    rows = await db.fetch(
        """
        SELECT w.id, w.requester_team_id, w.requested_by, w.created_at,
               ar.agent_name, ar.display_name as agent_display_name,
               ar.model, ar.skills,
               rt.name as requester_team_name, rt.display_name as requester_team_display_name,
               at_.name as agent_team_name
        FROM a2a_whitelist w
        JOIN agent_registrations ar ON ar.id=w.target_agent_id
        JOIN teams rt ON rt.id=w.requester_team_id
        JOIN teams at_ ON at_.id=ar.team_id
        WHERE w.status='pending'
        ORDER BY w.created_at DESC
        """
    )
    return {"requests": rows}


@router.get("/requests")
async def list_all_requests(x_user_role: str = Header(default="business-user")):
    if not can_manage_platform(x_user_role):
        raise HTTPException(status_code=403, detail="ai-devops required")
    rows = await db.fetch(
        """
        SELECT w.id, w.requester_team_id, w.requested_by, w.granted_by,
               w.status, w.created_at, w.updated_at,
               ar.agent_name, ar.display_name as agent_display_name,
               rt.name as requester_team_name,
               at_.name as agent_team_name
        FROM a2a_whitelist w
        JOIN agent_registrations ar ON ar.id=w.target_agent_id
        JOIN teams rt ON rt.id=w.requester_team_id
        JOIN teams at_ ON at_.id=ar.team_id
        ORDER BY w.created_at DESC
        """
    )
    return {"requests": rows}


@router.put("/requests/{request_id}/approve")
async def approve_request(request_id: str, body: A2ADecision, x_user_role: str = Header(default="business-user")):
    if not can_manage_platform(x_user_role):
        raise HTTPException(status_code=403, detail="ai-devops required")
    row = await db.fetchrow("SELECT status FROM a2a_whitelist WHERE id=?", request_id)
    if not row:
        raise HTTPException(status_code=404, detail="Request not found")
    if row["status"] != "pending":
        raise HTTPException(status_code=409, detail=f"Request is already '{row['status']}'")
    await db.execute(
        "UPDATE a2a_whitelist SET status='approved', granted_by=?, updated_at=datetime('now') WHERE id=?",
        body.granted_by, request_id,
    )
    return {"message": "Access approved", "request_id": request_id}


@router.put("/requests/{request_id}/deny")
async def deny_request(request_id: str, body: A2ADecision, x_user_role: str = Header(default="business-user")):
    if not can_manage_platform(x_user_role):
        raise HTTPException(status_code=403, detail="ai-devops required")
    row = await db.fetchrow("SELECT status FROM a2a_whitelist WHERE id=?", request_id)
    if not row:
        raise HTTPException(status_code=404, detail="Request not found")
    if row["status"] != "pending":
        raise HTTPException(status_code=409, detail=f"Request is already '{row['status']}'")
    await db.execute(
        "UPDATE a2a_whitelist SET status='denied', granted_by=?, updated_at=datetime('now') WHERE id=?",
        body.granted_by, request_id,
    )
    return {"message": "Access denied", "request_id": request_id}


@router.delete("/requests/{request_id}", status_code=204)
async def delete_request(request_id: str, x_user_role: str = Header(default="business-user")):
    if not can_manage_platform(x_user_role):
        raise HTTPException(status_code=403, detail="ai-devops required")
    await db.execute("DELETE FROM a2a_whitelist WHERE id=?", request_id)


# ── Legacy whitelist (kept for backward compat) ───────────────────────────────

@router.post("/whitelist", status_code=201)
async def grant_a2a_access_direct(body: A2AAccessRequest, x_user_role: str = Header(default="business-user")):
    """Direct approve without approval flow (ai-devops only)."""
    if not can_manage_platform(x_user_role):
        raise HTTPException(status_code=403, detail="Only ai-devops can grant A2A access directly")
    wl_id = str(uuid.uuid4())
    try:
        await db.execute(
            """INSERT OR REPLACE INTO a2a_whitelist
               (id, requester_team_id, target_agent_id, requested_by, granted_by, status)
               VALUES (?,?,?,?,?,'approved')""",
            wl_id, body.requester_team_id, body.target_agent_id,
            body.requested_by, body.requested_by,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"message": "A2A access granted"}


@router.get("/whitelist/{team_id}")
async def list_team_whitelist(team_id: str):
    rows = await db.fetch(
        """
        SELECT w.id, w.granted_by, w.status, w.created_at,
               ar.agent_name, ar.display_name as agent_display_name,
               t.name as target_team_name
        FROM a2a_whitelist w
        JOIN agent_registrations ar ON ar.id=w.target_agent_id
        JOIN teams t ON t.id=ar.team_id
        WHERE w.requester_team_id=? AND w.status='approved'
        ORDER BY t.name, ar.agent_name
        """,
        team_id,
    )
    return {"whitelist": rows}
