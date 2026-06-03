"""Users API — user lookup and role assignment."""

import uuid
import logging
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
from src.db import connection as db
from src.policy.engine import can_manage_platform, can_view_all, ROLE_LEVELS

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/users", tags=["users"])
VALID_ROLES = {"ai-architect", "ai-devops", "app-devops", "business-ops", "ba", "business-user"}


class UserCreate(BaseModel):
    email: str
    display_name: Optional[str] = None
    role: str
    team_id: Optional[str] = None


class UserRoleUpdate(BaseModel):
    role: str
    team_id: Optional[str] = None


@router.get("/me")
async def get_me(x_user_email: str = Header(default=""), x_user_role: str = Header(default="business-user")):
    if not x_user_email:
        return {"email": "unknown", "role": "business-user", "team_id": None}
    row = await db.fetchrow(
        "SELECT u.id, u.email, u.display_name, u.role, u.team_id, u.is_active, t.name as team_name, u.created_at FROM users u LEFT JOIN teams t ON t.id=u.team_id WHERE u.email=?",
        x_user_email,
    )
    if not row:
        return {"email": x_user_email, "role": "business-user", "team_id": None, "team_name": None, "registered": False}
    return {**row, "registered": True}


@router.get("/by-email/{email}")
async def get_user_by_email(email: str):
    row = await db.fetchrow(
        "SELECT u.id, u.email, u.display_name, u.role, u.team_id, u.is_active, t.name as team_name FROM users u LEFT JOIN teams t ON t.id=u.team_id WHERE u.email=? AND u.is_active=1",
        email,
    )
    if not row:
        return {"email": email, "role": "business-user", "team_id": None, "team_name": None}
    return row


@router.get("")
async def list_users(x_user_role: str = Header(default="business-user")):
    if not can_view_all(x_user_role):
        raise HTTPException(status_code=403, detail="Insufficient role")
    return await db.fetch(
        "SELECT u.id, u.email, u.display_name, u.role, u.team_id, u.is_active, t.name as team_name, u.created_at FROM users u LEFT JOIN teams t ON t.id=u.team_id ORDER BY u.email"
    )


@router.post("", status_code=201)
async def create_user(body: UserCreate, x_user_role: str = Header(default="business-user")):
    if not can_manage_platform(x_user_role):
        raise HTTPException(status_code=403, detail="Only ai-devops can register users")
    if body.role not in VALID_ROLES:
        raise HTTPException(status_code=422, detail=f"Invalid role. Must be one of: {sorted(VALID_ROLES)}")
    user_id = str(uuid.uuid4())
    try:
        await db.execute(
            "INSERT INTO users (id, email, display_name, role, team_id) VALUES (?,?,?,?,?)",
            user_id, body.email, body.display_name, body.role, body.team_id,
        )
    except Exception as e:
        if "unique" in str(e).lower():
            raise HTTPException(status_code=409, detail=f"User '{body.email}' already exists")
        raise HTTPException(status_code=500, detail=str(e))
    return await db.fetchrow("SELECT id, email, display_name, role, team_id, is_active, created_at FROM users WHERE id=?", user_id)


@router.put("/{user_id}/role")
async def update_user_role(user_id: str, body: UserRoleUpdate, x_user_role: str = Header(default="business-user")):
    if not can_manage_platform(x_user_role):
        raise HTTPException(status_code=403, detail="Only ai-devops can update user roles")
    if body.role not in VALID_ROLES:
        raise HTTPException(status_code=422, detail=f"Invalid role: {body.role}")
    await db.execute(
        "UPDATE users SET role=?, team_id=?, updated_at=datetime('now') WHERE id=?",
        body.role, body.team_id, user_id,
    )
    return {"message": "Role updated", "user_id": user_id, "new_role": body.role}


@router.delete("/{user_id}", status_code=204)
async def deactivate_user(user_id: str, x_user_role: str = Header(default="business-user")):
    if not can_manage_platform(x_user_role):
        raise HTTPException(status_code=403, detail="Only ai-devops can deactivate users")
    await db.execute("UPDATE users SET is_active=0, updated_at=datetime('now') WHERE id=?", user_id)
