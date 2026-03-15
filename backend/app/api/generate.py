"""Generate API routes - CV generation via agentic AI pipeline."""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.agents.tailor import tailor_cv
from app.agents.validator import validate_cv
from app.config import get_settings, AVAILABLE_MODELS

logger = logging.getLogger(__name__)

router = APIRouter()


class GenerateRequest(BaseModel):
    """Request body for CV generation."""

    resume_text: str
    job_description: str
    user_instructions: str | None = None
    api_key: str | None = None
    model_name: str | None = None


class GenerateResponse(BaseModel):
    """Response body for CV generation."""

    cv_data: dict
    ats_issues: list[str]
    hallucination_warnings: list[str]


@router.post("/generate", response_model=GenerateResponse)
async def generate_cv(request: GenerateRequest):
    """Generate a tailored CV using the agentic pipeline.

    Pipeline: resume_text + job_description → Tailor Agent → Validator → cleaned CV

    The api_key in the request body takes priority over the server-level API key.
    The model_name in the request body overrides the server default (format: "provider:model-id").
    """
    settings = get_settings()

    # Resolve model name: request override > server default
    model_name = request.model_name or settings.model_name

    # Extract provider from the selected model to resolve the correct API key
    provider = model_name.split(":")[0] if ":" in model_name else "openai"

    api_key = request.api_key or settings.resolve_api_key_for_provider(provider)
    if not api_key:
        raise HTTPException(
            status_code=400,
            detail=f"No API key available for provider '{provider}'. "
            f"Set the appropriate API key env var or pass api_key in request body.",
        )

    try:
        cv = await tailor_cv(
            resume_text=request.resume_text,
            job_description=request.job_description,
            model_name=model_name,
            api_key=api_key,
            user_instructions=request.user_instructions,
        )
    except Exception:
        logger.exception("Tailor agent failed")
        raise HTTPException(status_code=502, detail="CV generation failed — LLM error")

    cv_dict = cv.model_dump(mode="json")
    result = validate_cv(cv_dict, request.resume_text)

    return GenerateResponse(
        cv_data=result["cv_data"],
        ats_issues=result["ats_issues"],
        hallucination_warnings=result["hallucination_warnings"],
    )


@router.get("/models")
async def get_models():
    """Return available LLM models grouped by provider.

    Only providers that have a server-side API key configured are
    included in ``available_providers``.  The frontend uses this list
    to filter the provider dropdown so users cannot select a provider
    that has no key.

    Returns:
        {
            "providers": {"google": [...], "openai": [...], "anthropic": [...]},
            "available_providers": ["google"],
            "default": "google:gemini-2.5-pro"
        }
    """
    settings = get_settings()

    available_providers: list[str] = [
        provider
        for provider in AVAILABLE_MODELS
        if settings.resolve_api_key_for_provider(provider)
    ]

    return {
        "providers": AVAILABLE_MODELS,
        "available_providers": available_providers,
        "default": settings.model_name,
    }
