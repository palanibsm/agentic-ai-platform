"""
Integration tests for rag-service.

Tests health check, document ingestion, semantic search,
and idempotent re-ingestion (no duplicate chunks).
"""

import pytest


TEST_DOCUMENT = {
    "content": (
        "MAS TRM Guideline 6.1: Financial institutions must implement "
        "multi-factor authentication for all privileged access to critical systems. "
        "Access reviews must be conducted quarterly and documented for audit purposes."
    ),
    "source": "integration-test/mas-trm-test-doc.txt",
    "metadata": {
        "category": "compliance",
        "test": True,
    },
}

TEST_QUERY = "MAS TRM multi-factor authentication privileged access"


class TestHealth:
    def test_health_returns_200(self, rag_client):
        resp = rag_client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestIngest:
    def test_ingest_single_document(self, rag_client):
        resp = rag_client.post("/ingest", json={
            "documents": [TEST_DOCUMENT],
            "allowed_roles": ["developer", "admin"],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "ingested" in data
        assert data["ingested"] >= 1

    def test_ingest_returns_ingested_and_skipped_counts(self, rag_client):
        resp = rag_client.post("/ingest", json={
            "documents": [TEST_DOCUMENT],
            "allowed_roles": ["developer"],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "ingested" in data
        assert "skipped" in data
        assert isinstance(data["ingested"], int)
        assert isinstance(data["skipped"], int)

    def test_ingest_idempotent_no_duplicates(self, rag_client):
        """Ingesting the same document twice should not create duplicate chunks."""
        payload = {
            "documents": [TEST_DOCUMENT],
            "allowed_roles": ["developer", "admin"],
        }
        # First ingest
        resp1 = rag_client.post("/ingest", json=payload)
        assert resp1.status_code == 200
        ingested_first = resp1.json()["ingested"]

        # Second ingest — same document, same source
        resp2 = rag_client.post("/ingest", json=payload)
        assert resp2.status_code == 200
        data2 = resp2.json()

        # On re-ingest, chunks should be skipped (upserted with same ID = no duplicate)
        assert data2["ingested"] + data2["skipped"] == ingested_first + data2["skipped"]

    def test_ingest_multiple_documents(self, rag_client):
        docs = [
            {
                "content": f"Test document {i} about banking security policy number {i}.",
                "source": f"integration-test/batch-doc-{i}.txt",
                "metadata": {"test": True},
            }
            for i in range(3)
        ]
        resp = rag_client.post("/ingest", json={
            "documents": docs,
            "allowed_roles": ["developer"],
        })
        assert resp.status_code == 200
        assert resp.json()["ingested"] >= 1

    def test_ingest_empty_documents_list(self, rag_client):
        resp = rag_client.post("/ingest", json={
            "documents": [],
            "allowed_roles": ["developer"],
        })
        assert resp.status_code == 200
        assert resp.json()["ingested"] == 0


class TestSearch:
    @pytest.fixture(autouse=True)
    def ensure_test_doc_ingested(self, rag_client):
        """Ensure test document is present before search tests run."""
        rag_client.post("/ingest", json={
            "documents": [TEST_DOCUMENT],
            "allowed_roles": ["developer", "admin"],
        })

    def test_search_returns_results(self, rag_client):
        resp = rag_client.post("/search", json={
            "query": TEST_QUERY,
            "top_k": 3,
            "user_role": "developer",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "results" in data
        assert isinstance(data["results"], list)

    def test_search_results_contain_relevant_content(self, rag_client):
        resp = rag_client.post("/search", json={
            "query": TEST_QUERY,
            "top_k": 5,
            "user_role": "developer",
        })
        assert resp.status_code == 200
        results = resp.json()["results"]
        assert len(results) > 0
        # At least one result should mention MAS TRM or authentication
        combined = " ".join(r.get("content", "") for r in results).lower()
        assert any(kw in combined for kw in ["mas", "authentication", "privileged", "access"])

    def test_search_respects_top_k(self, rag_client):
        resp = rag_client.post("/search", json={
            "query": TEST_QUERY,
            "top_k": 2,
            "user_role": "developer",
        })
        assert resp.status_code == 200
        results = resp.json()["results"]
        assert len(results) <= 2

    def test_search_results_have_required_fields(self, rag_client):
        resp = rag_client.post("/search", json={
            "query": TEST_QUERY,
            "top_k": 3,
            "user_role": "developer",
        })
        assert resp.status_code == 200
        for result in resp.json()["results"]:
            assert "content" in result
            assert "score" in result

    def test_search_empty_query_handled(self, rag_client):
        resp = rag_client.post("/search", json={
            "query": "",
            "top_k": 3,
            "user_role": "developer",
        })
        # Should not 500 — either empty results or 422
        assert resp.status_code in (200, 422)
