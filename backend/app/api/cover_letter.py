"""Cover letter API routes."""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.agents.cover_letter import generate_cover_letter, CoverLetter
from app.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter()


class CoverLetterRequest(BaseModel):
    """Request body for cover letter generation."""

    cv_data: dict
    job_description: str
    company_name: str | None = None
    user_instructions: str | None = None
    api_key: str | None = None


class CoverLetterResponse(BaseModel):
    """Response body for cover letter generation."""

    greeting: str
    opening: str
    body: list[str]
    closing: str
    sign_off: str
    full_text: str


@router.post("/cover-letter", response_model=CoverLetterResponse)
async def create_cover_letter(request: CoverLetterRequest):
    """Generate a tailored cover letter from CV data and job description.

    Uses the same LLM provider configured for CV generation.
    """
    settings = get_settings()

    api_key = request.api_key or settings.resolved_api_key
    if not api_key:
        raise HTTPException(
            status_code=400,
            detail="No API key provided. Set API_KEY env var or pass api_key in request body.",
        )

    try:
        letter = await generate_cover_letter(
            cv_data=request.cv_data,
            job_description=request.job_description,
            model_name=settings.model_name,
            api_key=api_key,
            company_name=request.company_name,
            user_instructions=request.user_instructions,
        )
    except Exception:
        logger.exception("Cover letter generation failed")
        raise HTTPException(status_code=502, detail="Cover letter generation failed — LLM error")

    # Assemble full text for convenience
    body_text = "\n\n".join(letter.body)
    full_text = f"{letter.greeting}\n\n{letter.opening}\n\n{body_text}\n\n{letter.closing}\n\n{letter.sign_off}"

    return CoverLetterResponse(
        greeting=letter.greeting,
        opening=letter.opening,
        body=letter.body,
        closing=letter.closing,
        sign_off=letter.sign_off,
        full_text=full_text,
    )
