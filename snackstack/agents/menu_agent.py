"""
agents/menu_agent.py — Menu Discovery Agent.

Runs its own tool-calling loop so that parallel Send() branches
never contaminate each other's message history.
"""

from typing import Literal
from langchain_core.messages import (
    SystemMessage,
    HumanMessage,
    AIMessage,
    ToolMessage,
)
from langgraph.types import Command

from snackstack.config import llm
from snackstack.state import StackState
from snackstack.agents.prompts import MENU_AGENT_PROMPT
from snackstack.tools.menu_tools import menu_tools_list
from snackstack.logger import setup_logger

logger = setup_logger("snackstack.menu_agent")

MAX_TOOL_ITERATIONS = 5

# LLM with menu tools bound
menu_llm = llm.bind_tools(menu_tools_list)
tool_map = {t.name: t for t in menu_tools_list}


def menu_agent_node(state: StackState) -> Command[Literal["synthesizer_node"]]:
    """
    Menu Agent — invokes the LLM in a loop, executing any requested
    tools until the model produces a final text answer.
    """
    logger.info("Processing menu query...")

    # Build conversation history from prior turns for context
    history_msgs = []
    for msg in state.get("messages", [])[-6:]:
        role = getattr(msg, "type", "unknown")
        if role == "human":
            history_msgs.append(HumanMessage(content=msg.content))
        elif role == "ai" and msg.content:
            history_msgs.append(AIMessage(content=msg.content))

    # Fresh local message list — isolated from the shared graph state
    local_msgs = [
        SystemMessage(content=MENU_AGENT_PROMPT),
        *history_msgs,
        HumanMessage(content=state["user_query"]),
    ]

    for iteration in range(MAX_TOOL_ITERATIONS):
        response = menu_llm.invoke(local_msgs)

        # ── No tool calls → agent is done ──
        if not getattr(response, "tool_calls", None):
            logger.info("Done (iteration %d)", iteration)
            return Command(
                goto="synthesizer_node",
                update={
                    "messages": [response],
                    "menu_response": response.content,
                },
            )

        # ── Execute requested tools ──
        tool_names = [tc["name"] for tc in response.tool_calls]
        logger.info("Tools: %s (iter %d)", tool_names, iteration)
        local_msgs.append(response)

        for tc in response.tool_calls:
            result = tool_map[tc["name"]].invoke(tc["args"])
            local_msgs.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))

    # Safety: max iterations reached
    fallback = response.content or "I found menu results but could not finalise a response."
    logger.warning("Hit max iterations (%d)", MAX_TOOL_ITERATIONS)
    return Command(
        goto="synthesizer_node",
        update={"messages": [AIMessage(content=fallback)], "menu_response": fallback},
    )