"""Teams API — CRUD for platform teams."""

import uuid
import logging
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
from src.db import connection as db
from src.policy.engine import can_manage_platform, can_view_all

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/teams", tags=["teams"])
TEAM_TYPES = {"ai-devops", "app-devops", "business", "platform"}


class TeamCreate(BaseModel):
    name: str
    display_name: str
    description: Optional[str] = None
    team_type: str


class TeamUpdate(BaseModel):
    display_name: Optional[str] = None
    description: Optional[str] = None


def _require_role(user_role: str, write: bool = False):
    if write and not can_manage_platform(user_role):
        raise HTTPException(status_code=403, detail="Only ai-devops can manage teams")
    if not write and not can_view_all(user_role):
        raise HTTPException(status_code=403, detail="Insufficient role to view teams")


@router.get("")
async def list_teams(x_user_role: str = Header(default="business-user")):
    _require_role(x_user_role)
    return await db.fetch("SELECT id, name, display_name, description, team_type, created_at FROM teams ORDER BY name")


@router.get("/{team_id}")
async def get_team(team_id: str, x_user_role: str = Header(default="business-user")):
    _require_role(x_user_role)
    row = await db.fetchrow("SELECT id, name, display_name, description, team_type, created_at FROM teams WHERE id=?", team_id)
    if not row:
        raise HTTPException(status_code=404, detail="Team not found")
    return row


@router.post("", status_code=201)
async def create_team(body: TeamCreate, x_user_role: str = Header(default="business-user")):
    _require_role(x_user_role, write=True)
    if body.team_type not in TEAM_TYPES:
        raise HTTPException(status_code=422, detail=f"team_type must be one of {TEAM_TYPES}")
    team_id = str(uuid.uuid4())
    try:
        await db.execute(
            "INSERT INTO teams (id, name, display_name, description, team_type) VALUES (?,?,?,?,?)",
            team_id, body.name, body.display_name, body.description, body.team_type,
        )
    except Exception as e:
        if "unique" in str(e).lower():
            raise HTTPException(status_code=409, detail=f"Team '{body.name}' already exists")
        raise HTTPException(status_code=500, detail=str(e))
    return await db.fetchrow("SELECT id, name, display_name, description, team_type, created_at FROM teams WHERE id=?", team_id)


@router.put("/{team_id}")
async def update_team(team_id: str, body: TeamUpdate, x_user_role: str = Header(default="business-user")):
    _require_role(x_user_role, write=True)
    await db.execute(
        "UPDATE teams SET display_name=COALESCE(?,display_name), description=COALESCE(?,description), updated_at=datetime('now') WHERE id=?",
        body.display_name, body.description, team_id,
    )
    row = await db.fetchrow("SELECT id, name, display_name, description, team_type, created_at FROM teams WHERE id=?", team_id)
    if not row:
        raise HTTPException(status_code=404, detail="Team not found")
    return row


@router.delete("/{team_id}", status_code=204)
async def delete_team(team_id: str, x_user_role: str = Header(default="business-user")):
    _require_role(x_user_role, write=True)
    await db.execute("DELETE FROM teams WHERE id=?", team_id)


@router.get("/{team_id}/agents")
async def list_team_agents(team_id: str, x_user_role: str = Header(default="business-user")):
    return await db.fetch(
        "SELECT id, agent_name, display_name, description, skills, model, service_url, is_public, is_active, created_at FROM agent_registrations WHERE team_id=? ORDER BY agent_name",
        team_id,
    )
