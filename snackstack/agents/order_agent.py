"""
agents/order_agent.py — Order Support Agent with Human-in-the-Loop.

Uses LangGraph conditional edges instead of a manual tool-calling loop.
- order_agent_node  → extracts/asks for ID, calls the LLM
- order_tools_node  → executes tool calls
- should_continue_order → conditional edge: tool calls? → tools : → synthesizer

If the user query doesn't contain an order ID, tracking ID, or email,
the agent uses interrupt() to pause and ask the user before proceeding.
"""

import re
from langchain_core.messages import (
    SystemMessage,
    HumanMessage,
    AIMessage,
    ToolMessage,
)
from langgraph.types import interrupt

from snackstack.config import llm
from snackstack.state import StackState
from snackstack.agents.prompts import ORDER_AGENT_PROMPT
from snackstack.tools.order_tools import order_tools_list
from snackstack.logger import setup_logger

logger = setup_logger("snackstack.order_agent")

order_llm = llm.bind_tools(order_tools_list)
tool_map = {t.name: t for t in order_tools_list}

# Patterns to detect identifiers in the user query
ORDER_ID_RE = re.compile(r"ORD-\d+", re.IGNORECASE)
TRACKING_RE = re.compile(r"SS\d+TRK", re.IGNORECASE)
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")


def extract_identifier(text: str) -> str | None:
    """Try to extract an order ID, tracking ID, or email from text."""
    for pattern in (ORDER_ID_RE, TRACKING_RE, EMAIL_RE):
        match = pattern.search(text)
        if match:
            return match.group()
    return None


def order_agent_node(state: StackState) -> dict:
    """Call the LLM. On first invocation handle HITL for missing IDs;
    on subsequent invocations continue after tool results."""

    existing = state.get("order_messages") or []

    if not existing:
        # First call — extract identifier or interrupt
        logger.info("Processing order query...")
        query = state["user_query"]
        lookup_key = extract_identifier(query)

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

        all_msgs = [
            SystemMessage(content=ORDER_AGENT_PROMPT),
            HumanMessage(content=f"{query}\n\nLookup key: {lookup_key}"),
        ]
    else:
        # Subsequent call — tool results already in order_messages
        logger.info("Order agent re-invoked after tool results")
        all_msgs = existing

    response = order_llm.invoke(all_msgs)
    all_msgs = [*all_msgs, response]

    has_tools = bool(getattr(response, "tool_calls", None))
    logger.info("Tool calls: %s", has_tools)

    update: dict = {"order_messages": all_msgs}

    if not has_tools:
        update["order_response"] = response.content
        update["messages"] = [response]

    return update


def order_tools_node(state: StackState) -> dict:
    """Execute tool calls from the last AI message in order_messages."""

    all_msgs = list(state["order_messages"])
    last_msg = all_msgs[-1]
    tool_names = [tc["name"] for tc in last_msg.tool_calls]
    logger.info("Executing tools: %s", tool_names)

    for tc in last_msg.tool_calls:
        result = tool_map[tc["name"]].invoke(tc["args"])
        all_msgs.append(
            ToolMessage(content=str(result), tool_call_id=tc["id"])
        )

    return {"order_messages": all_msgs}


def should_continue_order(state: StackState) -> str:
    """Conditional edge: route to tools or synthesizer."""
    order_msgs = state.get("order_messages") or []
    if order_msgs:
        last = order_msgs[-1]
        if getattr(last, "tool_calls", None):
            return "order_tools_node"
    return "synthesizer_node"