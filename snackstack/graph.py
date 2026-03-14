"""
graph.py — Build and compile the SnackStack LangGraph StateGraph.

Graph topology (conditional edges shown as dashed):
    START → orchestrator ─ ─ ─ ┬─ menu_agent_node ─ ─ ─ menu_tools_node ─┐
                                │       ↑________________________ ________┘
                                │       └─ ─ ─ ─ → synthesizer_node → END
                                │
                                └─ order_agent_node ─ ─ ─ order_tools_node ─┐
                                        ↑___________________________________┘
                                        └─ ─ ─ ─ → synthesizer_node → END

    Orchestrator dispatches agents conditionally via Send().
    Each agent uses a conditional edge to route to its tools node
    or directly to the synthesizer.

HITL:
    order_agent_node uses interrupt() to pause execution when the user
    query is missing an order ID / tracking ID / email.  The caller
    resumes with Command(resume=<user_input>).
"""

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from snackstack.state import StackState
from snackstack.agents import (
    orchestrator_node,
    menu_agent_node,
    menu_tools_node,
    should_continue_menu,
    order_agent_node,
    order_tools_node,
    should_continue_order,
    synthesizer_node,
)
from snackstack.logger import setup_logger

logger = setup_logger("snackstack.graph")


def build_graph():
    """Construct, compile, and return the SnackStack graph."""

    builder = StateGraph(StackState)

    # ── Nodes ───────────────────────────────────────────────
    builder.add_node("orchestrator", orchestrator_node)
    builder.add_node("menu_agent_node", menu_agent_node)
    builder.add_node("menu_tools_node", menu_tools_node)
    builder.add_node("order_agent_node", order_agent_node)
    builder.add_node("order_tools_node", order_tools_node)
    builder.add_node("synthesizer_node", synthesizer_node)

    # ── Edges ───────────────────────────────────────────────

    # START → orchestrator (fixed)
    builder.add_edge(START, "orchestrator")
    # orchestrator → agent(s) routing handled via Command + Send()

    # Menu agent: conditional → tools (loop) or synthesizer
    builder.add_conditional_edges(
        "menu_agent_node",
        should_continue_menu,
        {"menu_tools_node": "menu_tools_node", "synthesizer_node": "synthesizer_node"},
    )
    builder.add_edge("menu_tools_node", "menu_agent_node")

    # Order agent: conditional → tools (loop) or synthesizer
    builder.add_conditional_edges(
        "order_agent_node",
        should_continue_order,
        {"order_tools_node": "order_tools_node", "synthesizer_node": "synthesizer_node"},
    )
    builder.add_edge("order_tools_node", "order_agent_node")

    # Synthesizer → END (fixed)
    builder.add_edge("synthesizer_node", END)

    # ── Compile with memory ─────────────────────────────────
    memory = MemorySaver()
    graph = builder.compile(checkpointer=memory)

    logger.info("SnackStack graph compiled")
    return graph