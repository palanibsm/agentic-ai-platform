"""
Integration tests for agent-core.

Tests health, skills discovery, run endpoint with/without skills,
role enforcement, and graceful unknown skill fallback.

Note: LLM calls are made against the live service. Tests use short,
fast queries to keep costs and latency low.
"""

import pytest


FAST_QUERY = "What is your purpose? Reply in one sentence."


class TestHealth:
    def test_health_returns_200(self, agent_client):
        resp = agent_client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["service"] == "agent-core"


class TestSkillsEndpoint:
    def test_skills_returns_200(self, agent_client):
        resp = agent_client.get("/skills")
        assert resp.status_code == 200

    def test_skills_returns_all_eight(self, agent_client):
        resp = agent_client.get("/skills")
        skills = resp.json()["skills"]
        assert len(skills) == 8

    def test_skills_have_required_fields(self, agent_client):
        resp = agent_client.get("/skills")
        for skill in resp.json()["skills"]:
            assert "name" in skill
            assert "display_name" in skill
            assert "description" in skill
            assert "allowed_roles" in skill

    def test_expected_skill_names_present(self, agent_client):
        resp = agent_client.get("/skills")
        names = {s["name"] for s in resp.json()["skills"]}
        expected = {
            "secure-coding", "banking-compliance", "terraform-iac",
            "threat-modeling", "api-standards", "data-privacy",
            "cloud-architecture", "incident-response",
        }
        assert expected == names


class TestRunNoSkill:
    def test_run_returns_200(self, agent_client):
        resp = agent_client.post("/run", json={
            "query": FAST_QUERY,
            "user_id": "test-user",
            "user_role": "developer",
        })
        assert resp.status_code == 200

    def test_run_returns_answer(self, agent_client):
        resp = agent_client.post("/run", json={
            "query": FAST_QUERY,
            "user_id": "test-user",
            "user_role": "developer",
        })
        data = resp.json()
        assert "answer" in data
        assert len(data["answer"]) > 0

    def test_run_returns_session_id(self, agent_client):
        resp = agent_client.post("/run", json={
            "query": FAST_QUERY,
            "user_id": "test-user",
            "user_role": "developer",
        })
        data = resp.json()
        assert "session_id" in data
        assert len(data["session_id"]) > 0

    def test_run_returns_tool_calls_list(self, agent_client):
        resp = agent_client.post("/run", json={
            "query": FAST_QUERY,
            "user_id": "test-user",
            "user_role": "developer",
        })
        data = resp.json()
        assert "tool_calls_made" in data
        assert isinstance(data["tool_calls_made"], list)

    def test_run_session_continuity(self, agent_client):
        """Second message in same session should maintain context."""
        session_id = "test-session-continuity"
        agent_client.post("/run", json={
            "query": "My name is TestUser.",
            "user_id": "test-user",
            "user_role": "developer",
            "session_id": session_id,
        })
        resp2 = agent_client.post("/run", json={
            "query": "What is my name?",
            "user_id": "test-user",
            "user_role": "developer",
            "session_id": session_id,
        })
        assert resp2.status_code == 200
        assert "testuser" in resp2.json()["answer"].lower()


class TestRunWithSkill:
    def test_run_with_secure_coding_skill(self, agent_client):
        resp = agent_client.post("/run", json={
            "query": "What security checks do you perform?",
            "user_id": "test-user",
            "user_role": "developer",
            "skill": "secure-coding",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["answer"]) > 0

    def test_run_with_banking_compliance_skill(self, agent_client):
        resp = agent_client.post("/run", json={
            "query": "What MAS TRM controls do you check?",
            "user_id": "test-user",
            "user_role": "developer",
            "skill": "banking-compliance",
        })
        assert resp.status_code == 200
        assert len(resp.json()["answer"]) > 0

    def test_run_skill_answer_reflects_skill_context(self, agent_client):
        """Answer with secure-coding skill should mention security concepts."""
        resp = agent_client.post("/run", json={
            "query": "What is your purpose?",
            "user_id": "test-user",
            "user_role": "developer",
            "skill": "secure-coding",
        })
        assert resp.status_code == 200
        answer = resp.json()["answer"].lower()
        assert any(kw in answer for kw in [
            "security", "vulnerabilit", "owasp", "code", "review", "secure"
        ])


class TestRoleEnforcement:
    def test_developer_blocked_from_threat_modeling(self, agent_client):
        resp = agent_client.post("/run", json={
            "query": "Threat model our payment system",
            "user_id": "test-user",
            "user_role": "developer",
            "skill": "threat-modeling",
        })
        # Governance returns 403 or agent returns access denied answer
        assert resp.status_code in (200, 403)
        if resp.status_code == 200:
            assert "denied" in resp.json()["answer"].lower() or \
                   "not permitted" in resp.json()["answer"].lower()

    def test_developer_blocked_from_cloud_architecture(self, agent_client):
        resp = agent_client.post("/run", json={
            "query": "Review our cloud architecture",
            "user_id": "test-user",
            "user_role": "developer",
            "skill": "cloud-architecture",
        })
        assert resp.status_code in (200, 403)
        if resp.status_code == 200:
            assert "denied" in resp.json()["answer"].lower() or \
                   "not permitted" in resp.json()["answer"].lower()

    def test_architect_allowed_for_cloud_architecture(self, agent_client):
        resp = agent_client.post("/run", json={
            "query": "What do you review in a cloud architecture?",
            "user_id": "test-user",
            "user_role": "architect",
            "skill": "cloud-architecture",
        })
        assert resp.status_code == 200
        assert len(resp.json()["answer"]) > 0


class TestEdgeCases:
    def test_unknown_skill_falls_back_gracefully(self, agent_client):
        resp = agent_client.post("/run", json={
            "query": FAST_QUERY,
            "user_id": "test-user",
            "user_role": "developer",
            "skill": "nonexistent-skill",
        })
        assert resp.status_code == 200
        assert len(resp.json()["answer"]) > 0

    def test_empty_session_id_generates_new_session(self, agent_client):
        resp = agent_client.post("/run", json={
            "query": FAST_QUERY,
            "user_id": "test-user",
            "user_role": "developer",
            "session_id": None,
        })
        assert resp.status_code == 200
        assert len(resp.json()["session_id"]) > 0

    def test_missing_user_id_uses_default(self, agent_client):
        resp = agent_client.post("/run", json={
            "query": FAST_QUERY,
            "user_role": "developer",
        })
        assert resp.status_code == 200
