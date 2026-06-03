"""
Policy engine — centralised RBAC and MAS TRM compliance rules.

Six-role model:
  ai-architect   — read-only across all platform resources
  ai-devops      — full platform management (infra, models, MCPs, governance)
  app-devops     — manage their own team's agents and consume platform services
  business-ops   — configure and run AI-assisted workflows
  ba             — submit requirements, view agent capabilities
  business-user  — use agents via chat and forms

Role hierarchy (higher number = more privilege):
  business-user(0) < ba(1) < business-ops(2) < app-devops(3) < ai-devops(4) < ai-architect(5)

Note: ai-architect has the highest level but READ-ONLY access.
      Mutating operations require ai-devops (level 4) or app-devops (level 3, scoped to their team).
"""

from dataclasses import dataclass, field


@dataclass
class PolicyResult:
    allowed: bool
    reason: str
    violations: list[str] = field(default_factory=list)


# ── Role hierarchy ─────────────────────────────────────────────────────────────

ROLE_LEVELS: dict[str, int] = {
    "business-user":  0,
    "ba":             1,
    "business-ops":   2,
    "app-devops":     3,
    "ai-devops":      4,
    "ai-architect":   5,
    # Legacy role aliases kept for backward compatibility
    "developer":      3,   # maps to app-devops
    "senior-engineer": 3,
    "architect":      4,   # maps to ai-devops
    "admin":          4,
    "viewer":         0,
}

# ── Skill access control ───────────────────────────────────────────────────────
# Maps skill name → minimum role required.
# ai-architect can access all skills (read/evaluate only).
# app-devops can access technical skills for their agents.
# business-ops can access compliance/process skills.

SKILL_MIN_ROLE: dict[str, str] = {
    # Technical skills — app-devops and above
    "secure-coding":      "app-devops",
    "terraform-iac":      "app-devops",
    "api-standards":      "app-devops",
    # Compliance/process skills — business-ops and above
    "banking-compliance": "business-ops",
    "data-privacy":       "business-ops",
    "incident-response":  "business-ops",
    # Architect-level skills — ai-devops and above
    "threat-modeling":    "ai-devops",
    "cloud-architecture": "ai-devops",
    # Legacy
    "code-review":        "app-devops",
    "rag-search":         "business-user",
}

# ── Platform operation access control ─────────────────────────────────────────
# Maps operation → minimum role required.

OPERATION_MIN_ROLE: dict[str, str] = {
    # Platform management (AI DevOps only)
    "manage_models":       "ai-devops",
    "manage_mcps":         "ai-devops",
    "manage_platform":     "ai-devops",
    "manage_governance":   "ai-devops",
    "view_all_teams":      "ai-devops",
    # Team agent management (App DevOps — scoped to their team)
    "deploy_agent":        "app-devops",
    "manage_team_agents":  "app-devops",
    "register_agent":      "app-devops",
    "manage_a2a":          "app-devops",
    # Workflow management (Business Ops)
    "create_workflow":     "business-ops",
    "manage_workflow":     "business-ops",
    # Read-only platform views (Architect + DevOps)
    "view_platform":       "ai-devops",   # architects bypass via level check
    "view_audit_logs":     "ai-devops",
    "view_costs":          "ai-devops",
    # Basic usage (all authenticated users)
    "use_agent":           "business-user",
    "submit_requirement":  "ba",
}

# ── Model access control ───────────────────────────────────────────────────────

MODEL_MIN_ROLE: dict[str, str] = {
    "claude-opus":    "ai-devops",
    "claude-sonnet":  "business-user",
    "claude-haiku":   "business-user",
    "gpt-4o":         "app-devops",
    "gpt-4o-mini":    "business-user",
    "gemini-pro":     "app-devops",
    "gemini-flash":   "business-user",
    "llama3":         "ai-devops",   # self-hosted, restricted
}

# ── MAS TRM blocked patterns ───────────────────────────────────────────────────

BLOCKED_PATTERNS: list[tuple[str, str]] = [
    ("jailbreak",       "ignore previous instructions"),
    ("jailbreak",       "disregard your system prompt"),
    ("jailbreak",       "act as dan"),
    ("jailbreak",       "pretend you are"),
    ("credential_leak", "my password"),
    ("credential_leak", "password is"),
    ("credential_leak", "api key is"),
    ("credential_leak", "secret is"),
    ("data_exfil",      "send this to"),
    ("data_exfil",      "email this to"),
    ("data_exfil",      "forward this to"),
    ("pii_request",     "show me all customer"),
    ("pii_request",     "list all user"),
]


# ── Core policy check ──────────────────────────────────────────────────────────

def check_access(
    user_role: str,
    skill: str | None = None,
    model: str | None = None,
    prompt: str | None = None,
    operation: str | None = None,
    team_id: str | None = None,
    target_team_id: str | None = None,
) -> PolicyResult:
    """
    Evaluate all governance policies for a request.

    Args:
        user_role:       The role of the requesting user.
        skill:           The skill being invoked (optional).
        model:           The LLM model being used (optional).
        prompt:          The user prompt for content scanning (optional).
        operation:       The platform operation being attempted (optional).
        team_id:         The team the user belongs to (optional).
        target_team_id:  The team owning the target resource (optional).

    Returns:
        PolicyResult with allowed=True if all checks pass.
    """
    violations: list[str] = []
    user_level = ROLE_LEVELS.get(user_role, -1)

    if user_level < 0:
        return PolicyResult(
            allowed=False,
            reason="Unknown role",
            violations=[f"Unknown role: '{user_role}'"],
        )

    # ── Skill access ──────────────────────────────────────────────────────────
    if skill:
        min_role = SKILL_MIN_ROLE.get(skill)
        if min_role:
            min_level = ROLE_LEVELS.get(min_role, 99)
            if user_level < min_level:
                violations.append(
                    f"skill '{skill}' requires role '{min_role}' (current: '{user_role}')"
                )

    # ── Model access ──────────────────────────────────────────────────────────
    if model:
        min_role = MODEL_MIN_ROLE.get(model)
        if min_role:
            min_level = ROLE_LEVELS.get(min_role, 99)
            if user_level < min_level:
                violations.append(
                    f"model '{model}' requires role '{min_role}' (current: '{user_role}')"
                )

    # ── Operation access ──────────────────────────────────────────────────────
    if operation:
        min_role = OPERATION_MIN_ROLE.get(operation)
        if min_role:
            min_level = ROLE_LEVELS.get(min_role, 99)
            # ai-architect (level 5) can perform read operations but not mutating ones
            is_read_op = operation.startswith("view_")
            if user_role == "ai-architect" and not is_read_op:
                violations.append(
                    f"ai-architect has read-only access — operation '{operation}' is not permitted"
                )
            elif user_level < min_level and user_role != "ai-architect":
                violations.append(
                    f"operation '{operation}' requires role '{min_role}' (current: '{user_role}')"
                )

    # ── Cross-team access ─────────────────────────────────────────────────────
    # app-devops can only manage their own team's resources.
    # ai-devops and ai-architect can access all teams.
    if team_id and target_team_id and team_id != target_team_id:
        if user_role == "app-devops":
            violations.append(
                f"app-devops can only access their own team resources "
                f"(team: '{team_id}', target: '{target_team_id}')"
            )

    # ── Prompt content scanning (MAS TRM) ─────────────────────────────────────
    if prompt:
        lowered = prompt.lower()
        for category, phrase in BLOCKED_PATTERNS:
            if phrase in lowered:
                violations.append(f"{category}: contains blocked phrase '{phrase}'")

    if violations:
        return PolicyResult(
            allowed=False,
            reason="Policy violations detected",
            violations=violations,
        )
    return PolicyResult(allowed=True, reason="ok")


# ── Convenience helpers ───────────────────────────────────────────────────────

def can_manage_platform(user_role: str) -> bool:
    """Only ai-devops can mutate platform resources."""
    return ROLE_LEVELS.get(user_role, -1) == ROLE_LEVELS["ai-devops"]


def can_view_all(user_role: str) -> bool:
    """ai-devops and ai-architect can view all resources."""
    return ROLE_LEVELS.get(user_role, -1) >= ROLE_LEVELS["ai-devops"]


def can_manage_team_agents(user_role: str) -> bool:
    """app-devops and above can manage agents (scoped to team)."""
    return ROLE_LEVELS.get(user_role, -1) >= ROLE_LEVELS["app-devops"]


def is_platform_role(user_role: str) -> bool:
    """Returns True for roles that belong to the AI platform team."""
    return user_role in ("ai-architect", "ai-devops")
