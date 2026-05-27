"""
Skill tools — lightweight tools that wrap enterprise skill logic.
Each tool is a thin adapter; real logic lives in the skills/ directory.
"""

from langchain_core.tools import tool


@tool
def get_current_user_role(user_role: str) -> str:
    """Return the current user's role. Useful before attempting privileged operations."""
    return user_role


@tool
def format_banking_response(text: str) -> str:
    """
    Format a response to meet MAS TRM communication standards.
    Ensures responses are clear, factual, and do not contain regulatory disclaimers.
    """
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    return "\n".join(lines)
