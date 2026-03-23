from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from langgraph.types import Command
from pydantic import BaseModel, Field

from app.api.sse import format_sse, stream_generation
from app.config import get_settings
from app.graph.registry import get_generation_graph, get_intake_graph, get_refinement_graph
from app.graph.runtime import GraphRuntimeConfig
from app.graph.state import GenerationState
from app.schemas.chat import ChatMessage
from app.services.session_store import SessionStore

logger = logging.getLogger(__name__)


def _get_session_store(request: Request) -> SessionStore:
    return request.app.state.session_store

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


async def _tracked_stream_generation(
    session_store: SessionStore,
    thread_id: str,
    state: Any,
    config: dict[str, Any],
    graph: Any,
) -> Any:
    """Wrap stream_generation to track session status (completed/interrupted/failed)."""
    status = "completed"
    try:
        async for frame in stream_generation(state, config, graph):
            # Detect interrupt events in the SSE frames
            if '"type": "interrupt.pending"' in frame or '"interrupt.pending"' in frame:
                status = "interrupted"
            if '"type": "result"' in frame:
                session_store.update_session(thread_id, has_cv=True)
            yield frame
    except Exception as exc:
        status = "failed"
        logger.exception("Tracked stream error for %s", thread_id)
        yield format_sse({"type": "error", "data": {"message": str(exc)}})
    finally:
        session_store.update_session(thread_id, status=status)


@router.post("/intake/stream")
async def stream_intake(request: IntakeStreamRequest, http_request: Request):
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

    thread_id = str(uuid.uuid4())
    graph = get_intake_graph(checkpointer=http_request.app.state.checkpointer)
    config = {
        "configurable": {
            "thread_id": thread_id,
            "runtime": runtime,
        }
    }

    session_store = _get_session_store(http_request)
    session_store.create_session(
        thread_id=thread_id,
        title="Intake conversation",
        mode="intake",
        status="running",
        model_name=model_name,
        requires_api_key_on_resume=not bool(request.api_key),
    )

    # Store user messages
    for msg in request.messages:
        session_store.add_message(
            thread_id=thread_id,
            message_id=msg.id,
            role=msg.role,
            content=msg.content,
            kind=msg.kind,
        )

    async def event_stream():
        status = "completed"
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
                            reply = node_output["assistant_reply"]
                            session_store.add_message(
                                thread_id=thread_id,
                                message_id=str(uuid.uuid4()),
                                role="assistant",
                                content=reply,
                                kind="text",
                            )
                            session_store.update_session(
                                thread_id, latest_assistant_message=reply
                            )
                            yield format_sse(
                                {
                                    "type": "chat.message.completed",
                                    "data": {"content": reply},
                                }
                            )

        except Exception as exc:
            status = "failed"
            logger.exception("Intake stream error")
            yield format_sse({"type": "error", "data": {"message": str(exc)}})
        finally:
            session_store.update_session(thread_id, status=status)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/generate/stream")
async def stream_generate(request: GenerateStreamRequest, http_request: Request):
    settings = get_settings()

    model_name = request.model_name or settings.model_name
    provider = model_name.split(":")[0] if ":" in model_name else "openai"
    api_key = _resolve_api_key(settings, provider, request.api_key)

    runtime = GraphRuntimeConfig(
        model_name=model_name,
        api_key=api_key,
    )

    review_model: str | None = None
    if request.review_mode:
        review_model = request.review_model or settings.default_review_model
        review_provider = review_model.split(":")[0] if ":" in review_model else "openai"
        review_api_key = _resolve_api_key(settings, review_provider, request.api_key)
        runtime.review_model_name = review_model
        runtime.review_api_key = review_api_key

    thread_id = str(uuid.uuid4())
    state: GenerationState = {
        "request_id": thread_id,
        "resume_text": request.resume_text,
        "job_description": request.job_description,
        "user_instructions": request.user_instructions,
        "review_mode": request.review_mode,
        "run_hallucination_check": request.review_mode,
    }

    graph = get_generation_graph(checkpointer=http_request.app.state.checkpointer)
    config = {
        "configurable": {
            "thread_id": thread_id,
            "runtime": runtime,
        }
    }

    session_store = _get_session_store(http_request)
    mode = "review" if request.review_mode else "standard"
    session_store.create_session(
        thread_id=thread_id,
        title="CV Generation",
        mode=mode,
        status="running",
        model_name=model_name,
        review_model=review_model,
        requires_api_key_on_resume=not bool(request.api_key),
    )

    return StreamingResponse(
        _tracked_stream_generation(session_store, thread_id, state, config, graph),
        media_type="text/event-stream",
    )


@router.post("/refine/stream")
async def stream_refine(request: RefineStreamRequest, http_request: Request):
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

    thread_id = str(uuid.uuid4())
    graph = get_refinement_graph(checkpointer=http_request.app.state.checkpointer)
    config = {
        "configurable": {
            "thread_id": thread_id,
            "runtime": runtime,
        }
    }

    session_store = _get_session_store(http_request)
    session_store.create_session(
        thread_id=thread_id,
        title="CV Refinement",
        mode="refinement",
        status="running",
        model_name=model_name,
        requires_api_key_on_resume=not bool(request.api_key),
    )
    session_store.add_message(
        thread_id=thread_id,
        message_id=str(uuid.uuid4()),
        role="user",
        content=request.latest_user_message,
        kind="text",
    )

    async def event_stream():
        status = "completed"
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
                            session_store.update_session(thread_id, has_cv=True)
                            yield format_sse(
                                {
                                    "type": "artifact.cv.updated",
                                    "data": {"cv_data": node_output["updated_cv_dict"]},
                                }
                            )

                        if "assistant_reply" in node_output:
                            reply = node_output["assistant_reply"]
                            session_store.add_message(
                                thread_id=thread_id,
                                message_id=str(uuid.uuid4()),
                                role="assistant",
                                content=reply,
                                kind="text",
                            )
                            session_store.update_session(
                                thread_id, latest_assistant_message=reply
                            )
                            yield format_sse(
                                {
                                    "type": "chat.message.completed",
                                    "data": {"content": reply},
                                }
                            )

        except Exception as exc:
            status = "failed"
            logger.exception("Refinement stream error")
            yield format_sse({"type": "error", "data": {"message": str(exc)}})
        finally:
            session_store.update_session(thread_id, status=status)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/review/resume/stream")
async def stream_review_resume(request: ReviewResumeRequest, http_request: Request):
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

    graph = get_generation_graph(checkpointer=http_request.app.state.checkpointer)
    config = {
        "configurable": {
            "thread_id": request.thread_id,
            "runtime": runtime,
        }
    }

    # Use Command to resume from interrupt
    resume_command = Command(resume={"review_decisions": decisions_dict})

    session_store = _get_session_store(http_request)
    session_store.update_session(request.thread_id, status="running")

    return StreamingResponse(
        _tracked_stream_generation(session_store, request.thread_id, resume_command, config, graph),
        media_type="text/event-stream",
    )
