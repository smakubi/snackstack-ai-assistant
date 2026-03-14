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


def orchestrator_node(
    state: StackState,
) -> Command[Literal["menu_agent_node", "order_agent_node"]]:
    """Classify the query and fan out to one or both agents."""

    query = state["user_query"]
    logger.info("Routing query: %s", query[:60])

    # Conversation history is persisted via MemorySaver — just use it
    history = state.get("messages", [])[-6:]

    decision: OrchestratorDecision = routing_llm.invoke([
        SystemMessage(content=ORCHESTRATOR_PROMPT),
        *history,
        HumanMessage(content=query),
    ])
    logger.info("Agents: %s | Reason: %s", decision.agents, decision.reasoning)

    # Reset per-turn buffers BEFORE sending to agents
    clean_state = {
        **state,
        "menu_messages": [],
        "order_messages": [],
        "menu_response": "",
        "order_response": "",
    }

    sends = [Send(f"{agent}_node", clean_state) for agent in decision.agents]
    return Command(goto=sends, update={"route": decision.agents})