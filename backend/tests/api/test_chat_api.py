"""Tests for chat streaming API endpoints."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from unittest.mock import patch

import pytest

from app.api.sse import format_sse


def parse_sse_events(response_text: str) -> list[dict[str, Any]]:
    """Parse an SSE response body into decoded event payloads."""
    events: list[dict[str, Any]] = []
    for chunk in response_text.split("\n\n"):
        if chunk.startswith("data: "):
            events.append(json.loads(chunk[6:]))
    return events


def _chat_message(message_id: str, role: str, content: str) -> dict[str, str]:
    return {
        "id": message_id,
        "role": role,
        "content": content,
        "kind": "text",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


class _FakeGraph:
    def __init__(self, chunks: list[object]):
        self._chunks = chunks

    async def astream(
        self,
        _state: dict[str, Any],
        config: dict[str, Any] | None = None,
        stream_mode: list[str] | None = None,
    ):
        _ = (config, stream_mode)
        for chunk in self._chunks:
            yield chunk


@pytest.mark.asyncio
async def test_intake_stream_endpoint_returns_sse(client):
    """POST /api/chat/intake/stream should return SSE response headers and content."""
    fake_graph = _FakeGraph(
        [
            (
                "updates",
                {
                    "intake": {
                        "ready_to_generate": False,
                        "extracted_constraints": [],
                        "missing_fields": ["Page count"],
                        "assistant_reply": "Do you prefer one page or two pages?",
                    }
                },
            )
        ]
    )

    with patch("app.api.chat.get_intake_graph", return_value=fake_graph):
        response = client.post(
            "/api/chat/intake/stream",
            json={
                "messages": [_chat_message("m1", "user", "Tailor my CV for this role.")],
                "resume_text": "Resume text",
                "job_description": "Job description",
                "api_key": "test-key",
                "model_name": "google:gemini-2.5-flash",
            },
        )

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    assert parse_sse_events(response.text)


@pytest.mark.asyncio
async def test_intake_stream_emits_intake_ready_event(client):
    """Intake stream should emit intake.ready event with readiness payload."""
    fake_graph = _FakeGraph(
        [
            (
                "updates",
                {
                    "intake": {
                        "ready_to_generate": True,
                        "extracted_constraints": ["1-page CV"],
                        "missing_fields": [],
                        "assistant_reply": "Great, I can generate now.",
                    }
                },
            )
        ]
    )

    with patch("app.api.chat.get_intake_graph", return_value=fake_graph):
        response = client.post(
            "/api/chat/intake/stream",
            json={
                "messages": [_chat_message("m1", "user", "One page please.")],
                "resume_text": "Resume text",
                "job_description": "Job description",
                "api_key": "test-key",
                "model_name": "google:gemini-2.5-flash",
            },
        )

    events = parse_sse_events(response.text)
    ready_events = [event for event in events if event.get("type") == "intake.ready"]
    assert len(ready_events) == 1
    assert ready_events[0]["data"]["ready"] is True
    assert ready_events[0]["data"]["constraints"] == ["1-page CV"]


@pytest.mark.asyncio
async def test_generate_stream_endpoint_works(client):
    """POST /api/chat/generate/stream should return SSE response for generation."""

    async def fake_stream_generation(_state, _config, _graph):
        yield format_sse({"type": "run.started", "data": {"thread_id": "t-1"}})
        yield format_sse({"type": "result", "data": {"cv_data": {"name": "Jane Doe"}}})

    with patch("app.api.chat.get_generation_graph", return_value=object()), patch(
        "app.api.chat.stream_generation",
        side_effect=fake_stream_generation,
    ):
        response = client.post(
            "/api/chat/generate/stream",
            json={
                "resume_text": "Resume text",
                "job_description": "Job description",
                "extracted_constraints": [],
                "review_mode": False,
                "api_key": "test-key",
                "model_name": "google:gemini-2.5-flash",
            },
        )

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    assert parse_sse_events(response.text)


@pytest.mark.asyncio
async def test_generate_stream_emits_result_event(client):
    """Generate stream should include result event with cv_data payload."""

    async def fake_stream_generation(_state, _config, _graph):
        yield format_sse(
            {
                "type": "result",
                "data": {
                    "cv_data": {"name": "Jane Doe", "sections": {"Summary": ["Backend engineer"]}},
                    "ats_issues": [],
                    "hallucination_warnings": [],
                },
            }
        )

    with patch("app.api.chat.get_generation_graph", return_value=object()), patch(
        "app.api.chat.stream_generation",
        side_effect=fake_stream_generation,
    ):
        response = client.post(
            "/api/chat/generate/stream",
            json={
                "resume_text": "Resume text",
                "job_description": "Job description",
                "review_mode": False,
                "api_key": "test-key",
                "model_name": "google:gemini-2.5-flash",
            },
        )

    events = parse_sse_events(response.text)
    result_events = [event for event in events if event.get("type") == "result"]
    assert len(result_events) == 1
    assert result_events[0]["data"]["cv_data"]["name"] == "Jane Doe"


@pytest.mark.asyncio
async def test_refine_stream_endpoint_returns_sse(client):
    """POST /api/chat/refine/stream should return SSE response headers and content."""
    fake_graph = _FakeGraph(
        [
            (
                "updates",
                {
                    "refinement": {
                        "updated_cv_dict": {"summary": "Concise summary"},
                        "assistant_reply": "I shortened your summary.",
                    }
                },
            )
        ]
    )

    with patch("app.api.chat.get_refinement_graph", return_value=fake_graph):
        response = client.post(
            "/api/chat/refine/stream",
            json={
                "messages": [_chat_message("m1", "user", "Make summary concise.")],
                "current_cv_dict": {"summary": "Verbose summary"},
                "resume_text": "Resume text",
                "job_description": "Job description",
                "latest_user_message": "Make summary concise.",
                "api_key": "test-key",
                "model_name": "google:gemini-2.5-flash",
            },
        )

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    assert parse_sse_events(response.text)


@pytest.mark.asyncio
async def test_refine_stream_emits_artifact_updated(client):
    """Refinement stream should emit artifact.cv.updated event containing updated CV."""
    updated_cv = {
        "summary": "Backend engineer focused on scalable APIs.",
        "skills": ["Python", "FastAPI"],
    }
    fake_graph = _FakeGraph(
        [
            (
                "updates",
                {
                    "refinement": {
                        "updated_cv_dict": updated_cv,
                        "assistant_reply": "Updated summary while preserving facts.",
                    }
                },
            )
        ]
    )

    with patch("app.api.chat.get_refinement_graph", return_value=fake_graph):
        response = client.post(
            "/api/chat/refine/stream",
            json={
                "messages": [_chat_message("m1", "user", "Polish summary wording.")],
                "current_cv_dict": {"summary": "Backend engineer.", "skills": ["Python", "FastAPI"]},
                "resume_text": "Resume text",
                "job_description": "Job description",
                "latest_user_message": "Polish summary wording.",
                "api_key": "test-key",
                "model_name": "google:gemini-2.5-flash",
            },
        )

    events = parse_sse_events(response.text)
    cv_events = [event for event in events if event.get("type") == "artifact.cv.updated"]
    assert len(cv_events) == 1
    assert cv_events[0]["data"]["cv_data"] == updated_cv
