"""LangGraph state graph builders for chat flows.

Constructs StateGraphs for intake and refinement:
- Intake graph: Single node that processes intake turns until ready_to_generate
- Refinement graph: Single node that processes refinement edits
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from app.graph.chat_state import IntakeState, RefinementState
from app.graph.nodes_chat import intake_node, refinement_node


def build_intake_graph() -> StateGraph:
    """Build the intake graph with intake node.

    Returns:
        StateGraph: Uncompiled graph ready for compilation.

    Graph flow:
        START → intake → END
    """
    graph = StateGraph(IntakeState)

    graph.add_node("intake", intake_node)
    graph.set_entry_point("intake")
    graph.add_edge("intake", END)

    return graph


def build_refinement_graph() -> StateGraph:
    """Build the refinement graph with refinement node.

    Returns:
        StateGraph: Uncompiled graph ready for compilation.

    Graph flow:
        START → refinement → END
    """
    graph = StateGraph(RefinementState)

    graph.add_node("refinement", refinement_node)
    graph.set_entry_point("refinement")
    graph.add_edge("refinement", END)

    return graph
