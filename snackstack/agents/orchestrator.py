"""
agents/orchestrator.py — Classifies the user query and dispatches
to the correct specialist agent(s) using LangGraph's Send() API.
"""

from typing import Literal
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.types import Command, Send

from snackstack.config import llm
from snackstack.state import StackState
from snackstack.agents.prompts import ORCHESTRATOR_PROMPT
from snackstack.logger import setup_logger

logger = setup_logger("snackstack.orchestrator")


class OrchestratorDecision(BaseModel):
    """The orchestrator's routing decision."""

    reasoning: str = Field(description="Brief explanation of why these agents were chosen")
    agents: list[Literal["menu_agent", "order_agent"]] = Field(
        description="List of agents to dispatch. Always at least one.",
        min_length=1,
    )


routing_llm = llm.with_structured_output(OrchestratorDecision)


def format_history(state: StackState, max_turns: int = 6) -> str:
    """Build a short conversation summary from recent messages."""
    history_lines = []
    for msg in state.get("messages", [])[-max_turns:]:
        role = getattr(msg, "type", "unknown")
        if role == "human":
            history_lines.append(f"Customer: {msg.content}")
        elif role == "ai" and msg.content:
            history_lines.append(f"Assistant: {msg.content[:200]}")
    return "\n".join(history_lines)


def orchestrator_node(
    state: StackState,
) -> Command[Literal["menu_agent_node", "order_agent_node"]]:
    """Classify the query and fan out to one or both agents."""

    query = state["user_query"]
    logger.info("Routing query: %s", query[:60])

    history = format_history(state)
    context = f"Conversation so far:\n{history}\n\nLatest query: {query}" if history else query

    decision: OrchestratorDecision = routing_llm.invoke([
        SystemMessage(content=ORCHESTRATOR_PROMPT),
        HumanMessage(content=context),
    ])
    logger.info("Agents: %s | Reason: %s", decision.agents, decision.reasoning)

    sends = [Send(f"{agent}_node", state) for agent in decision.agents]
    return Command(goto=sends, update={"route": decision.agents})