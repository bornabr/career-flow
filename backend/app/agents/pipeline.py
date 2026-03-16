"""CV generation pipeline — orchestrates tailor, review committee, and synthesis agents.

Two modes:
- Standard: Tailor agent → Validator → done
- Review:   Tailor agent → 3 parallel reviewers + optional hallucination check → Synthesis → Validator → done

The review mode runs HR, Technical, and ATS reviewer agents in parallel via asyncio.gather,
collects their ReviewMemos, then feeds them to the Synthesis agent for a refined CV.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.agents.tailor import tailor_cv
from app.agents.validator import validate_cv
from app.agents.hr_reviewer import review_as_hr
from app.agents.technical_reviewer import review_as_technical
from app.agents.ats_reviewer import review_as_ats
from app.agents.synthesis import synthesize_cv
from app.agents.hallucination_checker import check_hallucinations_ai
from app.schemas.cv import CV
from app.schemas.review import ReviewMemo, ReviewPanelResult, HallucinationReport

logger = logging.getLogger(__name__)


async def generate_cv_standard(
    resume_text: str,
    job_description: str,
    model_name: str,
    api_key: str,
    user_instructions: str | None = None,
) -> dict[str, Any]:
    """Standard pipeline: Tailor → Validate.

    Returns dict with cv_data, ats_issues, hallucination_warnings.
    """
    cv = await tailor_cv(
        resume_text=resume_text,
        job_description=job_description,
        model_name=model_name,
        api_key=api_key,
        user_instructions=user_instructions,
    )

    cv_dict = cv.model_dump(mode="json")
    result = validate_cv(cv_dict, resume_text)

    return {
        "cv_data": result["cv_data"],
        "ats_issues": result["ats_issues"],
        "hallucination_warnings": result["hallucination_warnings"],
        "review_panel": None,
    }


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
    """Review pipeline: Tailor → Parallel Reviewers (+ optional hallucination check) → Synthesis → Validate.

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
    # Step 1: Generate initial CV draft
    logger.info("Pipeline: generating initial CV draft with %s", model_name)
    cv = await tailor_cv(
        resume_text=resume_text,
        job_description=job_description,
        model_name=model_name,
        api_key=api_key,
        user_instructions=user_instructions,
    )
    cv_dict = cv.model_dump(mode="json")

    # Step 2: Run reviewers in parallel (+ optional hallucination check)
    logger.info("Pipeline: running review committee in parallel with %s", review_model_name)

    review_tasks: list[asyncio.Task[ReviewMemo]] = [
        asyncio.create_task(
            review_as_hr(cv_dict, job_description, review_model_name, review_api_key),
            name="hr_review",
        ),
        asyncio.create_task(
            review_as_technical(cv_dict, job_description, review_model_name, review_api_key),
            name="technical_review",
        ),
        asyncio.create_task(
            review_as_ats(cv_dict, job_description, review_model_name, review_api_key),
            name="ats_review",
        ),
    ]

    hallucination_task: asyncio.Task[HallucinationReport] | None = None
    if run_hallucination_check:
        hallucination_task = asyncio.create_task(
            check_hallucinations_ai(cv_dict, resume_text, review_model_name, review_api_key),
            name="hallucination_check",
        )

    # Gather all review results
    review_results: list[ReviewMemo | BaseException] = await asyncio.gather(
        *review_tasks, return_exceptions=True
    )

    # Process review results — log failures but continue with successful reviews
    reviews: list[ReviewMemo] = []
    reviewer_names = ["HR", "Technical", "ATS"]
    for i, result in enumerate(review_results):
        if isinstance(result, BaseException):
            logger.error("Reviewer %s failed: %s", reviewer_names[i], result)
        else:
            reviews.append(result)

    # Collect hallucination report if requested
    hallucination_report: HallucinationReport | None = None
    if hallucination_task is not None:
        try:
            hallucination_report = await hallucination_task
        except Exception as exc:
            logger.error("Hallucination check failed: %s", exc)

    # Calculate consensus score
    if reviews:
        consensus_score = sum(r.overall_score for r in reviews) / len(reviews)
    else:
        consensus_score = 0.0

    review_panel = ReviewPanelResult(
        reviews=reviews,
        hallucination_report=hallucination_report,
        consensus_score=round(consensus_score, 1),
    )

    # Step 3: Synthesis — refine CV based on reviewer feedback (only if we got reviews)
    if reviews:
        logger.info(
            "Pipeline: synthesizing refined CV (consensus score: %.1f/10) with %s",
            consensus_score,
            model_name,
        )
        refined_cv = await synthesize_cv(
            cv_data=cv_dict,
            reviews=reviews,
            resume_text=resume_text,
            job_description=job_description,
            model_name=model_name,
            api_key=api_key,
        )
        cv_dict = refined_cv.model_dump(mode="json")
    else:
        logger.warning("Pipeline: all reviewers failed, skipping synthesis step")

    # Step 4: Validate the final CV
    logger.info("Pipeline: validating final CV")
    validation_result = validate_cv(cv_dict, resume_text)

    return {
        "cv_data": validation_result["cv_data"],
        "ats_issues": validation_result["ats_issues"],
        "hallucination_warnings": validation_result["hallucination_warnings"],
        "review_panel": review_panel.model_dump(mode="json"),
    }
