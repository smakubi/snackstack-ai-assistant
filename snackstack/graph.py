"""
graph.py — Build and compile the SnackStack LangGraph StateGraph.

Graph topology:
    START → orchestrator → ┬─ menu_agent_node  ─┬→ synthesizer_node → END
                           └─ order_agent_node ─┘
    (agents dispatched in parallel via Send() when both are needed)

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
    order_agent_node,
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
    builder.add_node("order_agent_node", order_agent_node)
    builder.add_node("synthesizer_node", synthesizer_node)

    # ── Edges ───────────────────────────────────────────────
    builder.add_edge(START, "orchestrator")
    # orchestrator → agent(s) routing is handled inside the node
    # via Command + Send()
    builder.add_edge("synthesizer_node", END)

    # ── Compile with memory ─────────────────────────────────
    memory = MemorySaver()
    graph = builder.compile(checkpointer=memory)

    logger.info("SnackStack graph compiled")
    return graph
