"""
Integration test configuration.

Service URLs are loaded from environment variables so the same tests
run against local Docker Compose or live Cloud Run.

Local:
    AGENT_CORE_URL=http://localhost:8002
    RAG_SERVICE_URL=http://localhost:8001
    GOVERNANCE_URL=http://localhost:8003

Cloud Run (set in CI secrets or .env):
    AGENT_CORE_URL=https://agent-core-hcm6dgvcaq-uc.a.run.app
    RAG_SERVICE_URL=https://rag-service-hcm6dgvcaq-uc.a.run.app
    GOVERNANCE_URL=https://governance-hcm6dgvcaq-uc.a.run.app
"""

import os
import pytest
import httpx

# ── Service base URLs ─────────────────────────────────────────────────────────

AGENT_CORE_URL  = os.getenv("AGENT_CORE_URL",  "http://localhost:8002")
RAG_SERVICE_URL = os.getenv("RAG_SERVICE_URL", "http://localhost:8001")
GOVERNANCE_URL  = os.getenv("GOVERNANCE_URL",  "http://localhost:8003")

# Generous timeout — LLM calls can be slow
DEFAULT_TIMEOUT = float(os.getenv("TEST_TIMEOUT", "120"))


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def agent_client():
    with httpx.Client(base_url=AGENT_CORE_URL, timeout=DEFAULT_TIMEOUT) as client:
        yield client


@pytest.fixture(scope="session")
def rag_client():
    with httpx.Client(base_url=RAG_SERVICE_URL, timeout=DEFAULT_TIMEOUT) as client:
        yield client


@pytest.fixture(scope="session")
def governance_client():
    with httpx.Client(base_url=GOVERNANCE_URL, timeout=DEFAULT_TIMEOUT) as client:
        yield client
