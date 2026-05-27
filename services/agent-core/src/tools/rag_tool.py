"""
RAG tool — calls rag-service /retrieve endpoint.
Used as a LangChain tool inside the LangGraph agent node.
"""

import os
import httpx
from langchain_core.tools import tool


RAG_SERVICE_URL = os.getenv("RAG_SERVICE_URL", "http://localhost:8001")


@tool
async def retrieve(query: str, user_id: str = "", user_role: str = "developer") -> str:
    """
    Retrieve relevant knowledge-base chunks for a query.
    Use this whenever you need factual context from internal documents.

    Args:
        query: The search query string.
        user_id: Caller's user ID (for access-control logging).
        user_role: Caller's role (developer / architect / admin).

    Returns:
        Formatted string of the top retrieved chunks.
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{RAG_SERVICE_URL}/retrieve",
                json={"query": query, "top_k": 5, "user_id": user_id, "user_roles": [user_role]},
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.TimeoutException:
        return "Knowledge base retrieval timed out. Please answer from general knowledge if possible."
    except httpx.HTTPError as e:
        return f"Knowledge base unavailable ({e}). Please answer from general knowledge if possible."

    chunks = data.get("chunks", [])
    if not chunks:
        return "No relevant documents found."

    lines = []
    for i, chunk in enumerate(chunks, 1):
        score = chunk.get("score", 0)
        source = chunk.get("source", "unknown")
        text = chunk.get("text", "")
        lines.append(f"[{i}] (score={score:.3f}, source={source})\n{text}")

    return "\n\n".join(lines)
