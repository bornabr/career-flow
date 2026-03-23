"""Graph registry for CV generation pipeline.

Provides factory function to retrieve a compiled LangGraph generation graph
with optional checkpointer configuration. This centralizes graph instantiation
and checkpointer setup.
"""

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.state import CompiledStateGraph

from app.graph.build_chat_graphs import build_intake_graph, build_refinement_graph
from app.graph.build_generation_graph import build_generation_graph


def get_generation_graph(checkpointer=None) -> CompiledStateGraph:
    """Get compiled generation graph with optional checkpointer.
    
    Builds and compiles the generation graph with the specified checkpointer.
    If no checkpointer is provided, uses in-memory MemorySaver for session
    state management.
    
    Args:
        checkpointer: Optional checkpointer instance for graph state persistence.
            If None, defaults to MemorySaver (in-memory, non-persistent).
            Typical values:
            - MemorySaver() for development/testing (state lost on restart)
            - SqliteSaver(db_path) for persistence (coming in Phase 5)
        
    Returns:
        CompiledStateGraph: Compiled graph ready for invoke/ainvoke/stream/astream
            with the specified checkpointer configured for state management.
        
    Example:
        >>> graph = get_generation_graph()
        >>> result = graph.invoke(initial_state, config={"configurable": {"thread_id": "1"}})
        
        >>> from langgraph.checkpoint.sqlite import SqliteSaver
        >>> graph_persistent = get_generation_graph(
        ...     checkpointer=SqliteSaver(db_path="graph.db")
        ... )
    """
    if checkpointer is None:
        checkpointer = MemorySaver()
    
    graph = build_generation_graph()
    return graph.compile(checkpointer=checkpointer)


def get_intake_graph(checkpointer=None) -> CompiledStateGraph:
    """Get compiled intake graph with optional checkpointer.

    Builds and compiles the intake graph with the specified checkpointer.
    If no checkpointer is provided, uses in-memory MemorySaver.

    Args:
        checkpointer: Optional checkpointer instance for graph state persistence.

    Returns:
        CompiledStateGraph: Compiled graph ready for invoke/stream.
    """
    if checkpointer is None:
        checkpointer = MemorySaver()

    graph = build_intake_graph()
    return graph.compile(checkpointer=checkpointer)


def get_refinement_graph(checkpointer=None) -> CompiledStateGraph:
    """Get compiled refinement graph with optional checkpointer.

    Builds and compiles the refinement graph with the specified checkpointer.
    If no checkpointer is provided, uses in-memory MemorySaver.

    Args:
        checkpointer: Optional checkpointer instance for graph state persistence.

    Returns:
        CompiledStateGraph: Compiled graph ready for invoke/stream.
    """
    if checkpointer is None:
        checkpointer = MemorySaver()

    graph = build_refinement_graph()
    return graph.compile(checkpointer=checkpointer)
