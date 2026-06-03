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
    granted_by: str


class A2ACheckRequest(BaseModel):
    requester_team_id: str
    target_agent_id: str


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


@router.post("/agents", status_code=201)
async def register_agent(body: AgentRegister, x_user_role: str = Header(default="business-user")):
    if not can_manage_team_agents(x_user_role):
        raise HTTPException(status_code=403, detail="app-devops or above required")
    agent_id = str(uuid.uuid4())
    try:
        await db.execute(
            "INSERT INTO agent_registrations (id, team_id, agent_name, display_name, description, skills, model, service_url, is_public) VALUES (?,?,?,?,?,?,?,?,?)",
            agent_id, body.team_id, body.agent_name, body.display_name,
            body.description, json.dumps(body.skills), body.model,
            body.service_url, 1 if body.is_public else 0,
        )
    except Exception as e:
        if "unique" in str(e).lower():
            raise HTTPException(status_code=409, detail="Agent already registered for this team")
        raise HTTPException(status_code=500, detail=str(e))
    return {"id": agent_id, "agent_name": body.agent_name, "status": "registered"}


@router.put("/agents/{agent_id}/url")
async def update_agent_url(agent_id: str, service_url: str, x_user_role: str = Header(default="business-user")):
    if not can_manage_team_agents(x_user_role):
        raise HTTPException(status_code=403, detail="app-devops or above required")
    await db.execute(
        "UPDATE agent_registrations SET service_url=?, updated_at=datetime('now') WHERE id=?",
        service_url, agent_id,
    )
    return {"message": "URL updated"}


@router.post("/check")
async def check_a2a_access(body: A2ACheckRequest):
    row = await db.fetchrow(
        "SELECT w.id FROM a2a_whitelist w JOIN agent_registrations ar ON ar.id=w.target_agent_id WHERE w.requester_team_id=? AND w.target_agent_id=? AND ar.is_active=1",
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


@router.post("/whitelist", status_code=201)
async def grant_a2a_access(body: A2AAccessRequest, x_user_role: str = Header(default="business-user")):
    if not can_manage_platform(x_user_role):
        raise HTTPException(status_code=403, detail="Only ai-devops can grant A2A access")
    wl_id = str(uuid.uuid4())
    try:
        await db.execute(
            "INSERT OR IGNORE INTO a2a_whitelist (id, requester_team_id, target_agent_id, granted_by) VALUES (?,?,?,?)",
            wl_id, body.requester_team_id, body.target_agent_id, body.granted_by,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"message": "A2A access granted"}


@router.get("/whitelist/{team_id}")
async def list_team_whitelist(team_id: str):
    rows = await db.fetch(
        """
        SELECT w.id, w.granted_by, w.created_at,
               ar.agent_name, ar.display_name as agent_display_name,
               t.name as target_team_name
        FROM a2a_whitelist w
        JOIN agent_registrations ar ON ar.id=w.target_agent_id
        JOIN teams t ON t.id=ar.team_id
        WHERE w.requester_team_id=?
        ORDER BY t.name, ar.agent_name
        """,
        team_id,
    )
    return {"whitelist": rows}


@router.delete("/whitelist/{whitelist_id}", status_code=204)
async def revoke_a2a_access(whitelist_id: str, x_user_role: str = Header(default="business-user")):
    if not can_manage_platform(x_user_role):
        raise HTTPException(status_code=403, detail="Only ai-devops can revoke A2A access")
    await db.execute("DELETE FROM a2a_whitelist WHERE id=?", whitelist_id)
