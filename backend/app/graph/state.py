from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict

from app.schemas.cv import CV
from app.schemas.review import ReviewMemo, HallucinationReport, ReviewPanelResult, InteractiveReviewMemo


class GenerationState(TypedDict, total=False):
    """LangGraph state for CV generation pipeline.

    Attributes:
        request_id: Unique identifier for this generation request
        resume_text: Original resume text input
        job_description: Target job description
        user_instructions: Optional custom instructions from user
        review_mode: Whether to run review committee pipeline
        run_hallucination_check: Whether to run AI hallucination validator
        draft_cv: Initial CV from tailor agent (CV object)
        current_cv_dict: Current CV as dict (for passing between nodes)
        reviews: List of ReviewMemo objects from reviewer agents (reducer: append)
        review_errors: List of error dicts when reviewers fail (reducer: append)
        hallucination_report: Optional hallucination analysis report
        review_panel: Aggregated review panel result
        filtered_reviews: Review memos filtered by user item-level decisions
        validation_result: Output from validator (ats_issues, hallucination_warnings)
        final_response: Final API response dict
    """
    request_id: str
    resume_text: str
    job_description: str
    user_instructions: str | None
    review_mode: bool
    run_hallucination_check: bool
    draft_cv: CV | None
    current_cv_dict: dict[str, Any] | None
    reviews: Annotated[list[ReviewMemo], operator.add]
    review_errors: Annotated[list[dict[str, str]], operator.add]
    hallucination_report: HallucinationReport | None
    review_panel: ReviewPanelResult | None
    interactive_reviews: list[InteractiveReviewMemo]
    awaiting_review_approval: bool
    review_decisions: dict[str, bool] | None
    filtered_reviews: list[ReviewMemo]
    validation_result: dict[str, Any] | None
    final_response: dict[str, Any] | None
