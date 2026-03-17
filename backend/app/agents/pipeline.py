"""CV generation pipeline — orchestrates LangGraph for tailor, review committee, and synthesis agents.

Two modes:
- Standard: Tailor agent → Validator → done
- Review:   Tailor agent → 3 parallel reviewers + optional hallucination check → Synthesis → Validator → done

Uses LangGraph graph execution for orchestration instead of manual asyncio.gather.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from app.graph.registry import get_generation_graph
from app.graph.state import GenerationState
from app.graph.runtime import GraphRuntimeConfig

logger = logging.getLogger(__name__)


async def generate_cv_standard(
    resume_text: str,
    job_description: str,
    model_name: str,
    api_key: str,
    user_instructions: str | None = None,
) -> dict[str, Any]:
    """Standard pipeline: Tailor → Validate via LangGraph.

    Returns dict with cv_data, ats_issues, hallucination_warnings.
    """
    # Generate unique request ID for thread tracking
    request_id = str(uuid.uuid4())

    # Build state from inputs
    state: GenerationState = {
        "request_id": request_id,
        "resume_text": resume_text,
        "job_description": job_description,
        "user_instructions": user_instructions,
        "review_mode": False,
        "run_hallucination_check": False,
    }

    # Build runtime config (secrets not in state)
    runtime = GraphRuntimeConfig(
        model_name=model_name,
        api_key=api_key,
    )

    # Get compiled graph
    graph = get_generation_graph()

    # Invoke graph
    logger.info("Pipeline: invoking LangGraph with thread_id=%s (standard mode)", request_id)
    result = await graph.ainvoke(
        state,
        config={"configurable": {"thread_id": request_id, "runtime": runtime}}
    )

    # Extract final_response from result state
    final_response = result["final_response"]

    return final_response


async def generate_cv_with_review(
    resume_text: str,
    job_description: str,
    model_name: str,
    api_key: str,
    review_model_name: str,
    review_api_key: str,
    user_instructions: str | None = None,
    run_hallucination_check: bool = True,
) -> dict[str, Any]:
    """Review pipeline: Tailor → Parallel Reviewers (+ optional hallucination check) → Synthesis → Validate via LangGraph.

    Args:
        resume_text: Extracted text from uploaded resume document(s).
        job_description: Target job description text.
        model_name: Model string for the tailor and synthesis agents (e.g., "google:gemini-2.5-pro").
        api_key: API key for the tailor/synthesis model provider.
        review_model_name: Model string for reviewer agents (e.g., "google:gemini-2.5-flash").
        review_api_key: API key for the reviewer model provider.
        user_instructions: Optional user-provided instructions for the tailor agent.
        run_hallucination_check: Whether to run the AI hallucination validator (default True).

    Returns:
        Dict with cv_data, ats_issues, hallucination_warnings, and review_panel.
    """
    # Generate unique request ID for thread tracking
    request_id = str(uuid.uuid4())

    # Build state from inputs
    state: GenerationState = {
        "request_id": request_id,
        "resume_text": resume_text,
        "job_description": job_description,
        "user_instructions": user_instructions,
        "review_mode": True,
        "run_hallucination_check": run_hallucination_check,
    }

    # Build runtime config with review models (secrets not in state)
    runtime = GraphRuntimeConfig(
        model_name=model_name,
        api_key=api_key,
        review_model_name=review_model_name,
        review_api_key=review_api_key,
    )

    # Get compiled graph
    graph = get_generation_graph()

    # Invoke graph
    logger.info(
        "Pipeline: invoking LangGraph with thread_id=%s (review mode, hallucination_check=%s)",
        request_id,
        run_hallucination_check,
    )
    result = await graph.ainvoke(
        state,
        config={"configurable": {"thread_id": request_id, "runtime": runtime}}
    )

    # Extract final_response from result state
    final_response = result["final_response"]

    return final_response

