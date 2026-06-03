"""
Skill registry — maps skill names to metadata and system prompt extensions.

Skills are defined by SKILL.md files in the skills/ directory at the repo root.
The registry loads them at startup and makes them available to the agent graph.

Skill names must match the directory names under skills/:
  api-standards, banking-compliance, cloud-architecture, data-privacy,
  incident-response, secure-coding, terraform-iac, threat-modeling
"""

import os
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Path to the skills/ directory (repo root / skills)
# When running in Cloud Run the working directory is /app; skills are copied there.
_SKILLS_ROOT = Path(os.getenv("SKILLS_ROOT", "/app/skills"))

# Fallback for local dev — walk up from this file to the repo root
if not _SKILLS_ROOT.exists():
    _here = Path(__file__).resolve()
    for parent in _here.parents:
        candidate = parent / "skills"
        if candidate.exists():
            _SKILLS_ROOT = candidate
            break


@dataclass
class SkillMeta:
    name: str                        # canonical skill ID (directory name)
    display_name: str                # human-friendly label
    description: str                 # one-liner for UI / governance
    system_prompt: str               # injected into the agent system message
    tool_names: list[str] = field(default_factory=list)  # tools activated for this skill
    allowed_roles: list[str] = field(default_factory=lambda: ["developer", "admin"])


def _load_skill_md(skill_dir: Path) -> str:
    """Read SKILL.md content; return empty string if missing."""
    skill_md = skill_dir / "SKILL.md"
    if skill_md.exists():
        return skill_md.read_text(encoding="utf-8")
    logger.warning("SKILL.md not found at %s", skill_md)
    return ""


def _build_system_prompt(display_name: str, skill_md: str) -> str:
    """Compose the skill system prompt from the SKILL.md content."""
    return f"""## Active Skill: {display_name}

You are operating in a specialised mode. Follow the skill instructions below exactly.
All outputs must comply with MAS TRM guidelines and bank internal standards.

{skill_md}

---
Always structure your response clearly with headings and severity ratings where applicable.
Cite specific evidence (file names, line numbers, control IDs) in your findings.
"""


# ── Skill definitions ─────────────────────────────────────────────────────────

def _build_registry() -> dict[str, SkillMeta]:
    skills_root = _SKILLS_ROOT
    registry: dict[str, SkillMeta] = {}

    definitions = [
        dict(
            name="secure-coding",
            display_name="Secure Coding Review",
            description="Review code for OWASP Top 10, MAS TRM, and bank secure coding standards",
            tool_names=["secure_code_review", "retrieve"],
            allowed_roles=["developer", "senior-engineer", "architect", "admin"],
        ),
        dict(
            name="banking-compliance",
            display_name="Banking Compliance Review",
            description="MAS TRM, MAS Notice 655/644, PDPA, and internal bank policy compliance",
            tool_names=["compliance_check", "retrieve"],
            allowed_roles=["developer", "senior-engineer", "architect", "admin"],
        ),
        dict(
            name="terraform-iac",
            display_name="Terraform / IaC Review",
            description="Review Terraform for security misconfigurations and GCP best practices",
            tool_names=["terraform_review", "retrieve"],
            allowed_roles=["developer", "senior-engineer", "architect", "admin"],
        ),
        dict(
            name="threat-modeling",
            display_name="Threat Modeling",
            description="STRIDE-based threat modeling with Mermaid DFD and MAS TRM mapping",
            tool_names=["threat_model", "retrieve"],
            allowed_roles=["senior-engineer", "architect", "admin"],
        ),
        dict(
            name="api-standards",
            display_name="API Standards Review",
            description="REST, OpenAPI 3.1, OAuth2/OIDC, RBAC, and bank API gateway standards",
            tool_names=["api_review", "retrieve"],
            allowed_roles=["developer", "senior-engineer", "architect", "admin"],
        ),
        dict(
            name="data-privacy",
            display_name="Data Privacy Review",
            description="PDPA Singapore, data classification, PII handling, and retention policies",
            tool_names=["privacy_review", "retrieve"],
            allowed_roles=["developer", "senior-engineer", "architect", "admin"],
        ),
        dict(
            name="cloud-architecture",
            display_name="Cloud Architecture Review",
            description="GCP architecture for reliability, security, cost, and MAS cloud outsourcing",
            tool_names=["architecture_review", "retrieve"],
            allowed_roles=["architect", "admin"],
        ),
        dict(
            name="incident-response",
            display_name="Incident Response Assistant",
            description="Structured IR for P1–P4 incidents, MAS Notice 655 reporting obligations",
            tool_names=["incident_response", "retrieve"],
            allowed_roles=["developer", "senior-engineer", "architect", "admin"],
        ),
    ]

    for d in definitions:
        skill_dir = skills_root / d["name"]
        skill_md = _load_skill_md(skill_dir)
        registry[d["name"]] = SkillMeta(
            name=d["name"],
            display_name=d["display_name"],
            description=d["description"],
            system_prompt=_build_system_prompt(d["display_name"], skill_md),
            tool_names=d["tool_names"],
            allowed_roles=d["allowed_roles"],
        )
        logger.info("Loaded skill: %s", d["name"])

    return registry


# Singleton — built once at import time
SKILL_REGISTRY: dict[str, SkillMeta] = _build_registry()


def get_skill(skill_name: Optional[str]) -> Optional[SkillMeta]:
    """Return SkillMeta for the given skill name, or None if not found / not provided."""
    if not skill_name:
        return None
    meta = SKILL_REGISTRY.get(skill_name)
    if meta is None:
        logger.warning("Unknown skill requested: %s", skill_name)
    return meta


def list_skills() -> list[dict]:
    """Return a list of skill summaries for the UI / API."""
    return [
        {
            "name": s.name,
            "display_name": s.display_name,
            "description": s.description,
            "allowed_roles": s.allowed_roles,
        }
        for s in SKILL_REGISTRY.values()
    ]
