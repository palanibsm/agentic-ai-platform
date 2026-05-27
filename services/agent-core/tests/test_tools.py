"""Tests for agent tools — run with: pytest tests/test_tools.py -v"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx


class TestRagTool:
    @pytest.mark.asyncio
    async def test_retrieve_returns_formatted_chunks(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "chunks": [
                {"text": "MAS TRM requires...", "score": 0.95, "source": "docs/mas_trm.pdf"},
                {"text": "Governance framework...", "score": 0.88, "source": "docs/gov.pdf"},
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            from src.tools.rag_tool import retrieve
            result = await retrieve.ainvoke({
                "query": "MAS TRM requirements",
                "user_id": "u1",
                "user_role": "developer",
            })

        assert "MAS TRM requires" in result
        assert "0.950" in result
        assert "docs/mas_trm.pdf" in result

    @pytest.mark.asyncio
    async def test_retrieve_no_chunks_returns_message(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {"chunks": []}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            from src.tools.rag_tool import retrieve
            result = await retrieve.ainvoke({"query": "unknown topic"})

        assert result == "No relevant documents found."

    @pytest.mark.asyncio
    async def test_retrieve_http_error_raises(self):
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(
                side_effect=httpx.ConnectError("Connection refused")
            )
            mock_client_cls.return_value = mock_client

            from src.tools.rag_tool import retrieve
            with pytest.raises(httpx.ConnectError):
                await retrieve.ainvoke({"query": "test"})


class TestSkillTools:
    def test_get_current_user_role(self):
        from src.tools.skill_tool import get_current_user_role
        result = get_current_user_role.invoke({"user_role": "architect"})
        assert result == "architect"

    def test_format_banking_response_strips_blanks(self):
        from src.tools.skill_tool import format_banking_response
        raw = "  Line one.  \n\n  Line two.  \n"
        result = format_banking_response.invoke({"text": raw})
        assert "Line one." in result
        assert "Line two." in result
        assert result == "Line one.\nLine two."
