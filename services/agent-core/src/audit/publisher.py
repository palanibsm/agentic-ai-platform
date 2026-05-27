"""
Audit event publisher — emits structured events to Cloud Pub/Sub.
Every agent action must produce an audit event (CLAUDE.md requirement).
Falls back to stdout logging when GCP is unavailable (local dev).
"""

import json
import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

PUBSUB_TOPIC = os.getenv("PUBSUB_TOPIC_AUDIT_EVENTS", "audit-events")
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "")

_publisher = None
_topic_path = None


def _get_publisher():
    global _publisher, _topic_path
    if _publisher is not None:
        return _publisher, _topic_path
    if not GCP_PROJECT_ID:
        return None, None
    try:
        from google.cloud import pubsub_v1
        _publisher = pubsub_v1.PublisherClient()
        _topic_path = _publisher.topic_path(GCP_PROJECT_ID, PUBSUB_TOPIC)
        return _publisher, _topic_path
    except Exception as exc:
        logger.warning("Pub/Sub unavailable: %s", exc)
        return None, None


def emit_audit_event(
    event_type: str,
    user_id: str,
    session_id: str,
    payload: dict,
) -> None:
    """
    Publish a single audit event.

    Args:
        event_type: e.g. "agent.run.start", "agent.run.complete", "tool.call"
        user_id: the authenticated user
        session_id: current agent session
        payload: arbitrary JSON-serialisable data
    """
    event = {
        "event_type": event_type,
        "user_id": user_id,
        "session_id": session_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **payload,
    }

    pub, topic_path = _get_publisher()
    if pub is None:
        logger.info("[AUDIT] %s", json.dumps(event))
        return

    try:
        data = json.dumps(event).encode("utf-8")
        future = pub.publish(topic_path, data)
        future.result(timeout=5)
        logger.debug("Audit event published: %s", event_type)
    except Exception as exc:
        # Never let audit failure block the main flow
        logger.error("Failed to publish audit event: %s", exc)
        logger.info("[AUDIT-FALLBACK] %s", json.dumps(event))
