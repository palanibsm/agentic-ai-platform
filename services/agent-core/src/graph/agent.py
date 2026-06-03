"""
LangGraph agent graph.
Architecture: ReAct loop — llm_node → tool_node → llm_node → … → END

Skill routing:
  When a skill name is provided, the agent:
  1. Injects a skill-specific system prompt (loaded from SKILL.md)
  2. Activates only the tools relevant to that skill
  3. Emits audit events with the skill name attached
"""

import os
import logging
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from src.graph.state import AgentState
from src.tools.rag_tool import retrieve
from src.tools.skill_tool import get_current_user_role, format_banking_response
from src.tools.skill_tools import SKILL_TOOLS, SKILL_TOOL_MAP
from src.skills.registry import get_skill, SkillMeta
from src.audit.publisher import emit_audit_event

logger = logging.getLogger(__name__)

# ── Base tools (always available) ────────────────────────────────────────────

BASE_TOOLS = [retrieve, get_current_user_role, format_banking_response]

# ── LLM factory ──────────────────────────────────────────────────────────────

LLM_GATEWAY_URL = os.getenv("LLM_GATEWAY_URL", "http://localhost:4000")
DEFAULT_MODEL = os.getenv("AGENT_DEFAULT_MODEL", "claude-sonnet")


def _build_llm(model: str = DEFAULT_MODEL, tools: list = None):
    """
    Route to LiteLLM gateway when LITELLM_MASTER_KEY is set.
    Falls back to direct Anthropic/OpenAI API keys for local dev.
    Binds the provided tool list so the LLM knows what tools are available.
    """
    if tools is None:
        tools = BASE_TOOLS

    use_gateway = bool(os.getenv("LITELLM_MASTER_KEY"))

    if "claude" in model:
        if use_gateway:
            return ChatOpenAI(
                model=model,
                base_url=f"{LLM_GATEWAY_URL}/v1",
                api_key=os.getenv("LITELLM_MASTER_KEY"),
                max_tokens=4096,
            ).bind_tools(tools)
        return ChatAnthropic(
            model="claude-sonnet-4-6",
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            max_tokens=4096,
        ).bind_tools(tools)

    kwargs = dict(model="gpt-4o", max_tokens=4096)
    if use_gateway:
        kwargs["base_url"] = f"{LLM_GATEWAY_URL}/v1"
        kwargs["api_key"] = os.getenv("LITELLM_MASTER_KEY")
    else:
        kwargs["api_key"] = os.getenv("OPENAI_API_KEY")
    return ChatOpenAI(**kwargs).bind_tools(tools)


# ── System prompts ────────────────────────────────────────────────────────────

BASE_SYSTEM_PROMPT = """You are an enterprise AI assistant for a Singapore bank.

Guidelines:
- Always retrieve relevant documents before answering factual questions.
- Never reveal customer PII, credentials, or internal system details.
- Cite document sources when using retrieved content.
- If a request requires elevated permissions, state so clearly.
- Follow MAS TRM guidelines: be accurate, auditable, and conservative.
"""


def _build_system_prompt(skill: SkillMeta | None) -> str:
    """Combine the base prompt with the skill-specific prompt if a skill is active."""
    if skill is None:
        return BASE_SYSTEM_PROMPT
    return BASE_SYSTEM_PROMPT + "\n\n" + skill.system_prompt


def _get_active_tools(skill: SkillMeta | None) -> list:
    """
    Return the tool list for the current skill.
    Base tools are always included. Skill tools are added on top.
    """
    if skill is None:
        return BASE_TOOLS

    skill_tools = [
        SKILL_TOOL_MAP[name]
        for name in skill.tool_names
        if name in SKILL_TOOL_MAP
    ]
    # retrieve is always included (in BASE_TOOLS and in skill tool_names)
    # deduplicate by tool name
    all_tools = {t.name: t for t in BASE_TOOLS + skill_tools}
    return list(all_tools.values())


# ── Graph nodes ───────────────────────────────────────────────────────────────

def llm_node(state: AgentState) -> dict:
    """Call the LLM with the current skill context and message history."""
    skill = get_skill(state.skill)
    active_tools = _get_active_tools(skill)
    llm = _build_llm(tools=active_tools)

    system_prompt = _build_system_prompt(skill)
    messages = [SystemMessage(content=system_prompt)] + list(state.messages)
    response = llm.invoke(messages)

    audit_event = {
        "node": "llm",
        "model": DEFAULT_MODEL,
        "skill": state.skill,
        "tool_calls": [tc["name"] for tc in (response.tool_calls or [])],
    }
    emit_audit_event("agent.llm.call", state.user_id, state.session_id, audit_event)

    finished = not response.tool_calls
    return {"messages": [response], "finished": finished}


def tool_node_factory(state: AgentState):
    """
    Dynamically build a ToolNode with only the active skill's tools.
    This prevents the LLM from calling tools outside the active skill scope.
    """
    skill = get_skill(state.skill)
    active_tools = _get_active_tools(skill)
    return ToolNode(active_tools)


def should_continue(state: AgentState) -> str:
    if state.finished:
        return END
    last = state.messages[-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tools"
    return END


# ── Graph assembly ─────────────────────────────────────────────────────────────
# We compile with ALL tools registered so LangGraph's ToolNode can resolve
# any tool call. Skill scoping is enforced by _build_llm binding only the
# active skill's tools — the LLM can only call tools it knows about.

ALL_TOOLS = {t.name: t for t in BASE_TOOLS + SKILL_TOOLS}
_global_tool_node = ToolNode(list(ALL_TOOLS.values()))


def build_graph() -> StateGraph:
    builder = StateGraph(AgentState)
    builder.add_node("llm", llm_node)
    builder.add_node("tools", _global_tool_node)

    builder.set_entry_point("llm")
    builder.add_conditional_edges("llm", should_continue, {"tools": "tools", END: END})
    builder.add_edge("tools", "llm")

    return builder.compile()


# Singleton graph — compiled once at import time
graph = build_graph()

# ── In-memory session store ───────────────────────────────────────────────────
_SESSION_STORE: dict[str, list] = {}
MAX_HISTORY = 20


# ── Public API ────────────────────────────────────────────────────────────────

async def run_agent(
    query: str,
    user_id: str,
    user_role: str = "business-user",
    skill: str | None = None,
    session_id: str = "",
    team_id: str = "platform",
) -> dict:
    """
    Run the agent graph for a single user query.

    Returns:
        {"answer": str, "session_id": str, "tool_calls_made": list[str], "skill": str|None}
    """
    # Validate skill exists if provided
    skill_meta = get_skill(skill)
    if skill and skill_meta is None:
        logger.warning("Skill '%s' not found — falling back to base mode", skill)
        skill = None

    # Check role is allowed for this skill
    if skill_meta and user_role not in skill_meta.allowed_roles:
        return {
            "answer": (
                f"Access denied: your role '{user_role}' is not permitted to use "
                f"the '{skill_meta.display_name}' skill. "
                f"Allowed roles: {', '.join(skill_meta.allowed_roles)}."
            ),
            "session_id": session_id,
            "tool_calls_made": [],
            "skill": skill,
        }

    emit_audit_event(
        "agent.run.start", user_id, session_id,
        {"query": query, "skill": skill, "user_role": user_role, "team_id": team_id},
    )

    history = _SESSION_STORE.get(session_id, [])

    initial_state = AgentState(
        messages=history + [HumanMessage(content=query)],
        user_id=user_id,
        user_role=user_role,
        skill=skill,
        session_id=session_id,
        team_id=team_id,
    )

    final_state = await graph.ainvoke(initial_state)

    _SESSION_STORE[session_id] = list(final_state["messages"])[-MAX_HISTORY:]

    answer = ""
    tool_calls_made = []
    for msg in final_state["messages"]:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            tool_calls_made.extend(tc["name"] for tc in msg.tool_calls)
        if (
            hasattr(msg, "content")
            and isinstance(msg.content, str)
            and msg.content
            and not (hasattr(msg, "tool_calls") and msg.tool_calls)
            and msg.__class__.__name__ != "HumanMessage"
        ):
            answer = msg.content

    emit_audit_event(
        "agent.run.complete", user_id, session_id,
        {"skill": skill, "team_id": team_id, "tool_calls_made": tool_calls_made, "answer_length": len(answer)},
    )

    return {
        "answer": answer,
        "session_id": session_id,
        "tool_calls_made": tool_calls_made,
        "skill": skill,
        "team_id": team_id,
    }
