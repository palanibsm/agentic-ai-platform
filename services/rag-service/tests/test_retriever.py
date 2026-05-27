"""
Tests for retriever — mocks Vertex AI so no GCP credentials needed.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.pop("GCP_PROJECT_ID", None)

import pytest
from unittest.mock import AsyncMock, patch
from src.retrieval.retriever import retrieve_chunks, register_chunks, _CHUNK_STORE


SAMPLE_CHUNKS = [
    {
        "id": "chunk-001",
        "text": "MAS TRM requires encryption of data at rest and in transit.",
        "source": "gs://bucket/mas-trm.md",
        "chunk_index": 0,
        "metadata": {"allowed_roles": ["developer", "architect"]},
    },
    {
        "id": "chunk-002",
        "text": "LangGraph supports stateful multi-agent orchestration.",
        "source": "gs://bucket/langgraph-docs.md",
        "chunk_index": 1,
        "metadata": {"allowed_roles": ["developer"]},
    },
]


@pytest.fixture(autouse=True)
def seed_chunk_store():
    """Pre-load chunks into the in-memory store before each test."""
    _CHUNK_STORE.clear()
    register_chunks(SAMPLE_CHUNKS)
    yield
    _CHUNK_STORE.clear()


@pytest.mark.asyncio
async def test_retrieve_returns_chunks():
    mock_neighbors = [
        {"id": "chunk-001", "distance": 0.1},
        {"id": "chunk-002", "distance": 0.3},
    ]
    with patch("src.retrieval.retriever.query_index", new=AsyncMock(return_value=mock_neighbors)):
        results = await retrieve_chunks(
            query="What does MAS TRM say about encryption?",
            top_k=2,
            user_id="user-123",
            user_roles=["developer"],
        )
    assert len(results) == 2
    assert results[0]["score"] > results[1]["score"]   # sorted by score desc


@pytest.mark.asyncio
async def test_retrieve_empty_when_no_neighbors():
    with patch("src.retrieval.retriever.query_index", new=AsyncMock(return_value=[])):
        results = await retrieve_chunks(query="anything", user_roles=["developer"])
    assert results == []


@pytest.mark.asyncio
async def test_retrieve_score_is_1_minus_distance():
    mock_neighbors = [{"id": "chunk-001", "distance": 0.25}]
    with patch("src.retrieval.retriever.query_index", new=AsyncMock(return_value=mock_neighbors)):
        results = await retrieve_chunks(query="test", user_roles=["developer"])
    assert results[0]["score"] == round(1.0 - 0.25, 4)


@pytest.mark.asyncio
async def test_retrieve_chunk_text_from_store():
    mock_neighbors = [{"id": "chunk-001", "distance": 0.1}]
    with patch("src.retrieval.retriever.query_index", new=AsyncMock(return_value=mock_neighbors)):
        results = await retrieve_chunks(query="encryption", user_roles=["developer"])
    assert "encryption" in results[0]["text"]
    assert results[0]["source"] == "gs://bucket/mas-trm.md"
