from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from langgraph.types import Command
from pydantic import BaseModel, Field

from app.api.sse import format_sse, stream_generation
from app.config import get_settings
from app.graph.registry import get_generation_graph, get_intake_graph, get_refinement_graph
from app.graph.runtime import GraphRuntimeConfig
from app.graph.state import GenerationState
from app.schemas.chat import ChatMessage

logger = logging.getLogger(__name__)

router = APIRouter()


class IntakeStreamRequest(BaseModel):
    messages: list[ChatMessage]
    resume_text: str
    job_description: str
    user_instructions: str | None = None
    api_key: str | None = None
    model_name: str | None = None


class GenerateStreamRequest(BaseModel):
    resume_text: str
    job_description: str
    user_instructions: str | None = None
    extracted_constraints: list[str] = Field(default_factory=list)
    api_key: str | None = None
    model_name: str | None = None
    review_mode: bool = False
    review_model: str | None = None


class RefineStreamRequest(BaseModel):
    messages: list[ChatMessage]
    current_cv_dict: dict[str, Any]
    resume_text: str
    job_description: str
    latest_user_message: str
    api_key: str | None = None
    model_name: str | None = None


class ReviewResumeRequest(BaseModel):
    thread_id: str = Field(..., description="Thread ID from original generation request")
    decisions: list[dict[str, bool]] = Field(..., description="List of {item_key: str, accepted: bool}")
    api_key: str | None = None
    model_name: str | None = None


class StreamEvent(BaseModel):
    type: str
    data: dict[str, Any] = Field(default_factory=dict)


def _resolve_api_key(settings: Any, provider: str, request_api_key: str | None) -> str:
    api_key = request_api_key or settings.resolve_api_key_for_provider(provider)
    if not api_key:
        raise HTTPException(
            status_code=400,
            detail=f"No API key available for provider '{provider}'. "
            f"Set the appropriate API key env var or pass api_key in request body.",
        )
    return api_key


def _extract_stream_mode_payload(chunk: Any) -> tuple[str | None, dict[str, Any]]:
    if isinstance(chunk, tuple) and len(chunk) == 2:
        mode, payload = chunk
        if isinstance(mode, str) and isinstance(payload, dict):
            return mode, payload
        return None, {}

    if isinstance(chunk, dict):
        if "type" in chunk and isinstance(chunk.get("type"), str):
            payload = chunk.get("data", {})
            return chunk["type"], payload if isinstance(payload, dict) else {}
        return "updates", chunk

    return None, {}


@router.post("/intake/stream")
async def stream_intake(request: IntakeStreamRequest):
    settings = get_settings()

    model_name = request.model_name or settings.model_name
    provider = model_name.split(":")[0] if ":" in model_name else "openai"
    api_key = _resolve_api_key(settings, provider, request.api_key)

    runtime = GraphRuntimeConfig(
        model_name=model_name,
        api_key=api_key,
    )

    state = {
        "messages": request.messages,
        "resume_text": request.resume_text,
        "job_description": request.job_description,
        "user_instructions": request.user_instructions,
    }

    graph = get_intake_graph()
    config = {
        "configurable": {
            "thread_id": str(uuid.uuid4()),
            "runtime": runtime,
        }
    }

    async def event_stream():
        try:
            async for chunk in graph.astream(state, config=config, stream_mode=["custom", "updates"]):
                mode, payload = _extract_stream_mode_payload(chunk)

                if mode == "custom":
                    yield format_sse(payload)
                    continue

                if mode == "updates":
                    for _, node_output in payload.items():
                        if not isinstance(node_output, dict):
                            continue

                        if "ready_to_generate" in node_output:
                            yield format_sse(
                                {
                                    "type": "intake.ready",
                                    "data": {
                                        "ready": node_output["ready_to_generate"],
                                        "constraints": node_output.get("extracted_constraints", []),
                                        "missing_fields": node_output.get("missing_fields", []),
                                    },
                                }
                            )

                        if "assistant_reply" in node_output:
                            yield format_sse(
                                {
                                    "type": "chat.message.completed",
                                    "data": {"content": node_output["assistant_reply"]},
                                }
                            )

        except Exception as exc:
            logger.exception("Intake stream error")
            yield format_sse({"type": "error", "data": {"message": str(exc)}})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/generate/stream")
async def stream_generate(request: GenerateStreamRequest):
    settings = get_settings()

    model_name = request.model_name or settings.model_name
    provider = model_name.split(":")[0] if ":" in model_name else "openai"
    api_key = _resolve_api_key(settings, provider, request.api_key)

    runtime = GraphRuntimeConfig(
        model_name=model_name,
        api_key=api_key,
    )

    if request.review_mode:
        review_model = request.review_model or settings.default_review_model
        review_provider = review_model.split(":")[0] if ":" in review_model else "openai"
        review_api_key = _resolve_api_key(settings, review_provider, request.api_key)
        runtime.review_model_name = review_model
        runtime.review_api_key = review_api_key

    state: GenerationState = {
        "request_id": str(uuid.uuid4()),
        "resume_text": request.resume_text,
        "job_description": request.job_description,
        "user_instructions": request.user_instructions,
        "review_mode": request.review_mode,
        "run_hallucination_check": request.review_mode,
    }

    graph = get_generation_graph()
    config = {
        "configurable": {
            "thread_id": str(uuid.uuid4()),
            "runtime": runtime,
        }
    }

    return StreamingResponse(
        stream_generation(state, config, graph),
        media_type="text/event-stream",
    )


@router.post("/refine/stream")
async def stream_refine(request: RefineStreamRequest):
    settings = get_settings()

    model_name = request.model_name or settings.model_name
    provider = model_name.split(":")[0] if ":" in model_name else "openai"
    api_key = _resolve_api_key(settings, provider, request.api_key)

    runtime = GraphRuntimeConfig(
        model_name=model_name,
        api_key=api_key,
    )

    state = {
        "messages": request.messages,
        "current_cv_dict": request.current_cv_dict,
        "resume_text": request.resume_text,
        "job_description": request.job_description,
        "latest_user_message": request.latest_user_message,
    }

    graph = get_refinement_graph()
    config = {
        "configurable": {
            "thread_id": str(uuid.uuid4()),
            "runtime": runtime,
        }
    }

    async def event_stream():
        try:
            async for chunk in graph.astream(state, config=config, stream_mode=["custom", "updates"]):
                mode, payload = _extract_stream_mode_payload(chunk)

                if mode == "custom":
                    yield format_sse(payload)
                    continue

                if mode == "updates":
                    for _, node_output in payload.items():
                        if not isinstance(node_output, dict):
                            continue

                        if "updated_cv_dict" in node_output:
                            yield format_sse(
                                {
                                    "type": "artifact.cv.updated",
                                    "data": {"cv_data": node_output["updated_cv_dict"]},
                                }
                            )

                        if "assistant_reply" in node_output:
                            yield format_sse(
                                {
                                    "type": "chat.message.completed",
                                    "data": {"content": node_output["assistant_reply"]},
                                }
                            )

        except Exception as exc:
            logger.exception("Refinement stream error")
            yield format_sse({"type": "error", "data": {"message": str(exc)}})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/review/resume/stream")
async def stream_review_resume(request: ReviewResumeRequest):
    settings = get_settings()

    model_name = request.model_name or settings.model_name
    provider = model_name.split(":")[0] if ":" in model_name else "openai"
    api_key = _resolve_api_key(settings, provider, request.api_key)

    runtime = GraphRuntimeConfig(
        model_name=model_name,
        api_key=api_key,
    )

    # Convert list of dicts to {item_key: accepted} dict
    decisions_dict = {d["item_key"]: d["accepted"] for d in request.decisions}

    graph = get_generation_graph()
    config = {
        "configurable": {
            "thread_id": request.thread_id,
            "runtime": runtime,
        }
    }

    # Use Command to resume from interrupt
    resume_command = Command(resume={"review_decisions": decisions_dict})

    return StreamingResponse(
        stream_generation(resume_command, config, graph),
        media_type="text/event-stream",
    )
