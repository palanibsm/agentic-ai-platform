"""
Policy engine for LLM Gateway.
Enforces prompt/response guardrails on every request.
"""

from dataclasses import dataclass, field


@dataclass
class PolicyResult:
    allowed: bool
    reason: str
    violations: list[str] = field(default_factory=list)


BLOCKED_PROMPT_PATTERNS: list[tuple[str, str]] = [
    ("hardcoded_secret", "api_key"),
    ("hardcoded_secret", "secret_key"),
    ("hardcoded_secret", "private_key"),
    ("credential_leak",  "password is"),
    ("credential_leak",  "my password"),
    ("jailbreak",        "ignore previous instructions"),
    ("jailbreak",        "disregard your system prompt"),
    ("jailbreak",        "you are now"),
    ("data_exfil",       "send this to"),
    ("data_exfil",       "email this to"),
]

HIGH_RISK_SKILLS: set[str] = {
    "incident-response",
    "terraform-iac",
    "banking-compliance",
}

RESTRICTED_MODELS: set[str] = {
    "claude-opus",
}


def check_prompt(
    prompt: str,
    skill: str | None = None,
    model: str | None = None,
    user_role: str = "developer",
) -> PolicyResult:
    violations: list[str] = []
    lowered = prompt.lower()

    for category, phrase in BLOCKED_PROMPT_PATTERNS:
        if phrase in lowered:
            violations.append(f"{category}: contains '{phrase}'")

    if skill in HIGH_RISK_SKILLS and user_role not in ("admin", "senior-engineer", "architect"):
        violations.append(f"skill '{skill}' requires elevated role (current: {user_role})")

    if model in RESTRICTED_MODELS and user_role not in ("admin", "architect"):
        violations.append(f"model '{model}' is restricted (current role: {user_role})")

    if violations:
        return PolicyResult(allowed=False, reason="Policy violations detected", violations=violations)
    return PolicyResult(allowed=True, reason="ok")


def check_response(response_text: str) -> PolicyResult:
    violations: list[str] = []
    lowered = response_text.lower()

    BLOCKED_RESPONSE_PATTERNS = [
        ("credential_in_response", "here is your password"),
        ("credential_in_response", "your api key is"),
        ("harmful_content",        "here is how to hack"),
    ]

    for category, phrase in BLOCKED_RESPONSE_PATTERNS:
        if phrase in lowered:
            violations.append(f"{category}: response contains '{phrase}'")

    if violations:
        return PolicyResult(allowed=False, reason="Response policy violation", violations=violations)
    return PolicyResult(allowed=True, reason="ok")
