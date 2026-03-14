"""
agents/menu_agent.py — Menu Discovery Agent.

Uses LangGraph conditional edges instead of a manual tool-calling loop.
- menu_agent_node  → calls the LLM, stores response in menu_messages
- menu_tools_node  → executes tool calls, stores results in menu_messages
- should_continue_menu → conditional edge: tool calls? → tools : → synthesizer
"""

from langchain_core.messages import (
    SystemMessage,
    HumanMessage,
    AIMessage,
    ToolMessage,
)

from snackstack.config import llm
from snackstack.state import StackState
from snackstack.agents.prompts import MENU_AGENT_PROMPT
from snackstack.tools.menu_tools import menu_tools_list
from snackstack.logger import setup_logger

logger = setup_logger("snackstack.menu_agent")

# LLM with menu tools bound
menu_llm = llm.bind_tools(menu_tools_list)
tool_map = {t.name: t for t in menu_tools_list}


def menu_agent_node(state: StackState) -> dict:
    """Call the LLM. On first invocation build the initial prompt
    using persisted conversation history; on subsequent invocations
    (after tool results) continue from menu_messages."""

    existing = state.get("menu_messages") or []

    if not existing:
        # First call — conversation history is persisted via MemorySaver
        logger.info("Processing menu query...")
        history = state.get("messages", [])[-6:]

        all_msgs = [
            SystemMessage(content=MENU_AGENT_PROMPT),
            *history,
            HumanMessage(content=state["user_query"]),
        ]
    else:
        # Subsequent call — tool results already in menu_messages
        logger.info("Menu agent re-invoked after tool results")
        all_msgs = existing

    response = menu_llm.invoke(all_msgs)
    all_msgs = [*all_msgs, response]

    has_tools = bool(getattr(response, "tool_calls", None))
    logger.info("Tool calls: %s", has_tools)

    update: dict = {"menu_messages": all_msgs}

    if not has_tools:
        update["menu_response"] = response.content
        update["messages"] = [response]

    return update


def menu_tools_node(state: StackState) -> dict:
    """Execute tool calls from the last AI message in menu_messages."""

    all_msgs = list(state["menu_messages"])
    last_msg = all_msgs[-1]
    tool_names = [tc["name"] for tc in last_msg.tool_calls]
    logger.info("Executing tools: %s", tool_names)

    for tc in last_msg.tool_calls:
        result = tool_map[tc["name"]].invoke(tc["args"])
        all_msgs.append(
            ToolMessage(content=str(result), tool_call_id=tc["id"])
        )

    return {"menu_messages": all_msgs}


def should_continue_menu(state: StackState) -> str:
    """Conditional edge: route to tools or synthesizer."""
    menu_msgs = state.get("menu_messages") or []
    if menu_msgs:
        last = menu_msgs[-1]
        if getattr(last, "tool_calls", None):
            return "menu_tools_node"
    return "synthesizer_node"