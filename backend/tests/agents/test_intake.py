from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.agents.intake import run_intake_turn
from app.schemas.chat import IntakeTurnResult


SAMPLE_RESUME_TEXT = "Senior backend engineer with Python, FastAPI, and distributed systems experience."
SAMPLE_JOB_DESCRIPTION = "Looking for senior backend engineer with leadership and API platform ownership."


@pytest.mark.asyncio
async def test_run_intake_turn_questions_when_info_missing():
    conversation_history = [
        {"role": "user", "content": "Please tailor my CV for this role."},
    ]

    mocked_output = IntakeTurnResult(
        assistant_reply="Got it. Do you prefer a one-page or two-page CV?",
        ready_to_generate=False,
        extracted_constraints=[],
        missing_fields=["Page count preference", "Key skills to highlight"],
    )

    fake_model = object()
    with patch("app.agents.intake.create_model_from_string", return_value=fake_model), patch(
        "app.agents.intake.intake_agent.run",
        new=AsyncMock(return_value=SimpleNamespace(output=mocked_output)),
    ) as mock_run:
        result = await run_intake_turn(
            conversation_history=conversation_history,
            resume_text=SAMPLE_RESUME_TEXT,
            job_description=SAMPLE_JOB_DESCRIPTION,
            user_instructions=None,
            model_name="google:gemini-2.5-flash",
            api_key="test-key",
        )

    assert result.ready_to_generate is False
    assert result.missing_fields == ["Page count preference", "Key skills to highlight"]
    assert result.assistant_reply.count("?") == 1

    assert mock_run.await_args is not None
    prompt_arg = mock_run.await_args.args[0]
    assert "Ask exactly one clarifying question" in prompt_arg
    assert "Do not ask multiple questions" in prompt_arg
    assert "1. user: Please tailor my CV for this role." in prompt_arg


@pytest.mark.asyncio
async def test_run_intake_turn_marks_ready_and_extracts_constraints():
    conversation_history = [
        {"role": "assistant", "content": "Do you prefer a one-page or two-page CV?"},
        {"role": "user", "content": "One page please, emphasize technical leadership, and exclude internships."},
    ]

    mocked_output = IntakeTurnResult(
        assistant_reply="Perfect — I have enough context and will generate your tailored CV now.",
        ready_to_generate=True,
        extracted_constraints=[
            "1-page CV preferred",
            "Emphasize technical leadership",
            "Exclude internships",
        ],
        missing_fields=[],
    )

    fake_model = object()
    with patch("app.agents.intake.create_model_from_string", return_value=fake_model), patch(
        "app.agents.intake.intake_agent.run",
        new=AsyncMock(return_value=SimpleNamespace(output=mocked_output)),
    ) as mock_run:
        result = await run_intake_turn(
            conversation_history=conversation_history,
            resume_text=SAMPLE_RESUME_TEXT,
            job_description=SAMPLE_JOB_DESCRIPTION,
            user_instructions="Keep a leadership-focused tone.",
            model_name="google:gemini-2.5-flash",
            api_key="test-key",
        )

    assert result.ready_to_generate is True
    assert result.missing_fields == []
    assert "1-page CV preferred" in result.extracted_constraints
    assert "Emphasize technical leadership" in result.extracted_constraints
    assert result.assistant_reply.count("?") == 0

    assert mock_run.await_args is not None
    prompt_arg = mock_run.await_args.args[0]
    assert "Keep a leadership-focused tone." in prompt_arg
    assert "2. user: One page please, emphasize technical leadership, and exclude internships." in prompt_arg
