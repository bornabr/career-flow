from __future__ import annotations

import logging
from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.config import get_stream_writer

from app.agents.ats_reviewer import review_as_ats
from app.agents.hallucination_checker import check_hallucinations_ai
from app.agents.hr_reviewer import review_as_hr
from app.agents.synthesis import synthesize_cv
from app.agents.tailor import tailor_cv
from app.agents.technical_reviewer import review_as_technical
from app.agents.validator import validate_cv
from app.graph.events import (
    emit_review_failed,
    emit_review_memo,
    emit_step_completed,
    emit_step_started,
    emit_validation_completed,
)
from app.graph.runtime import GraphRuntimeConfig
from app.graph.state import GenerationState
from app.schemas.review import ReviewMemo

logger = logging.getLogger(__name__)


async def tailor_node(state: GenerationState, config: RunnableConfig) -> dict[str, Any]:
    """Generate initial CV draft from resume and job description using tailor agent.
    
    This node wraps the tailor_cv agent function to produce a structured CV from
    the original resume and target job description. The output becomes the basis
    for review and synthesis stages.
    """
    writer = get_stream_writer()
    emit_step_started(writer, "generation")
    
    runtime: GraphRuntimeConfig = config["configurable"]["runtime"]
    
    cv = await tailor_cv(
        resume_text=state["resume_text"],
        job_description=state["job_description"],
        model_name=runtime.model_name,
        api_key=runtime.api_key,
        user_instructions=state.get("user_instructions"),
    )
    
    emit_step_completed(writer, "generation")
    
    return {
        "draft_cv": cv,
        "current_cv_dict": cv.model_dump(mode="json"),
    }


async def hr_review_node(state: GenerationState, config: RunnableConfig) -> dict[str, Any]:
    """HR reviewer agent node for assessing career fit and presentation.
    
    Wraps review_as_hr to evaluate the CV from an HR perspective: career progression,
    role alignment, cultural fit signals, and red flags. On failure, appends error
    dict to review_errors rather than raising, allowing other reviewers to continue.
    """
    writer = get_stream_writer()
    emit_step_started(writer, "hr_review")
    
    runtime: GraphRuntimeConfig = config["configurable"]["runtime"]
    review_model = runtime.review_model_name or runtime.model_name
    review_key = runtime.review_api_key or runtime.api_key
    
    try:
        review = await review_as_hr(
            cv_data=state["current_cv_dict"],
            job_description=state["job_description"],
            model_name=review_model,
            api_key=review_key,
        )
        item_keys = [f"hr:{i}" for i in range(len(review.priority_changes))]
        emit_review_memo(writer, "hr", review.model_dump(), item_keys)
        emit_step_completed(writer, "hr_review")
        return {"reviews": [review]}
    except Exception as exc:
        logger.error("HR reviewer failed: %s", exc)
        emit_review_failed(writer, "hr", str(exc))
        return {"review_errors": [{"reviewer": "hr", "error": str(exc)}]}


async def technical_review_node(state: GenerationState, config: RunnableConfig) -> dict[str, Any]:
    """Technical reviewer agent node for assessing technical depth and credibility.
    
    Wraps review_as_technical to evaluate the CV from a technical lead perspective:
    technical depth, stack relevance, project credibility, skill progression.
    On failure, appends error dict to review_errors rather than raising.
    """
    writer = get_stream_writer()
    emit_step_started(writer, "technical_review")
    
    runtime: GraphRuntimeConfig = config["configurable"]["runtime"]
    review_model = runtime.review_model_name or runtime.model_name
    review_key = runtime.review_api_key or runtime.api_key
    
    try:
        review = await review_as_technical(
            cv_data=state["current_cv_dict"],
            job_description=state["job_description"],
            model_name=review_model,
            api_key=review_key,
        )
        item_keys = [f"technical:{i}" for i in range(len(review.priority_changes))]
        emit_review_memo(writer, "technical", review.model_dump(), item_keys)
        emit_step_completed(writer, "technical_review")
        return {"reviews": [review]}
    except Exception as exc:
        logger.error("Technical reviewer failed: %s", exc)
        emit_review_failed(writer, "technical", str(exc))
        return {"review_errors": [{"reviewer": "technical", "error": str(exc)}]}


async def ats_review_node(state: GenerationState, config: RunnableConfig) -> dict[str, Any]:
    """ATS reviewer agent node for optimizing applicant tracking system compatibility.
    
    Wraps review_as_ats to evaluate the CV from an ATS optimization perspective:
    keyword coverage, keyword placement, section structure, formatting compliance.
    On failure, appends error dict to review_errors rather than raising.
    """
    writer = get_stream_writer()
    emit_step_started(writer, "ats_review")
    
    runtime: GraphRuntimeConfig = config["configurable"]["runtime"]
    review_model = runtime.review_model_name or runtime.model_name
    review_key = runtime.review_api_key or runtime.api_key
    
    try:
        review = await review_as_ats(
            cv_data=state["current_cv_dict"],
            job_description=state["job_description"],
            model_name=review_model,
            api_key=review_key,
        )
        item_keys = [f"ats:{i}" for i in range(len(review.priority_changes))]
        emit_review_memo(writer, "ats", review.model_dump(), item_keys)
        emit_step_completed(writer, "ats_review")
        return {"reviews": [review]}
    except Exception as exc:
        logger.error("ATS reviewer failed: %s", exc)
        emit_review_failed(writer, "ats", str(exc))
        return {"review_errors": [{"reviewer": "ats", "error": str(exc)}]}


async def hallucination_check_node(state: GenerationState, config: RunnableConfig) -> dict[str, Any]:
    """AI-powered hallucination detector for semantic accuracy validation.
    
    Wraps check_hallucinations_ai to detect fabricated or embellished CV claims
    against the original resume text using semantic comparison. On failure, logs
    error and returns empty dict (graceful degradation without pipeline disruption).
    """
    writer = get_stream_writer()
    emit_step_started(writer, "hallucination_check")
    
    runtime: GraphRuntimeConfig = config["configurable"]["runtime"]
    
    try:
        report = await check_hallucinations_ai(
            cv_data=state["current_cv_dict"],
            original_resume=state["resume_text"],
            model_name=runtime.model_name,
            api_key=runtime.api_key,
        )
        emit_step_completed(writer, "hallucination_check")
        return {"hallucination_report": report}
    except Exception as exc:
        logger.error("Hallucination checker failed: %s", exc)
        emit_step_completed(writer, "hallucination_check")
        return {}


async def review_apply_node(state: GenerationState) -> dict[str, Any]:
    reviews = state.get("reviews", [])
    review_decisions = state.get("review_decisions")

    if not reviews:
        return {"filtered_reviews": []}

    if not review_decisions:
        return {"filtered_reviews": [memo.model_copy(deep=True) for memo in reviews]}

    filtered_reviews: list[ReviewMemo] = []
    for memo in reviews:
        accepted_priority_changes = [
            priority_change
            for index, priority_change in enumerate(memo.priority_changes)
            if review_decisions.get(f"{memo.reviewer_role}:{index}", False)
        ]

        if not accepted_priority_changes:
            continue

        filtered_reviews.append(
            memo.model_copy(
                update={"priority_changes": accepted_priority_changes},
                deep=True,
            )
        )

    return {"filtered_reviews": filtered_reviews}


async def synthesis_node(state: GenerationState, config: RunnableConfig) -> dict[str, Any]:
    """Synthesis agent node for refining CV based on reviewer feedback.
    
    Wraps synthesize_cv to incorporate recommendations from all three reviewers
    (HR, Technical, ATS) into an improved CV draft. Runs only if reviews exist
    (checked by conditional routing). Treats all reviewer perspectives with equal weight.
    """
    writer = get_stream_writer()
    emit_step_started(writer, "synthesis")
    
    runtime: GraphRuntimeConfig = config["configurable"]["runtime"]
    filtered_state = await review_apply_node(state)
    filtered_reviews: list[ReviewMemo] = filtered_state["filtered_reviews"]
    
    refined_cv = await synthesize_cv(
        cv_data=state["current_cv_dict"],
        reviews=filtered_reviews,
        resume_text=state["resume_text"],
        job_description=state["job_description"],
        model_name=runtime.model_name,
        api_key=runtime.api_key,
    )
    
    emit_step_completed(writer, "synthesis")
    
    return {
        "filtered_reviews": filtered_reviews,
        "current_cv_dict": refined_cv.model_dump(mode="json"),
    }


async def validate_node(state: GenerationState, config: RunnableConfig) -> dict[str, Any]:
    """Deterministic post-generation validation node.
    
    Wraps validate_cv (no LLM calls) to perform ATS cleaning, fuzzy hallucination
    detection, and empty section removal. Populates final_response for API return.
    """
    writer = get_stream_writer()
    emit_step_started(writer, "validation")
    
    result = validate_cv(
        cv_data=state["current_cv_dict"],
        original_resume=state["resume_text"],
    )
    
    emit_validation_completed(
        writer,
        ats_issues=result["ats_issues"],
        hallucination_warnings=result["hallucination_warnings"],
    )
    
    # Build final_response dict matching the API contract
    # In standard mode: review_panel is None
    # In review mode: review_panel is ReviewPanelResult (populated by review_join node)
    review_panel = state.get("review_panel")
    
    final_response = {
        "cv_data": result["cv_data"],
        "ats_issues": result["ats_issues"],
        "hallucination_warnings": result["hallucination_warnings"],
        "review_panel": review_panel.model_dump(mode="json") if review_panel else None,
    }
    
    emit_step_completed(writer, "validation")
    
    return {
        "validation_result": result,
        "final_response": final_response,
    }
