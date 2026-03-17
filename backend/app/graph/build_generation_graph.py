"""LangGraph state graph builder for CV generation pipeline.

Constructs a StateGraph with 7 nodes and conditional routing:
- Entry: tailor node
- Conditional branching based on review_mode flag
- Parallel execution of three reviewer nodes (HR, Technical, ATS)
- Optional hallucination check node (parallel with reviewers)
- Fan-in via review_join node
- Conditional synthesis routing based on review count
- Exit: validate node

Graph structure mirrors the async pipeline orchestration in agents/pipeline.py
but using LangGraph's declarative graph definition.
"""

from __future__ import annotations

from typing import Any

from langgraph.graph import StateGraph, END
from langgraph.types import Send

from app.graph.state import GenerationState
from app.graph.nodes_generation import (
    tailor_node,
    hr_review_node,
    technical_review_node,
    ats_review_node,
    hallucination_check_node,
    synthesis_node,
    validate_node,
)
from app.schemas.review import ReviewPanelResult


def build_generation_graph() -> StateGraph:
    """Build the generation graph with all nodes and conditional edges.
    
    Returns:
        StateGraph: Compiled graph ready for execution with invoke/stream.
        
    Graph flow:
        START → tailor
                 ├─ review_mode=false → validate → END
                 └─ review_mode=true → parallel fans (hr_review, technical_review, ats_review, hallucination_check)
                                         → review_join
                                         ├─ reviews exist → synthesis → validate → END
                                         └─ no reviews → validate → END
    """
    graph = StateGraph(GenerationState)
    
    # Add all 7 nodes
    graph.add_node("tailor", tailor_node)
    graph.add_node("hr_review", hr_review_node)
    graph.add_node("technical_review", technical_review_node)
    graph.add_node("ats_review", ats_review_node)
    graph.add_node("hallucination_check", hallucination_check_node)
    graph.add_node("synthesis", synthesis_node)
    graph.add_node("validate", validate_node)
    
    # Add the review_join node — constructs review_panel from collected reviews
    async def review_join(state: GenerationState) -> dict[str, Any]:
        """Fan-in node that waits for all parallel reviewers and constructs review_panel.
        
        After all reviewers complete, this node aggregates their ReviewMemos,
        calculates consensus score, and creates the ReviewPanelResult for the API response.
        This follows the same logic as the original pipeline's review orchestration.
        """
        reviews = state.get("reviews", [])
        hallucination_report = state.get("hallucination_report")
        
        # Calculate consensus score from successful reviews
        if reviews and len(reviews) > 0:
            consensus_score = sum(r.overall_score for r in reviews) / len(reviews)
        else:
            consensus_score = 0.0
        
        # Construct review_panel matching original pipeline structure
        review_panel = ReviewPanelResult(
            reviews=reviews,
            hallucination_report=hallucination_report,
            consensus_score=round(consensus_score, 1),
        )
        
        return {"review_panel": review_panel}
    
    graph.add_node("review_join", review_join)
    
    # Set entry point
    graph.set_entry_point("tailor")
    
    # Conditional edge after tailor using routing function that returns Send list
    def route_after_tailor(state: GenerationState) -> str | list[Send]:
        """Route after tailor node based on review_mode flag.
        
        If review_mode is true, returns list[Send] to fan out to reviewer nodes in parallel.
        Otherwise, returns "validate" node name to skip review pipeline.
        
        Args:
            state: Current generation state
            
        Returns:
            list[Send] if review_mode=true, else "validate" node name
        """
        if state.get("review_mode", False):
            # Fan out to all reviewer nodes
            sends = [
                Send("hr_review", state),
                Send("technical_review", state),
                Send("ats_review", state),
            ]
            
            # Include hallucination check in parallel if enabled
            if state.get("run_hallucination_check", False):
                sends.append(Send("hallucination_check", state))
            
            return sends
        
        # Direct path to validate if not in review mode
        return "validate"
    
    # Add conditional edge with mapping for the string returns
    graph.add_conditional_edges(
        "tailor",
        route_after_tailor,
        {"validate": "validate"},  # Maps string returns to node names
    )
    
    # All reviewers route to review_join (these edges are auto-triggered by Send)
    graph.add_edge("hr_review", "review_join")
    graph.add_edge("technical_review", "review_join")
    graph.add_edge("ats_review", "review_join")
    
    # Hallucination check also routes to review_join (runs in parallel with reviewers)
    graph.add_edge("hallucination_check", "review_join")
    
    # Conditional edge after review_join: check if any reviews exist
    def route_after_review_join(state: GenerationState) -> str:
        """Route after review_join based on whether reviews exist.
        
        If any reviews were collected from the reviewer agents, route to synthesis
        to refine the CV with their recommendations. Otherwise, skip synthesis
        and go directly to validate.
        
        Args:
            state: Current generation state
            
        Returns:
            "synthesis" if reviews exist (len > 0), else "validate"
        """
        reviews = state.get("reviews", [])
        if reviews and len(reviews) > 0:
            return "synthesis"
        return "validate"
    
    graph.add_conditional_edges(
        "review_join",
        route_after_review_join,
        {
            "synthesis": "synthesis",
            "validate": "validate",
        },
    )
    
    # Edge from synthesis to validate
    graph.add_edge("synthesis", "validate")
    
    # Edge from validate to END
    graph.add_edge("validate", END)
    
    return graph
