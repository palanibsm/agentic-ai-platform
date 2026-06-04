"""
Long-term memory — persistent per-user facts and preferences.

Stored in SQLite. Each memory entry has:
  - user_id   (email or user identifier)
  - content   (the memory text)
  - category  (preference | fact | instruction | context)
  - source    (how it was created: manual | auto-extracted)
  - created_at

Auto-extraction: agent-core can POST memories after runs when it detects
  user preferences or important facts in the conversation.
"""

import aiosqlite
import os
import uuid
import logging
from typing import Optional

logger = logging.getLogger(__name__)

DB_PATH = os.getenv("LONGTERM_DB_PATH", "/app/data/memory.db")

_db: aiosqlite.Connection | None = None


async def init_db() -> None:
    global _db
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    _db = await aiosqlite.connect(DB_PATH)
    _db.row_factory = aiosqlite.Row
    await _db.execute("PRAGMA journal_mode=WAL")
    await _db.executescript("""
        CREATE TABLE IF NOT EXISTS longterm_memories (
            id         TEXT PRIMARY KEY,
            user_id    TEXT NOT NULL,
            content    TEXT NOT NULL,
            category   TEXT NOT NULL DEFAULT 'fact'
                           CHECK (category IN ('preference','fact','instruction','context')),
            source     TEXT NOT NULL DEFAULT 'manual'
                           CHECK (source IN ('manual','auto-extracted')),
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_lt_user ON longterm_memories(user_id);
        CREATE INDEX IF NOT EXISTS idx_lt_category ON longterm_memories(category);

        CREATE TABLE IF NOT EXISTS team_memories (
            id         TEXT PRIMARY KEY,
            team_id    TEXT NOT NULL,
            content    TEXT NOT NULL,
            category   TEXT NOT NULL DEFAULT 'fact'
                           CHECK (category IN ('preference','fact','instruction','context','sop')),
            created_by TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_tm_team ON team_memories(team_id);
    """)
    await _db.commit()
    logger.info("Long-term memory DB initialised: %s", DB_PATH)


async def close_db() -> None:
    global _db
    if _db:
        await _db.close()
        _db = None


def _conn():
    if _db is None:
        raise RuntimeError("DB not initialised")
    return _db


# ── Long-term memory (per user) ───────────────────────────────────────────────

async def add_memory(
    user_id: str,
    content: str,
    category: str = "fact",
    source: str = "manual",
) -> dict:
    mem_id = str(uuid.uuid4())
    await _conn().execute(
        "INSERT INTO longterm_memories (id, user_id, content, category, source) VALUES (?,?,?,?,?)",
        (mem_id, user_id, content, category, source),
    )
    await _conn().commit()
    return {"id": mem_id, "user_id": user_id, "content": content, "category": category, "source": source}


async def get_memories(user_id: str, category: Optional[str] = None, limit: int = 50) -> list[dict]:
    if category:
        async with _conn().execute(
            "SELECT * FROM longterm_memories WHERE user_id=? AND category=? ORDER BY created_at DESC LIMIT ?",
            (user_id, category, limit),
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]
    async with _conn().execute(
        "SELECT * FROM longterm_memories WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
        (user_id, limit),
    ) as cur:
        return [dict(r) for r in await cur.fetchall()]


async def delete_memory(memory_id: str, user_id: str) -> bool:
    async with _conn().execute(
        "DELETE FROM longterm_memories WHERE id=? AND user_id=?", (memory_id, user_id)
    ) as cur:
        await _conn().commit()
        return cur.rowcount > 0


async def clear_user_memories(user_id: str) -> int:
    async with _conn().execute(
        "DELETE FROM longterm_memories WHERE user_id=?", (user_id,)
    ) as cur:
        await _conn().commit()
        return cur.rowcount


# ── Team memory (shared) ──────────────────────────────────────────────────────

async def add_team_memory(
    team_id: str,
    content: str,
    category: str = "fact",
    created_by: Optional[str] = None,
) -> dict:
    mem_id = str(uuid.uuid4())
    await _conn().execute(
        "INSERT INTO team_memories (id, team_id, content, category, created_by) VALUES (?,?,?,?,?)",
        (mem_id, team_id, content, category, created_by),
    )
    await _conn().commit()
    return {"id": mem_id, "team_id": team_id, "content": content, "category": category}


async def get_team_memories(team_id: str, category: Optional[str] = None, limit: int = 50) -> list[dict]:
    if category:
        async with _conn().execute(
            "SELECT * FROM team_memories WHERE team_id=? AND category=? ORDER BY created_at DESC LIMIT ?",
            (team_id, category, limit),
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]
    async with _conn().execute(
        "SELECT * FROM team_memories WHERE team_id=? ORDER BY created_at DESC LIMIT ?",
        (team_id, limit),
    ) as cur:
        return [dict(r) for r in await cur.fetchall()]


async def delete_team_memory(memory_id: str, team_id: str) -> bool:
    async with _conn().execute(
        "DELETE FROM team_memories WHERE id=? AND team_id=?", (memory_id, team_id)
    ) as cur:
        await _conn().commit()
        return cur.rowcount > 0
