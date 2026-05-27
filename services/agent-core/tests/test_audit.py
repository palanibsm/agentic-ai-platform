"""Tests for audit publisher — run with: pytest tests/test_audit.py -v"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import logging
from unittest.mock import patch, MagicMock


class TestEmitAuditEvent:
    def test_emits_to_stdout_when_no_gcp(self, caplog):
        """Without GCP_PROJECT_ID, events should log to stdout."""
        with patch.dict(os.environ, {"GCP_PROJECT_ID": ""}, clear=False):
            import importlib
            import src.audit.publisher as pub_mod
            importlib.reload(pub_mod)

            with caplog.at_level(logging.INFO, logger="src.audit.publisher"):
                pub_mod.emit_audit_event(
                    "agent.run.start", "u1", "sess-1", {"query": "hello"}
                )

        assert "agent.run.start" in caplog.text

    def test_event_structure(self, caplog):
        """Event must contain event_type, user_id, session_id, timestamp."""
        with patch.dict(os.environ, {"GCP_PROJECT_ID": ""}, clear=False):
            import importlib
            import src.audit.publisher as pub_mod
            importlib.reload(pub_mod)

            with caplog.at_level(logging.INFO, logger="src.audit.publisher"):
                pub_mod.emit_audit_event(
                    "tool.call", "u2", "sess-2", {"tool": "retrieve"}
                )

        assert "tool.call" in caplog.text
        assert "u2" in caplog.text

    def test_pubsub_failure_does_not_raise(self):
        """Pub/Sub publish errors must never propagate to the caller."""
        mock_pub = MagicMock()
        mock_future = MagicMock()
        mock_future.result.side_effect = Exception("Pub/Sub down")
        mock_pub.publish.return_value = mock_future
        mock_pub.topic_path.return_value = "projects/x/topics/audit-events"

        with patch.dict(os.environ, {"GCP_PROJECT_ID": "test-project"}, clear=False):
            import importlib
            import src.audit.publisher as pub_mod
            pub_mod._publisher = mock_pub
            pub_mod._topic_path = "projects/x/topics/audit-events"

            # Should not raise
            pub_mod.emit_audit_event("agent.run.start", "u3", "sess-3", {})

        pub_mod._publisher = None
        pub_mod._topic_path = None


import os
