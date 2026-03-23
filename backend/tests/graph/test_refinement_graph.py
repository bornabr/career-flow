"""Tests for refinement LangGraph execution behavior."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.graph.registry import get_refinement_graph
from app.graph.runtime import GraphRuntimeConfig
from app.schemas.chat import ChatMessage, RefinementResult


SAMPLE_RESUME_TEXT = (
    "Senior backend engineer with FastAPI and distributed systems experience. "
    "Reduced latency by 35% and led API modernization."
)
SAMPLE_JOB_DESCRIPTION = "Seeking backend engineer with Python, cloud systems, and communication skills."


def _message(message_id: str, role: str, content: str) -> ChatMessage:
    return ChatMessage(
        id=message_id,
        role=role,
        content=content,
        kind="text",
        timestamp=datetime.now(timezone.utc),
    )


def _config() -> dict[str, object]:
    return {
        "configurable": {
            "thread_id": str(uuid.uuid4()),
            "runtime": GraphRuntimeConfig(
                model_name="google:gemini-2.5-flash",
                api_key="test-key",
            ),
        }
    }


@pytest.mark.asyncio
async def test_refinement_graph_updates_cv_dict():
    """Graph should return updated_cv_dict with requested changes applied."""
    current_cv_dict = {
        "summary": "Senior backend engineer with 10+ years building distributed APIs.",
        "skills": ["Python", "FastAPI", "System Design"],
    }
    mocked_output = RefinementResult(
        assistant_reply="I tightened your summary wording and preserved all factual claims.",
        updated_cv_dict={
            "summary": "Senior backend engineer focused on scalable API platforms.",
            "skills": ["Python", "FastAPI", "System Design"],
        },
    )

    state = {
        "messages": [_message("m1", "user", "Make the summary more concise.")],
        "current_cv_dict": current_cv_dict,
        "resume_text": SAMPLE_RESUME_TEXT,
        "job_description": SAMPLE_JOB_DESCRIPTION,
        "latest_user_message": "Make the summary more concise.",
    }

    graph = get_refinement_graph()
    with patch("app.agents.refinement.create_model_from_string", return_value=object()), patch(
        "app.agents.refinement.refinement_agent.run",
        new=AsyncMock(return_value=SimpleNamespace(output=mocked_output)),
    ):
        result = await graph.ainvoke(state, config=_config())

    assert result["updated_cv_dict"]["summary"] != current_cv_dict["summary"]
    assert result["updated_cv_dict"]["skills"] == current_cv_dict["skills"]


@pytest.mark.asyncio
async def test_refinement_graph_returns_assistant_explanation():
    """Graph should include a clear assistant explanation of edits performed."""
    mocked_output = RefinementResult(
        assistant_reply="I shortened the summary and kept every original claim unchanged.",
        updated_cv_dict={
            "summary": "Backend engineer focused on Python API reliability.",
            "skills": ["Python", "FastAPI"],
        },
    )

    state = {
        "messages": [
            _message("m1", "assistant", "What would you like adjusted?"),
            _message("m2", "user", "Polish the summary wording."),
        ],
        "current_cv_dict": {
            "summary": "Backend engineer with Python and FastAPI.",
            "skills": ["Python", "FastAPI"],
        },
        "resume_text": SAMPLE_RESUME_TEXT,
        "job_description": SAMPLE_JOB_DESCRIPTION,
        "latest_user_message": "Polish the summary wording.",
    }

    graph = get_refinement_graph()
    with patch("app.agents.refinement.create_model_from_string", return_value=object()), patch(
        "app.agents.refinement.refinement_agent.run",
        new=AsyncMock(return_value=SimpleNamespace(output=mocked_output)),
    ):
        result = await graph.ainvoke(state, config=_config())

    assert "summary" in result["assistant_reply"].lower()
    assert "unchanged" in result["assistant_reply"].lower()
    assert result["assistant_reply"]


@pytest.mark.asyncio
async def test_refinement_graph_preserves_factual_accuracy():
    """Graph should keep CV unchanged when user asks for unsupported new facts."""
    current_cv_dict = {
        "summary": "Senior backend engineer with Python and FastAPI.",
        "skills": ["Python", "FastAPI"],
    }
    mocked_output = RefinementResult(
        assistant_reply="I could not add Kubernetes expertise because it is not in your resume.",
        updated_cv_dict=current_cv_dict,
    )

    state = {
        "messages": [_message("m1", "user", "Add Kubernetes expertise to my summary.")],
        "current_cv_dict": current_cv_dict,
        "resume_text": SAMPLE_RESUME_TEXT,
        "job_description": SAMPLE_JOB_DESCRIPTION,
        "latest_user_message": "Add Kubernetes expertise to my summary.",
    }

    graph = get_refinement_graph()
    with patch("app.agents.refinement.create_model_from_string", return_value=object()), patch(
        "app.agents.refinement.refinement_agent.run",
        new=AsyncMock(return_value=SimpleNamespace(output=mocked_output)),
    ) as mock_run:
        result = await graph.ainvoke(state, config=_config())

    assert result["updated_cv_dict"] == current_cv_dict
    assert "Kubernetes" not in " ".join(result["updated_cv_dict"].get("skills", []))
    assert "could not add kubernetes" in result["assistant_reply"].lower()

    assert mock_run.await_args is not None
    prompt = mock_run.await_args.args[0]
    assert "Only use information from the original resume text. Do not add unsupported facts." in prompt
