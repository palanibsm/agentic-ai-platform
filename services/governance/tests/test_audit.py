"""Tests for audit store."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.audit.store import record_event, query_events, event_count, _STORE


class TestAuditStore:
    def setup_method(self):
        _STORE.clear()

    def test_record_and_count(self):
        record_event({"event_type": "agent.run.start", "user_id": "u1", "session_id": "s1"})
        assert event_count() == 1

    def test_query_by_event_type(self):
        record_event({"event_type": "agent.run.start", "user_id": "u1", "session_id": "s1"})
        record_event({"event_type": "tool.call", "user_id": "u1", "session_id": "s1"})
        results = query_events(event_type="agent.run")
        assert len(results) == 1
        assert results[0]["event_type"] == "agent.run.start"

    def test_query_by_user(self):
        record_event({"event_type": "agent.run.start", "user_id": "u1", "session_id": "s1"})
        record_event({"event_type": "agent.run.start", "user_id": "u2", "session_id": "s2"})
        results = query_events(user_id="u2")
        assert len(results) == 1
        assert results[0]["user_id"] == "u2"

    def test_most_recent_first(self):
        record_event({"event_type": "agent.run.start", "user_id": "u1", "session_id": "s1"})
        record_event({"event_type": "agent.run.complete", "user_id": "u1", "session_id": "s1"})
        results = query_events()
        assert results[0]["event_type"] == "agent.run.complete"

    def test_limit(self):
        for i in range(10):
            record_event({"event_type": "agent.run.start", "user_id": "u1", "session_id": f"s{i}"})
        results = query_events(limit=3)
        assert len(results) == 3
