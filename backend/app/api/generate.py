"""Generate API routes — CV generation via agentic AI pipeline.

Supports two modes:
- Standard (default): Tailor agent → Validator → response
- Review (review_mode=true): Tailor → Parallel reviewers → Synthesis → Validator → response
"""

import logging
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.agents.pipeline import generate_cv_standard, generate_cv_with_review
from app.api.sse import stream_generation
from app.config import get_settings, AVAILABLE_MODELS
from app.graph.registry import get_generation_graph
from app.graph.runtime import GraphRuntimeConfig
from app.graph.state import GenerationState

logger = logging.getLogger(__name__)

router = APIRouter()


class GenerateRequest(BaseModel):
    """Request body for CV generation."""

    resume_text: str
    job_description: str
    user_instructions: str | None = None
    api_key: str | None = None
    model_name: str | None = None

    # Review committee options
    review_mode: bool = Field(
        default=False,
        description="Enable review committee pipeline (HR, Technical, ATS reviewers → Synthesis). "
        "When false, uses the standard single-agent pipeline.",
    )
    review_model: str | None = Field(
        default=None,
        description="Model for reviewer agents (e.g., 'google:gemini-2.5-flash'). "
        "Defaults to server setting (default_review_model). "
        "Can use a cheaper/faster model than the main generation model.",
    )


class GenerateResponse(BaseModel):
    """Response body for CV generation."""

    cv_data: dict[str, Any]
    ats_issues: list[str]
    hallucination_warnings: list[str]
    review_panel: dict[str, Any] | None = Field(
        default=None,
        description="Review panel results (scores, findings, recommendations) — only present when review_mode=true.",
    )


def _resolve_api_key(settings: Any, provider: str, request_api_key: str | None) -> str:
    """Resolve API key for a provider: request override → server config."""
    api_key = request_api_key or settings.resolve_api_key_for_provider(provider)
    if not api_key:
        raise HTTPException(
            status_code=400,
            detail=f"No API key available for provider '{provider}'. "
            f"Set the appropriate API key env var or pass api_key in request body.",
        )
    return api_key


@router.post("/generate", response_model=GenerateResponse)
async def generate_cv(request: GenerateRequest):
    """Generate a tailored CV using the agentic pipeline.

    Standard pipeline: resume_text + job_description → Tailor Agent → Validator → cleaned CV
    Review pipeline:   resume_text + job_description → Tailor → 3 Reviewers (parallel) → Synthesis → Validator

    The api_key in the request body takes priority over the server-level API key.
    The model_name overrides the server default (format: "provider:model-id").
    """
    settings = get_settings()

    # Resolve main model
    model_name = request.model_name or settings.model_name
    provider = model_name.split(":")[0] if ":" in model_name else "openai"
    api_key = _resolve_api_key(settings, provider, request.api_key)

    if request.review_mode:
        # Resolve review model (may be a different provider/model)
        review_model = request.review_model or settings.default_review_model
        review_provider = review_model.split(":")[0] if ":" in review_model else "openai"
        review_api_key = _resolve_api_key(settings, review_provider, request.api_key)

        try:
            result = await generate_cv_with_review(
                resume_text=request.resume_text,
                job_description=request.job_description,
                model_name=model_name,
                api_key=api_key,
                review_model_name=review_model,
                review_api_key=review_api_key,
                user_instructions=request.user_instructions,
            )
        except Exception:
            logger.exception("Review pipeline failed")
            raise HTTPException(status_code=502, detail="CV generation failed — review pipeline error")
    else:
        try:
            result = await generate_cv_standard(
                resume_text=request.resume_text,
                job_description=request.job_description,
                model_name=model_name,
                api_key=api_key,
                user_instructions=request.user_instructions,
            )
        except Exception:
            logger.exception("Standard pipeline failed")
            raise HTTPException(status_code=502, detail="CV generation failed — LLM error")

    return GenerateResponse(
        cv_data=result["cv_data"],
        ats_issues=result["ats_issues"],
        hallucination_warnings=result["hallucination_warnings"],
        review_panel=result.get("review_panel"),
    )


class StreamGenerateRequest(BaseModel):
    """Request body for streaming CV generation."""

    resume_text: str
    job_description: str
    user_instructions: str | None = None
    api_key: str | None = None
    model_name: str | None = None
    review_mode: bool = False
    review_model: str | None = None
    run_hallucination_check: bool = False
    thread_id: str | None = None


@router.post("/generate/stream")
async def generate_cv_stream(request: StreamGenerateRequest, http_request: Request):
    """Stream CV generation progress via Server-Sent Events.
    
    Same functionality as /api/generate but returns real-time progress events
    instead of blocking until completion.
    """
    settings = get_settings()
    
    # Resolve main model
    resolved_model = request.model_name or settings.model_name
    provider = resolved_model.split(":")[0] if ":" in resolved_model else "openai"
    resolved_api_key = _resolve_api_key(settings, provider, request.api_key)
    
    # Optional review model resolution
    if request.review_mode:
        resolved_review_model = request.review_model or settings.default_review_model
        review_provider = resolved_review_model.split(":")[0] if ":" in resolved_review_model else "openai"
        resolved_review_api_key = _resolve_api_key(settings, review_provider, request.api_key)
    else:
        resolved_review_model = None
        resolved_review_api_key = None
    
    # Generate unique thread_id if not provided
    thread_id = request.thread_id or str(uuid.uuid4())
    
    # Build initial state
    state: GenerationState = {
        "request_id": thread_id,
        "resume_text": request.resume_text,
        "job_description": request.job_description,
        "user_instructions": request.user_instructions,
        "review_mode": request.review_mode,
        "run_hallucination_check": request.run_hallucination_check,
    }
    
    # Build runtime config
    runtime = GraphRuntimeConfig(
        model_name=resolved_model,
        api_key=resolved_api_key,
        review_model_name=resolved_review_model,
        review_api_key=resolved_review_api_key,
    )
    
    # Build graph config
    config = {
        "configurable": {
            "thread_id": thread_id,
            "runtime": runtime,
        }
    }
    
    # Get graph and stream
    graph = get_generation_graph(checkpointer=http_request.app.state.checkpointer)
    
    return StreamingResponse(
        stream_generation(state, config, graph),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )



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
            "default": "google:gemini-2.5-pro",
            "default_review_model": "google:gemini-2.5-flash"
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
        "default_review_model": settings.default_review_model,
    }
