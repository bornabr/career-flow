"""Server-Sent Events (SSE) streaming support for LangGraph generation pipeline.

Provides utilities for formatting and streaming graph execution progress to
frontend clients via EventSource/fetch SSE connections.
"""

from __future__ import annotations

import json
import logging
from typing import Any, AsyncIterator

from langgraph.graph.state import CompiledStateGraph

from app.graph.runtime import GraphRuntimeConfig
from app.graph.state import GenerationState

logger = logging.getLogger(__name__)


def format_sse(data: dict[str, Any]) -> str:
    """Format data as Server-Sent Event frame.
    
    Args:
        data: Dictionary to send (must be JSON-serializable)
        
    Returns:
        SSE-formatted string: 'data: {json}\\n\\n'
    """
    return f"data: {json.dumps(data)}\n\n"


async def stream_generation(
    state: GenerationState,
    config: dict[str, Any],
    graph: CompiledStateGraph,
) -> AsyncIterator[str]:
    """Stream generation progress as Server-Sent Events.
    
    Wraps graph.astream() to consume custom events and state updates,
    formatting each as an SSE frame for real-time frontend consumption.
    
    Args:
        state: Initial generation state
        config: Graph config with thread_id and runtime
        graph: Compiled generation graph
        
    Yields:
        SSE-formatted strings (data: {...}\\n\\n)
    """
    try:
        async for chunk in graph.astream(
            state,
            config=config,
            stream_mode=["custom", "updates"],
        ):
            # With stream_mode=["custom", "updates"], chunks are tuples (namespace, value)
            if not isinstance(chunk, tuple) or len(chunk) != 2:
                continue

            ns, value = chunk

            if ns == "custom":
                # Custom events from nodes (via get_stream_writer)
                yield format_sse(value)

            elif ns == "updates":
                # State updates from node completions — value is dict of {node_name: output}
                if isinstance(value, dict):
                    for node_name in value:
                        yield format_sse({
                            "type": "node.completed",
                            "data": {"node_name": node_name}
                        })
    
    except Exception as exc:
        logger.error(f"Stream generation error: {exc}")
        yield format_sse({
            "type": "error",
            "data": {"message": str(exc)}
        })
