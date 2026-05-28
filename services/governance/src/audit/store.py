"""
Audit log store.
In production: subscribes to Cloud Pub/Sub audit-events topic.
For local dev: maintains an in-memory ring buffer (last 1000 events).
"""

import json
import logging
import os
from collections import deque
from datetime import datetime, timezone
logger = logging.getLogger(__name__)

_STORE: deque[dict] = deque(maxlen=1000)   # in-memory fallback

GCP_PROJECT_ID  = os.getenv("GCP_PROJECT_ID", "")
PUBSUB_SUB_NAME = os.getenv("PUBSUB_SUB_AUDIT", "audit-events-governance-sub")


def record_event(event: dict) -> None:
    """Append an audit event to the in-memory store."""
    _STORE.append({**event, "_received_at": datetime.now(timezone.utc).isoformat()})


def query_events(
    event_type: str | None = None,
    user_id: str | None = None,
    limit: int = 100,
) -> list[dict]:
    """
    Query the in-memory audit log.

    Args:
        event_type: filter by event type prefix (e.g. "agent.run")
        user_id: filter by user
        limit: max events to return (most recent first)
    """
    results = list(_STORE)

    if event_type:
        results = [e for e in results if e.get("event_type", "").startswith(event_type)]
    if user_id:
        results = [e for e in results if e.get("user_id") == user_id]

    return list(reversed(results))[:limit]


def event_count() -> int:
    return len(_STORE)
