"""
Usage tracker — aggregates token and cost metrics from audit events.
Provides per-user, per-model, per-skill breakdowns for MAS TRM reporting.
"""

from collections import defaultdict
from datetime import datetime, timezone

# Approximate cost per 1K tokens (USD) — update as pricing changes
COST_PER_1K: dict[str, dict[str, float]] = {
    "claude-sonnet": {"input": 0.003,  "output": 0.015},
    "claude-opus":   {"input": 0.015,  "output": 0.075},
    "gpt-4o":        {"input": 0.005,  "output": 0.015},
    "gpt-4o-mini":   {"input": 0.00015,"output": 0.0006},
}

# In-memory aggregations — reset on service restart
_by_user:  dict[str, dict] = defaultdict(lambda: {"calls": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0})
_by_model: dict[str, dict] = defaultdict(lambda: {"calls": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0})
_by_skill: dict[str, dict] = defaultdict(lambda: {"calls": 0})


def record_llm_call(
    user_id: str,
    model: str,
    skill: str | None,
    input_tokens: int,
    output_tokens: int,
) -> None:
    cost_table = COST_PER_1K.get(model, {"input": 0.0, "output": 0.0})
    cost = (input_tokens / 1000 * cost_table["input"]) + (output_tokens / 1000 * cost_table["output"])

    for store, key in [(_by_user, user_id), (_by_model, model)]:
        store[key]["calls"] += 1
        store[key]["input_tokens"] += input_tokens
        store[key]["output_tokens"] += output_tokens
        store[key]["cost_usd"] += cost

    if skill:
        _by_skill[skill]["calls"] += 1


def get_report() -> dict:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "by_user":  dict(_by_user),
        "by_model": dict(_by_model),
        "by_skill": dict(_by_skill),
        "total_cost_usd": sum(v["cost_usd"] for v in _by_model.values()),
    }


def reset() -> None:
    _by_user.clear()
    _by_model.clear()
    _by_skill.clear()
