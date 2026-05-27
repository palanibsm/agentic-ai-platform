"""
LangGraph agent graph.
Architecture: ReAct loop — llm_node → tool_node → llm_node → … → END
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
from src.audit.publisher import emit_audit_event

logger = logging.getLogger(__name__)

# ── Tool registry ────────────────────────────────────────────────────────────

TOOLS = [retrieve, get_current_user_role, format_banking_response]

# ── LLM factory ─────────────────────────────────────────────────────────────

LLM_GATEWAY_URL = os.getenv("LLM_GATEWAY_URL", "http://localhost:4000")
DEFAULT_MODEL = os.getenv("AGENT_DEFAULT_MODEL", "claude-sonnet")


def _build_llm(model: str = DEFAULT_MODEL):
    """
    Route to LiteLLM gateway when LITELLM_MASTER_KEY is set.
    Falls back to direct Anthropic/OpenAI API keys for local dev.
    """
    use_gateway = bool(os.getenv("LITELLM_MASTER_KEY"))

    if "claude" in model:
        if use_gateway:
            # Use gateway alias defined in config.yaml; route via OpenAI-compat endpoint
            return ChatOpenAI(
                model=model,                          # e.g. "claude-sonnet"
                base_url=f"{LLM_GATEWAY_URL}/v1",
                api_key=os.getenv("LITELLM_MASTER_KEY"),
                max_tokens=4096,
            ).bind_tools(TOOLS)
        return ChatAnthropic(
            model="claude-sonnet-4-6",
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            max_tokens=4096,
        ).bind_tools(TOOLS)

    kwargs = dict(model="gpt-4o", max_tokens=4096)
    if use_gateway:
        kwargs["base_url"] = f"{LLM_GATEWAY_URL}/v1"
        kwargs["api_key"] = os.getenv("LITELLM_MASTER_KEY")
    else:
        kwargs["api_key"] = os.getenv("OPENAI_API_KEY")
    return ChatOpenAI(**kwargs).bind_tools(TOOLS)


# ── System prompt ────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an enterprise AI assistant for a Singapore bank.

Guidelines:
- Always retrieve relevant documents before answering factual questions.
- Never reveal customer PII, credentials, or internal system details.
- Cite document sources when using retrieved content.
- If a request requires elevated permissions, state so clearly.
- Follow MAS TRM guidelines: be accurate, auditable, and conservative.
"""


# ── Graph nodes ──────────────────────────────────────────────────────────────

def llm_node(state: AgentState) -> dict:
    """Call the LLM with current messages; may produce tool calls."""
    llm = _build_llm()

    messages = [SystemMessage(content=SYSTEM_PROMPT)] + list(state.messages)
    response = llm.invoke(messages)

    audit_event = {
        "node": "llm",
        "model": DEFAULT_MODEL,
        "tool_calls": [tc["name"] for tc in (response.tool_calls or [])],
    }
    emit_audit_event("agent.llm.call", state.user_id, state.session_id, audit_event)

    # If no tool calls → agent is done
    finished = not response.tool_calls
    return {"messages": [response], "finished": finished}


def should_continue(state: AgentState) -> str:
    """Route: go to tools if the LLM made tool calls, else end."""
    if state.finished:
        return END
    last = state.messages[-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tools"
    return END


# ── Graph assembly ────────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    tool_node = ToolNode(TOOLS)

    builder = StateGraph(AgentState)
    builder.add_node("llm", llm_node)
    builder.add_node("tools", tool_node)

    builder.set_entry_point("llm")
    builder.add_conditional_edges("llm", should_continue, {"tools": "tools", END: END})
    builder.add_edge("tools", "llm")

    return builder.compile()


# Singleton graph — compiled once at import time
graph = build_graph()

# ── In-memory session store (keyed by session_id) ────────────────────────────
# Stores the full message history per session for multi-turn continuity.
# In production, replace with Redis or Firestore for persistence across restarts.
_SESSION_STORE: dict[str, list] = {}
MAX_HISTORY = 20  # keep last N messages to avoid context overflow


# ── Public API ────────────────────────────────────────────────────────────────

async def run_agent(
    query: str,
    user_id: str,
    user_role: str = "developer",
    skill: str | None = None,
    session_id: str = "",
) -> dict:
    """
    Run the agent graph for a single user query.

    Returns:
        {"answer": str, "session_id": str, "tool_calls_made": list[str]}
    """
    emit_audit_event(
        "agent.run.start", user_id, session_id,
        {"query": query, "skill": skill, "user_role": user_role},
    )

    # Load prior conversation history for this session
    history = _SESSION_STORE.get(session_id, [])

    initial_state = AgentState(
        messages=history + [HumanMessage(content=query)],
        user_id=user_id,
        user_role=user_role,
        skill=skill,
        session_id=session_id,
    )

    final_state = await graph.ainvoke(initial_state)

    # Persist updated history (trim to MAX_HISTORY to avoid bloat)
    _SESSION_STORE[session_id] = list(final_state["messages"])[-MAX_HISTORY:]

    # Extract final answer and all tool calls from message history
    answer = ""
    tool_calls_made = []
    for msg in final_state["messages"]:
        # Collect every tool call made across all LLM turns
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            tool_calls_made.extend(tc["name"] for tc in msg.tool_calls)
        # The final answer is the last AI message with text content and no tool calls
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
        {"tool_calls_made": tool_calls_made, "answer_length": len(answer)},
    )

    return {"answer": answer, "session_id": session_id, "tool_calls_made": tool_calls_made}
