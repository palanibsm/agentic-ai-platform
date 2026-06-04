"""
Session memory — short-term conversation history.

Storage strategy:
  - If REDIS_URL is set and Redis is reachable: use Redis (list of JSON messages, TTL 2h)
  - Otherwise: in-process dict with manual TTL tracking (prototype fallback)

Message format (stored as JSON strings in Redis list / in-memory list):
  {"role": "user"|"assistant"|"tool", "content": "...", "tool_calls": [...]}
"""

import json
import logging
import os
import time
from typing import Any

logger = logging.getLogger(__name__)

REDIS_URL   = os.getenv("REDIS_URL", "")
SESSION_TTL = int(os.getenv("SESSION_TTL_SECONDS", "7200"))   # 2 hours
MAX_MESSAGES = int(os.getenv("MAX_SESSION_MESSAGES", "40"))

# ── Redis client (optional) ───────────────────────────────────────────────────

_redis = None


async def _get_redis():
    """Lazy-init Redis connection. Returns None if unavailable."""
    global _redis
    if _redis is not None:
        return _redis
    if not REDIS_URL:
        return None
    try:
        import redis.asyncio as aioredis
        client = aioredis.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=2)
        await client.ping()
        _redis = client
        logger.info("Redis connected: %s", REDIS_URL)
        return _redis
    except Exception as exc:
        logger.warning("Redis unavailable — using in-memory session store: %s", exc)
        return None


# ── In-memory fallback ────────────────────────────────────────────────────────

_store: dict[str, dict] = {}
# {session_id: {"messages": [...], "expires_at": float}}


def _mem_get(session_id: str) -> list[dict]:
    entry = _store.get(session_id)
    if not entry:
        return []
    if time.time() > entry["expires_at"]:
        del _store[session_id]
        return []
    return entry["messages"]


def _mem_append(session_id: str, messages: list[dict]) -> None:
    existing = _mem_get(session_id)
    combined = existing + messages
    if len(combined) > MAX_MESSAGES:
        combined = combined[-MAX_MESSAGES:]
    _store[session_id] = {
        "messages": combined,
        "expires_at": time.time() + SESSION_TTL,
    }


def _mem_delete(session_id: str) -> None:
    _store.pop(session_id, None)


def _mem_list() -> list[str]:
    now = time.time()
    expired = [sid for sid, v in _store.items() if now > v["expires_at"]]
    for sid in expired:
        del _store[sid]
    return list(_store.keys())


# ── Public API ────────────────────────────────────────────────────────────────

async def get_session(session_id: str) -> list[dict]:
    """Return message history for a session."""
    r = await _get_redis()
    if r:
        try:
            key = f"session:{session_id}"
            raw = await r.lrange(key, 0, -1)
            return [json.loads(m) for m in raw]
        except Exception as exc:
            logger.warning("Redis get_session failed: %s", exc)
    return _mem_get(session_id)


async def append_messages(session_id: str, messages: list[dict]) -> None:
    """Append messages to session history."""
    r = await _get_redis()
    if r:
        try:
            key = f"session:{session_id}"
            pipe = r.pipeline()
            for msg in messages:
                pipe.rpush(key, json.dumps(msg))
            # Trim to max length and refresh TTL
            pipe.ltrim(key, -MAX_MESSAGES, -1)
            pipe.expire(key, SESSION_TTL)
            await pipe.execute()
            return
        except Exception as exc:
            logger.warning("Redis append_messages failed: %s", exc)
    _mem_append(session_id, messages)


async def set_session(session_id: str, messages: list[dict]) -> None:
    """Replace the full session history (used when syncing from agent-core)."""
    r = await _get_redis()
    if r:
        try:
            key = f"session:{session_id}"
            pipe = r.pipeline()
            pipe.delete(key)
            for msg in messages[-MAX_MESSAGES:]:
                pipe.rpush(key, json.dumps(msg))
            pipe.expire(key, SESSION_TTL)
            await pipe.execute()
            return
        except Exception as exc:
            logger.warning("Redis set_session failed: %s", exc)
    if len(messages) > MAX_MESSAGES:
        messages = messages[-MAX_MESSAGES:]
    _store[session_id] = {
        "messages": messages,
        "expires_at": time.time() + SESSION_TTL,
    }


async def delete_session(session_id: str) -> None:
    """Clear a session."""
    r = await _get_redis()
    if r:
        try:
            await r.delete(f"session:{session_id}")
        except Exception as exc:
            logger.warning("Redis delete_session failed: %s", exc)
    _mem_delete(session_id)


async def list_sessions() -> list[str]:
    """List active session IDs (best-effort, in-memory only)."""
    return _mem_list()


async def using_redis() -> bool:
    return (await _get_redis()) is not None
