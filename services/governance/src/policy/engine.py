"""
Policy engine for the governance service.
Centralised RBAC and MAS TRM compliance rules.
"""

from dataclasses import dataclass, field


@dataclass
class PolicyResult:
    allowed: bool
    reason: str
    violations: list[str] = field(default_factory=list)


# ── Role hierarchy ────────────────────────────────────────────────────────────

ROLE_LEVELS: dict[str, int] = {
    "viewer":           0,
    "developer":        1,
    "senior-engineer":  2,
    "architect":        3,
    "admin":            4,
}

# ── Skill access control ──────────────────────────────────────────────────────

SKILL_MIN_ROLE: dict[str, str] = {
    "incident-response":  "senior-engineer",
    "terraform-iac":      "senior-engineer",
    "banking-compliance": "architect",
    "code-review":        "developer",
    "rag-search":         "developer",
}

# ── Model access control ──────────────────────────────────────────────────────

MODEL_MIN_ROLE: dict[str, str] = {
    "claude-opus": "architect",
    "gpt-4o":      "developer",
    "claude-sonnet": "developer",
    "gpt-4o-mini": "developer",
}

# ── MAS TRM blocked patterns ─────────────────────────────────────────────────

BLOCKED_PATTERNS: list[tuple[str, str]] = [
    ("jailbreak",       "ignore previous instructions"),
    ("jailbreak",       "disregard your system prompt"),
    ("credential_leak", "my password"),
    ("credential_leak", "password is"),
    ("data_exfil",      "send this to"),
    ("data_exfil",      "email this to"),
]


def check_access(
    user_role: str,
    skill: str | None = None,
    model: str | None = None,
    prompt: str | None = None,
) -> PolicyResult:
    """
    Evaluate all governance policies for a request.
    Returns PolicyResult(allowed=True) if all checks pass.
    """
    violations: list[str] = []
    user_level = ROLE_LEVELS.get(user_role, 0)

    # Skill access
    if skill:
        min_role = SKILL_MIN_ROLE.get(skill)
        if min_role and user_level < ROLE_LEVELS.get(min_role, 99):
            violations.append(
                f"skill '{skill}' requires role '{min_role}' (current: '{user_role}')"
            )

    # Model access
    if model:
        min_role = MODEL_MIN_ROLE.get(model)
        if min_role and user_level < ROLE_LEVELS.get(min_role, 99):
            violations.append(
                f"model '{model}' requires role '{min_role}' (current: '{user_role}')"
            )

    # Prompt patterns
    if prompt:
        lowered = prompt.lower()
        for category, phrase in BLOCKED_PATTERNS:
            if phrase in lowered:
                violations.append(f"{category}: contains '{phrase}'")

    if violations:
        return PolicyResult(allowed=False, reason="Policy violations detected", violations=violations)
    return PolicyResult(allowed=True, reason="ok")
