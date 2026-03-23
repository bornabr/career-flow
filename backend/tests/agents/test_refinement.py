from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.agents.refinement import run_refinement_turn
from app.schemas.chat import RefinementResult


SAMPLE_RESUME_TEXT = (
    "Senior backend engineer with FastAPI, Python, and distributed systems experience. "
    "Led API modernization and reduced latency by 35%."
)
SAMPLE_JOB_DESCRIPTION = "Seeking backend engineer with Python, cloud systems, and stakeholder communication."


@pytest.mark.asyncio
async def test_run_refinement_turn_applies_requested_cv_change():
    current_cv_dict = {
        "summary": "Senior backend engineer with 10+ years of experience delivering distributed APIs.",
        "experience": [
            {
                "company": "Acme Corp",
                "title": "Senior Backend Engineer",
                "bullets": ["Reduced API latency by 35% through service decomposition."],
            }
        ],
    }

    mocked_output = RefinementResult(
        assistant_reply="I made the summary more concise while preserving your core experience.",
        updated_cv_dict={
            "summary": "Senior backend engineer focused on scalable APIs and distributed systems.",
            "experience": current_cv_dict["experience"],
        },
    )

    fake_model = object()
    with patch("app.agents.refinement.create_model_from_string", return_value=fake_model), patch(
        "app.agents.refinement.refinement_agent.run",
        new=AsyncMock(return_value=SimpleNamespace(output=mocked_output)),
    ) as mock_run:
        result = await run_refinement_turn(
            current_cv_dict=current_cv_dict,
            resume_text=SAMPLE_RESUME_TEXT,
            job_description=SAMPLE_JOB_DESCRIPTION,
            user_message="Make the summary more concise.",
            model_name="google:gemini-2.5-flash",
            api_key="test-key",
        )

    assert result.updated_cv_dict["summary"] != current_cv_dict["summary"]
    assert result.updated_cv_dict["experience"] == current_cv_dict["experience"]
    assert mock_run.await_args is not None


@pytest.mark.asyncio
async def test_run_refinement_turn_returns_explanatory_assistant_reply():
    current_cv_dict = {
        "summary": "Backend engineer.",
        "skills": ["Python", "FastAPI", "System Design"],
    }

    mocked_output = RefinementResult(
        assistant_reply="I kept your factual claims unchanged and tightened wording in the summary.",
        updated_cv_dict={
            "summary": "Backend engineer focused on Python API platforms.",
            "skills": ["Python", "FastAPI", "System Design"],
        },
    )

    fake_model = object()
    with patch("app.agents.refinement.create_model_from_string", return_value=fake_model), patch(
        "app.agents.refinement.refinement_agent.run",
        new=AsyncMock(return_value=SimpleNamespace(output=mocked_output)),
    ):
        result = await run_refinement_turn(
            current_cv_dict=current_cv_dict,
            resume_text=SAMPLE_RESUME_TEXT,
            job_description=SAMPLE_JOB_DESCRIPTION,
            user_message="Polish the summary wording.",
            model_name="google:gemini-2.5-flash",
            api_key="test-key",
        )

    assert "tightened wording" in result.assistant_reply
    assert "factual claims unchanged" in result.assistant_reply


@pytest.mark.asyncio
async def test_run_refinement_turn_reinforces_anti_hallucination_behavior():
    current_cv_dict = {
        "summary": "Senior backend engineer with Python and FastAPI.",
        "skills": ["Python", "FastAPI"],
    }

    mocked_output = RefinementResult(
        assistant_reply="I could not add Kubernetes because it is not supported by your resume text.",
        updated_cv_dict={
            "summary": "Senior backend engineer with Python and FastAPI.",
            "skills": ["Python", "FastAPI"],
        },
    )

    fake_model = object()
    with patch("app.agents.refinement.create_model_from_string", return_value=fake_model), patch(
        "app.agents.refinement.refinement_agent.run",
        new=AsyncMock(return_value=SimpleNamespace(output=mocked_output)),
    ) as mock_run:
        result = await run_refinement_turn(
            current_cv_dict=current_cv_dict,
            resume_text=SAMPLE_RESUME_TEXT,
            job_description=SAMPLE_JOB_DESCRIPTION,
            user_message="Add Kubernetes expertise to my summary.",
            model_name="google:gemini-2.5-flash",
            api_key="test-key",
        )

    assert "Kubernetes" not in " ".join(result.updated_cv_dict.get("skills", []))
    assert result.updated_cv_dict == current_cv_dict

    assert mock_run.await_args is not None
    prompt_arg = mock_run.await_args.args[0]
    assert "Only use information from the original resume text. Do not add unsupported facts." in prompt_arg
    assert "Add Kubernetes expertise to my summary." in prompt_arg
