"""Tests for the LangGraph agent graph — run with: pytest tests/test_graph.py -v"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from langchain_core.messages import HumanMessage, AIMessage

from src.graph.state import AgentState


class TestAgentState:
    def test_default_state(self):
        state = AgentState()
        assert state.messages == []
        assert state.user_role == "developer"
        assert state.finished is False
        assert state.retrieved_chunks == []

    def test_state_with_values(self):
        state = AgentState(
            user_id="u1",
            user_role="architect",
            session_id="sess-123",
            skill="banking-compliance",
        )
        assert state.user_id == "u1"
        assert state.user_role == "architect"
        assert state.skill == "banking-compliance"


class TestRunAgent:
    @pytest.mark.asyncio
    async def test_run_agent_returns_answer(self):
        """Graph should return a dict with answer, session_id, tool_calls_made."""
        fake_answer = AIMessage(content="Here is the answer.")
        fake_graph = AsyncMock()
        fake_graph.ainvoke.return_value = {
            "messages": [HumanMessage(content="q"), fake_answer],
            "session_id": "sess-1",
            "tool_calls_made": [],
            "finished": True,
        }

        with patch("src.graph.agent.graph", fake_graph), \
             patch("src.graph.agent.emit_audit_event"):
            from src.graph.agent import run_agent
            result = await run_agent(
                query="What is MAS TRM?",
                user_id="u1",
                session_id="sess-1",
            )

        assert result["answer"] == "Here is the answer."
        assert result["session_id"] == "sess-1"
        assert isinstance(result["tool_calls_made"], list)

    @pytest.mark.asyncio
    async def test_run_agent_empty_query_still_runs(self):
        fake_answer = AIMessage(content="Please provide a question.")
        fake_graph = AsyncMock()
        fake_graph.ainvoke.return_value = {
            "messages": [fake_answer],
            "session_id": "sess-2",
            "tool_calls_made": [],
            "finished": True,
        }

        with patch("src.graph.agent.graph", fake_graph), \
             patch("src.graph.agent.emit_audit_event"):
            from src.graph.agent import run_agent
            result = await run_agent(query="", user_id="u2", session_id="sess-2")

        assert "answer" in result

    @pytest.mark.asyncio
    async def test_audit_events_emitted(self):
        fake_answer = AIMessage(content="Done.")
        fake_graph = AsyncMock()
        fake_graph.ainvoke.return_value = {
            "messages": [fake_answer],
            "session_id": "sess-3",
            "tool_calls_made": [],
            "finished": True,
        }

        with patch("src.graph.agent.graph", fake_graph), \
             patch("src.graph.agent.emit_audit_event") as mock_emit:
            from src.graph.agent import run_agent
            await run_agent(query="Hello", user_id="u3", session_id="sess-3")

        # start + complete audit events
        assert mock_emit.call_count >= 2
        event_types = [call.args[0] for call in mock_emit.call_args_list]
        assert "agent.run.start" in event_types
        assert "agent.run.complete" in event_types
