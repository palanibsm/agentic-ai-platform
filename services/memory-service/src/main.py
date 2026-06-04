"""
memory-service — FastAPI entry point.

Endpoints:
  Session memory (short-term, Redis + in-memory fallback):
    GET    /session/{session_id}           — get message history
    POST   /session/{session_id}           — set full history (from agent-core)
    DELETE /session/{session_id}           — clear session

  Long-term memory (SQLite, per user):
    GET    /longterm/{user_id}             — list memories
    POST   /longterm/{user_id}             — add memory
    DELETE /longterm/{user_id}/{memory_id} — delete memory
    DELETE /longterm/{user_id}             — clear all

  Team memory (SQLite, shared per team):
    GET    /team/{team_id}                 — list team memories
    POST   /team/{team_id}                 — add team memory
    DELETE /team/{team_id}/{memory_id}     — delete team memory
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

try:
    from dotenv import load_dotenv
    load_dotenv(override=False)
except ImportError:
    pass

from src import session as sess
from src import longterm as lt

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ── Schemas ───────────────────────────────────────────────────────────────────

class Message(BaseModel):
    role: str          # user | assistant | tool | system
    content: str
    tool_calls: list   = []
    tool_call_id: str | None = None


class SetSessionRequest(BaseModel):
    messages: list[Message]


class MemoryCreate(BaseModel):
    content: str
    category: str = "fact"    # preference | fact | instruction | context
    source: str   = "manual"  # manual | auto-extracted


class TeamMemoryCreate(BaseModel):
    content: str
    category: str  = "fact"
    created_by: str | None = None


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    await lt.init_db()
    logger.info("memory-service ready")
    yield
    await lt.close_db()


app = FastAPI(
    title="memory-service",
    description="Short-term session memory and long-term user/team memory for Agentic AI Platform",
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


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    redis_ok = await sess.using_redis()
    return {
        "status": "ok",
        "service": "memory-service",
        "version": "0.1.0",
        "session_backend": "redis" if redis_ok else "in-memory",
    }


# ── Session memory ────────────────────────────────────────────────────────────

@app.get("/session/{session_id}")
async def get_session(session_id: str):
    messages = await sess.get_session(session_id)
    return {"session_id": session_id, "messages": messages, "count": len(messages)}


@app.post("/session/{session_id}", status_code=200)
async def set_session(session_id: str, body: SetSessionRequest):
    """Replace the full session history. Called by agent-core after each run."""
    msgs = [m.model_dump() for m in body.messages]
    await sess.set_session(session_id, msgs)
    return {"session_id": session_id, "count": len(msgs)}


@app.delete("/session/{session_id}", status_code=204)
async def delete_session(session_id: str):
    await sess.delete_session(session_id)


# ── Long-term memory ──────────────────────────────────────────────────────────

@app.get("/longterm/{user_id}")
async def list_memories(
    user_id: str,
    category: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    memories = await lt.get_memories(user_id, category=category, limit=limit)
    return {"user_id": user_id, "memories": memories, "count": len(memories)}


@app.post("/longterm/{user_id}", status_code=201)
async def add_memory(user_id: str, body: MemoryCreate):
    mem = await lt.add_memory(
        user_id=user_id,
        content=body.content,
        category=body.category,
        source=body.source,
    )
    return mem


@app.delete("/longterm/{user_id}/{memory_id}", status_code=204)
async def delete_memory(user_id: str, memory_id: str):
    deleted = await lt.delete_memory(memory_id, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Memory not found")


@app.delete("/longterm/{user_id}", status_code=200)
async def clear_memories(user_id: str):
    count = await lt.clear_user_memories(user_id)
    return {"deleted": count}


# ── Team memory ───────────────────────────────────────────────────────────────

@app.get("/team/{team_id}")
async def list_team_memories(
    team_id: str,
    category: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    memories = await lt.get_team_memories(team_id, category=category, limit=limit)
    return {"team_id": team_id, "memories": memories, "count": len(memories)}


@app.post("/team/{team_id}", status_code=201)
async def add_team_memory(team_id: str, body: TeamMemoryCreate):
    mem = await lt.add_team_memory(
        team_id=team_id,
        content=body.content,
        category=body.category,
        created_by=body.created_by,
    )
    return mem


@app.delete("/team/{team_id}/{memory_id}", status_code=204)
async def delete_team_memory(team_id: str, memory_id: str):
    deleted = await lt.delete_team_memory(memory_id, team_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Memory not found")
