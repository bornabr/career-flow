"""Tests for intake LangGraph execution behavior."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.graph.registry import get_intake_graph
from app.graph.runtime import GraphRuntimeConfig
from app.schemas.chat import ChatMessage, IntakeTurnResult


SAMPLE_RESUME_TEXT = "Senior backend engineer with Python and FastAPI experience."
SAMPLE_JOB_DESCRIPTION = "Hiring backend engineer to lead API platform reliability work."


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
async def test_intake_graph_asks_questions_when_not_ready():
    """Graph should ask one clarifying question when context is insufficient."""
    mocked_output = IntakeTurnResult(
        assistant_reply="Got it. Should this be one page or two pages?",
        ready_to_generate=False,
        extracted_constraints=[],
        missing_fields=["Page count preference"],
    )

    state = {
        "messages": [_message("m1", "user", "Tailor my CV for this role.")],
        "resume_text": SAMPLE_RESUME_TEXT,
        "job_description": SAMPLE_JOB_DESCRIPTION,
    }

    graph = get_intake_graph()
    with patch("app.agents.intake.create_model_from_string", return_value=object()), patch(
        "app.agents.intake.intake_agent.run",
        new=AsyncMock(return_value=SimpleNamespace(output=mocked_output)),
    ) as mock_run:
        result = await graph.ainvoke(state, config=_config())

    assert result["ready_to_generate"] is False
    assert result["assistant_reply"].count("?") == 1
    assert result["missing_fields"] == ["Page count preference"]
    assert result["extracted_constraints"] == []

    assert mock_run.await_args is not None
    prompt = mock_run.await_args.args[0]
    assert "1. user: Tailor my CV for this role." in prompt


@pytest.mark.asyncio
async def test_intake_graph_marks_ready_when_sufficient_info():
    """Graph should return ready flag and extracted constraints when context is sufficient."""
    mocked_output = IntakeTurnResult(
        assistant_reply="Perfect. I have enough context and will generate now.",
        ready_to_generate=True,
        extracted_constraints=[
            "1-page CV preferred",
            "Emphasize technical leadership",
            "Exclude internships",
        ],
        missing_fields=[],
    )

    state = {
        "messages": [
            _message("m1", "assistant", "Do you prefer one or two pages?"),
            _message(
                "m2",
                "user",
                "One page, emphasize leadership, and remove internships.",
            ),
        ],
        "resume_text": SAMPLE_RESUME_TEXT,
        "job_description": SAMPLE_JOB_DESCRIPTION,
    }

    graph = get_intake_graph()
    with patch("app.agents.intake.create_model_from_string", return_value=object()), patch(
        "app.agents.intake.intake_agent.run",
        new=AsyncMock(return_value=SimpleNamespace(output=mocked_output)),
    ):
        result = await graph.ainvoke(state, config=_config())

    assert result["ready_to_generate"] is True
    assert result["missing_fields"] == []
    assert "1-page CV preferred" in result["extracted_constraints"]
    assert "Emphasize technical leadership" in result["extracted_constraints"]


@pytest.mark.asyncio
async def test_intake_graph_preserves_conversation_history():
    """Graph should persist prior thread messages and pass full history on later turns."""
    first_turn_output = IntakeTurnResult(
        assistant_reply="Do you want one page or two pages?",
        ready_to_generate=False,
        extracted_constraints=[],
        missing_fields=["Page count preference"],
    )
    second_turn_output = IntakeTurnResult(
        assistant_reply="Great, I can generate your tailored CV now.",
        ready_to_generate=True,
        extracted_constraints=["1-page CV preferred"],
        missing_fields=[],
    )

    thread_config = {
        "configurable": {
            "thread_id": str(uuid.uuid4()),
            "runtime": GraphRuntimeConfig(
                model_name="google:gemini-2.5-flash",
                api_key="test-key",
            ),
        }
    }

    graph = get_intake_graph()
    mock_run = AsyncMock(
        side_effect=[
            SimpleNamespace(output=first_turn_output),
            SimpleNamespace(output=second_turn_output),
        ]
    )

    with patch("app.agents.intake.create_model_from_string", return_value=object()), patch(
        "app.agents.intake.intake_agent.run",
        new=mock_run,
    ):
        await graph.ainvoke(
            {
                "messages": [_message("m1", "user", "Help tailor my CV.")],
                "resume_text": SAMPLE_RESUME_TEXT,
                "job_description": SAMPLE_JOB_DESCRIPTION,
            },
            config=thread_config,
        )
        result = await graph.ainvoke(
            {
                "messages": [_message("m2", "user", "One page, leadership-focused.")],
                "resume_text": SAMPLE_RESUME_TEXT,
                "job_description": SAMPLE_JOB_DESCRIPTION,
            },
            config=thread_config,
        )

    assert result["ready_to_generate"] is True
    assert result["messages"][0].content == "Help tailor my CV."
    assert result["messages"][1].content == "One page, leadership-focused."

    second_prompt = mock_run.await_args_list[1].args[0]
    assert "1. user: Help tailor my CV." in second_prompt
    assert "2. user: One page, leadership-focused." in second_prompt
