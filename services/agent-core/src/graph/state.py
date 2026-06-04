"""AgentState — shared state passed through every LangGraph node."""

from typing import Annotated
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field
import operator


class AgentState(BaseModel):
    """Typed state for the agentic AI graph."""

    # Chat history — add_messages reducer appends new messages
    messages: Annotated[list, add_messages] = Field(default_factory=list)

    # Request context
    user_id: str = ""
    user_role: str = "business-user"      # see governance policy engine for valid roles
    skill: str | None = None              # active skill name, e.g. "banking-compliance"
    session_id: str = ""
    team_id: str = "platform"            # team the user belongs to — used for isolation

    # RAG results injected by the retrieve node
    retrieved_chunks: list[dict] = Field(default_factory=list)

    # Audit trail — accumulated during the run
    audit_events: Annotated[list[dict], operator.add] = Field(default_factory=list)

    # Long-term memory context injected into the system prompt
    longterm_context: str = ""

    # Terminal flag set by the agent when it has a final answer
    finished: bool = False
