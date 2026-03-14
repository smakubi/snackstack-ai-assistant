"""
agents/order_agent.py — Order Support Agent with Human-in-the-Loop.

If the user query doesn't contain an order ID, tracking ID, or email,
the agent interrupts and asks the user to provide one before proceeding.
"""

import re
from typing import Literal
from langchain_core.messages import (
    SystemMessage,
    HumanMessage,
    AIMessage,
    ToolMessage,
)
from langgraph.types import Command, interrupt

from snackstack.config import llm
from snackstack.state import StackState
from snackstack.agents.prompts import ORDER_AGENT_PROMPT
from snackstack.tools.order_tools import order_tools_list
from snackstack.logger import setup_logger

logger = setup_logger("snackstack.order_agent")

MAX_TOOL_ITERATIONS = 5

order_llm = llm.bind_tools(order_tools_list)
tool_map = {t.name: t for t in order_tools_list}

# Patterns to detect identifiers in the user query
ORDER_ID_RE = re.compile(r"ORD-\d+", re.IGNORECASE)
TRACKING_RE = re.compile(r"SS\d+TRK", re.IGNORECASE)
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")


def _extract_identifier(text: str) -> str | None:
    """Try to extract an order ID, tracking ID, or email from text."""
    for pattern in (ORDER_ID_RE, TRACKING_RE, EMAIL_RE):
        match = pattern.search(text)
        if match:
            return match.group()
    return None


def order_agent_node(state: StackState) -> Command[Literal["synthesizer_node"]]:
    """Order Agent — extracts or asks for a lookup key, then runs tools."""

    logger.info("Processing order query...")
    query = state["user_query"]

    # Step 1: Extract identifier or interrupt to ask the user
    lookup_key = _extract_identifier(query)

    if lookup_key:
        logger.info("Found identifier: %s", lookup_key)
    else:
        logger.info("No identifier found — interrupting for user input")
        lookup_key = interrupt(
            "I'd be happy to help with your order! "
            "Could you please provide one of the following?\n"
            "  • Order ID    (e.g. ORD-201)\n"
            "  • Tracking ID (e.g. SS201TRK)\n"
            "  • Email       (e.g. priya@example.com)"
        )
        lookup_key = lookup_key.strip()
        logger.info("User provided: %s", lookup_key)

    # Step 2: Run tool-calling loop
    local_msgs = [
        SystemMessage(content=ORDER_AGENT_PROMPT),
        HumanMessage(content=f"{query}\n\nLookup key: {lookup_key}"),
    ]

    for iteration in range(MAX_TOOL_ITERATIONS):
        response = order_llm.invoke(local_msgs)

        if not getattr(response, "tool_calls", None):
            logger.info("Done (iteration %d)", iteration)
            return Command(
                goto="synthesizer_node",
                update={"messages": [response], "order_response": response.content},
            )

        tool_names = [tc["name"] for tc in response.tool_calls]
        logger.info("Tools: %s (iter %d)", tool_names, iteration)
        local_msgs.append(response)

        for tc in response.tool_calls:
            result = tool_map[tc["name"]].invoke(tc["args"])
            local_msgs.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))

    fallback = response.content or "I couldn't complete the order lookup."
    logger.warning("Hit max iterations (%d)", MAX_TOOL_ITERATIONS)
    return Command(
        goto="synthesizer_node",
        update={"messages": [AIMessage(content=fallback)], "order_response": fallback},
    )
