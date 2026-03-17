"""Tests for graph node event emission.

Tests that nodes correctly emit events using the stream writer:
- Event helpers emit proper structure (type, timestamp, data)
- Nodes call get_stream_writer() and emit appropriate events
- Step lifecycle events (started/completed)
- Review success and failure paths
- Validation events with ATS/hallucination data

All LLM and business logic are mocked to isolate event emission.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock, call
import json
from datetime import datetime, UTC

from app.graph.events import (
    emit_step_started,
    emit_step_completed,
    emit_review_memo,
    emit_review_failed,
    emit_validation_completed,
    emit_result,
    emit_error,
    emit_run_started,
    emit_run_completed,
)
from app.graph.nodes_generation import (
    tailor_node,
    hr_review_node,
    technical_review_node,
    ats_review_node,
    validate_node,
    hallucination_check_node,
    synthesis_node,
)
from app.graph.runtime import GraphRuntimeConfig
from app.schemas.cv import CV
from app.schemas.review import ReviewMemo
from tests.fixtures.mock_data import SAMPLE_RESUME, SAMPLE_JOB_DESCRIPTION


# ============================================================================
# Fixtures for mocked stream writers and state
# ============================================================================


@pytest.fixture
def mock_writer():
    """Mock stream writer that captures emitted events."""
    events = []
    
    def writer_func(event: dict):
        events.append(event)
    
    writer_func.events = events
    return writer_func


@pytest.fixture
def mock_config():
    """Mock graph config with runtime settings."""
    return {
        "configurable": {
            "runtime": GraphRuntimeConfig(
                model_name="google:gemini-2.5-pro",
                api_key="test-key",
            )
        }
    }


@pytest.fixture
def sample_cv():
    """Create a sample CV for testing."""
    return CV.model_validate({
        "name": "John Doe",
        "location": "San Francisco, CA",
        "email": "john.doe@example.com",
        "phone": "+15551234567",
        "website": None,
        "social_networks": None,
        "sections": {
            "Summary": ["Senior Software Engineer"],
            "Skills": [
                {"label": "Languages", "details": "Python, JavaScript"},
            ],
            "Experience": [
                {
                    "company": "TechCorp",
                    "position": "Senior Engineer",
                    "location": "San Francisco",
                    "start_date": "2020-01",
                    "end_date": "present",
                    "highlights": ["Led microservices"],
                    "summary": "Led systems team.",
                }
            ],
            "Education": [
                {
                    "institution": "State University",
                    "area": "Computer Science",
                    "degree": "BS",
                    "location": "State",
                    "start_date": "2014-09",
                    "end_date": "2018-05",
                    "highlights": ["GPA: 3.8"],
                }
            ],
        }
    })


@pytest.fixture
def sample_review_memo():
    """Create a sample ReviewMemo."""
    return ReviewMemo(
        reviewer_role="hr",
        overall_score=8,
        strengths=["Strong progression"],
        weaknesses=["Limited diversity"],
        items=[],
        priority_changes=["Emphasize collaboration"],
    )


# ============================================================================
# Test: Event Helper Functions (emit_* functions)
# ============================================================================


def test_emit_step_started_structure(mock_writer):
    """Test emit_step_started creates correct event structure."""
    emit_step_started(mock_writer, "generation")
    
    assert len(mock_writer.events) == 1
    event = mock_writer.events[0]
    
    # Verify structure
    assert event["type"] == "step.started"
    assert "timestamp" in event
    assert isinstance(event["timestamp"], str)
    assert event["data"]["step_name"] == "generation"


def test_emit_step_completed_structure(mock_writer):
    """Test emit_step_completed creates correct event structure."""
    emit_step_completed(mock_writer, "generation")
    
    assert len(mock_writer.events) == 1
    event = mock_writer.events[0]
    
    assert event["type"] == "step.completed"
    assert "timestamp" in event
    assert event["data"]["step_name"] == "generation"


def test_emit_review_memo_structure(mock_writer, sample_review_memo):
    """Test emit_review_memo creates correct event structure."""
    memo_dict = sample_review_memo.model_dump()
    emit_review_memo(mock_writer, "hr", memo_dict)
    
    assert len(mock_writer.events) == 1
    event = mock_writer.events[0]
    
    assert event["type"] == "review.memo"
    assert "timestamp" in event
    assert event["data"]["reviewer_role"] == "hr"
    assert "memo" in event["data"]
    assert event["data"]["memo"]["overall_score"] == 8


def test_emit_review_failed_structure(mock_writer):
    """Test emit_review_failed creates correct event structure."""
    emit_review_failed(mock_writer, "technical", "API timeout")
    
    assert len(mock_writer.events) == 1
    event = mock_writer.events[0]
    
    assert event["type"] == "review.failed"
    assert "timestamp" in event
    assert event["data"]["reviewer_role"] == "technical"
    assert event["data"]["error"] == "API timeout"


def test_emit_validation_completed_structure(mock_writer):
    """Test emit_validation_completed creates correct event structure."""
    ats_issues = [{"issue": "Missing keyword"}]
    hallucination_warnings = [{"warning": "Embellished claim"}]
    
    emit_validation_completed(mock_writer, ats_issues, hallucination_warnings)
    
    assert len(mock_writer.events) == 1
    event = mock_writer.events[0]
    
    assert event["type"] == "validation.completed"
    assert "timestamp" in event
    assert event["data"]["ats_issues"] == ats_issues
    assert event["data"]["hallucination_warnings"] == hallucination_warnings


def test_emit_result_structure(mock_writer):
    """Test emit_result creates correct event structure."""
    response = {
        "cv_data": {"name": "John"},
        "ats_issues": [],
        "hallucination_warnings": [],
    }
    
    emit_result(mock_writer, response)
    
    assert len(mock_writer.events) == 1
    event = mock_writer.events[0]
    
    assert event["type"] == "result"
    assert "timestamp" in event
    assert event["data"] == response


def test_emit_error_structure(mock_writer):
    """Test emit_error creates correct event structure."""
    emit_error(mock_writer, "Unexpected error occurred")
    
    assert len(mock_writer.events) == 1
    event = mock_writer.events[0]
    
    assert event["type"] == "error"
    assert "timestamp" in event
    assert event["data"]["message"] == "Unexpected error occurred"


def test_emit_run_started_structure(mock_writer):
    """Test emit_run_started creates correct event structure."""
    emit_run_started(mock_writer, "thread-123", False)
    
    assert len(mock_writer.events) == 1
    event = mock_writer.events[0]
    
    assert event["type"] == "run.started"
    assert "timestamp" in event
    assert event["data"]["thread_id"] == "thread-123"
    assert event["data"]["review_mode"] is False


def test_emit_run_completed_structure(mock_writer):
    """Test emit_run_completed creates correct event structure."""
    emit_run_completed(mock_writer, "thread-123", "success")
    
    assert len(mock_writer.events) == 1
    event = mock_writer.events[0]
    
    assert event["type"] == "run.completed"
    assert "timestamp" in event
    assert event["data"]["thread_id"] == "thread-123"
    assert event["data"]["status"] == "success"


def test_event_timestamps_are_iso_format(mock_writer):
    """Test that all event timestamps are ISO 8601 format."""
    emit_step_started(mock_writer, "test")
    
    event = mock_writer.events[0]
    timestamp = event["timestamp"]
    
    # Should be parseable as ISO 8601
    dt = datetime.fromisoformat(timestamp)
    assert dt is not None


# ============================================================================
# Test: Node Event Emission (actual node functions)
# ============================================================================


@pytest.mark.asyncio
async def test_tailor_node_emits_step_events(
    mock_config, sample_cv, mock_writer
):
    """Test tailor_node emits step.started and step.completed events."""
    with patch("app.graph.nodes_generation.get_stream_writer", return_value=mock_writer), \
         patch("app.graph.nodes_generation.tailor_cv", new_callable=AsyncMock) as mock_tailor:
        
        mock_tailor.return_value = sample_cv
        
        state = {
            "resume_text": SAMPLE_RESUME,
            "job_description": SAMPLE_JOB_DESCRIPTION,
            "user_instructions": None,
        }
        
        result = await tailor_node(state, mock_config)
        
        # Verify events
        assert len(mock_writer.events) == 2
        
        # First event: step.started
        assert mock_writer.events[0]["type"] == "step.started"
        assert mock_writer.events[0]["data"]["step_name"] == "generation"
        
        # Second event: step.completed
        assert mock_writer.events[1]["type"] == "step.completed"
        assert mock_writer.events[1]["data"]["step_name"] == "generation"
        
        # Verify result
        assert "draft_cv" in result
        assert result["draft_cv"].name == "John Doe"


@pytest.mark.asyncio
async def test_hr_review_node_success_emits_memo(
    mock_config, sample_review_memo, mock_writer
):
    """Test hr_review_node emits review.memo on success."""
    with patch("app.graph.nodes_generation.get_stream_writer", return_value=mock_writer), \
         patch("app.graph.nodes_generation.review_as_hr", new_callable=AsyncMock) as mock_review:
        
        mock_review.return_value = sample_review_memo
        
        state = {
            "current_cv_dict": {"name": "John"},
            "job_description": SAMPLE_JOB_DESCRIPTION,
        }
        
        result = await hr_review_node(state, mock_config)
        
        # Verify events: step.started → review.memo → step.completed
        assert len(mock_writer.events) == 3
        
        assert mock_writer.events[0]["type"] == "step.started"
        assert mock_writer.events[0]["data"]["step_name"] == "hr_review"
        
        assert mock_writer.events[1]["type"] == "review.memo"
        assert mock_writer.events[1]["data"]["reviewer_role"] == "hr"
        
        assert mock_writer.events[2]["type"] == "step.completed"
        assert mock_writer.events[2]["data"]["step_name"] == "hr_review"
        
        # Verify result includes review
        assert "reviews" in result
        assert len(result["reviews"]) == 1


@pytest.mark.asyncio
async def test_hr_review_node_failure_emits_failed_no_completed(
    mock_config, mock_writer
):
    """Test hr_review_node emits review.failed (NOT step.completed) on failure."""
    with patch("app.graph.nodes_generation.get_stream_writer", return_value=mock_writer), \
         patch("app.graph.nodes_generation.review_as_hr", new_callable=AsyncMock) as mock_review:
        
        mock_review.side_effect = Exception("API error")
        
        state = {
            "current_cv_dict": {"name": "John"},
            "job_description": SAMPLE_JOB_DESCRIPTION,
        }
        
        result = await hr_review_node(state, mock_config)
        
        # Verify events: step.started → review.failed (NO step.completed)
        assert len(mock_writer.events) == 2
        
        assert mock_writer.events[0]["type"] == "step.started"
        
        assert mock_writer.events[1]["type"] == "review.failed"
        assert mock_writer.events[1]["data"]["reviewer_role"] == "hr"
        assert "error" in mock_writer.events[1]["data"]
        
        # Verify no step.completed
        completed_events = [e for e in mock_writer.events if e["type"] == "step.completed"]
        assert len(completed_events) == 0
        
        # Verify result includes error
        assert "review_errors" in result
        assert len(result["review_errors"]) == 1


@pytest.mark.asyncio
async def test_technical_review_node_success_emits_memo(
    mock_config, sample_review_memo, mock_writer
):
    """Test technical_review_node emits review.memo on success."""
    sample_review_memo.reviewer_role = "technical"
    
    with patch("app.graph.nodes_generation.get_stream_writer", return_value=mock_writer), \
         patch("app.graph.nodes_generation.review_as_technical", new_callable=AsyncMock) as mock_review:
        
        mock_review.return_value = sample_review_memo
        
        state = {
            "current_cv_dict": {"name": "John"},
            "job_description": SAMPLE_JOB_DESCRIPTION,
        }
        
        result = await technical_review_node(state, mock_config)
        
        # Verify events
        assert len(mock_writer.events) == 3
        assert mock_writer.events[0]["type"] == "step.started"
        assert mock_writer.events[1]["type"] == "review.memo"
        assert mock_writer.events[1]["data"]["reviewer_role"] == "technical"
        assert mock_writer.events[2]["type"] == "step.completed"


@pytest.mark.asyncio
async def test_ats_review_node_success_emits_memo(
    mock_config, sample_review_memo, mock_writer
):
    """Test ats_review_node emits review.memo on success."""
    sample_review_memo.reviewer_role = "ats"
    
    with patch("app.graph.nodes_generation.get_stream_writer", return_value=mock_writer), \
         patch("app.graph.nodes_generation.review_as_ats", new_callable=AsyncMock) as mock_review:
        
        mock_review.return_value = sample_review_memo
        
        state = {
            "current_cv_dict": {"name": "John"},
            "job_description": SAMPLE_JOB_DESCRIPTION,
        }
        
        result = await ats_review_node(state, mock_config)
        
        # Verify events
        assert len(mock_writer.events) == 3
        assert mock_writer.events[0]["type"] == "step.started"
        assert mock_writer.events[1]["type"] == "review.memo"
        assert mock_writer.events[1]["data"]["reviewer_role"] == "ats"
        assert mock_writer.events[2]["type"] == "step.completed"


@pytest.mark.asyncio
async def test_validate_node_emits_validation_completed(
    mock_config, mock_writer
):
    """Test validate_node emits validation.completed event."""
    with patch("app.graph.nodes_generation.get_stream_writer", return_value=mock_writer), \
         patch("app.graph.nodes_generation.validate_cv") as mock_validate:
        
        mock_validate.return_value = {
            "cv_data": {"name": "John"},
            "ats_issues": ["Missing keyword"],
            "hallucination_warnings": ["Embellished"],
        }
        
        state = {
            "resume_text": SAMPLE_RESUME,
            "current_cv_dict": {"name": "John"},
        }
        
        result = await validate_node(state, mock_config)
        
        # Verify events: step.started → validation.completed → step.completed
        assert len(mock_writer.events) == 3
        
        assert mock_writer.events[0]["type"] == "step.started"
        assert mock_writer.events[0]["data"]["step_name"] == "validation"
        
        assert mock_writer.events[1]["type"] == "validation.completed"
        assert mock_writer.events[1]["data"]["ats_issues"] == ["Missing keyword"]
        assert mock_writer.events[1]["data"]["hallucination_warnings"] == ["Embellished"]
        
        assert mock_writer.events[2]["type"] == "step.completed"
        assert mock_writer.events[2]["data"]["step_name"] == "validation"


@pytest.mark.asyncio
async def test_hallucination_check_node_emits_step_events(
    mock_config, mock_writer
):
    """Test hallucination_check_node emits step lifecycle events."""
    with patch("app.graph.nodes_generation.get_stream_writer", return_value=mock_writer), \
         patch("app.graph.nodes_generation.check_hallucinations_ai", new_callable=AsyncMock) as mock_check:
        
        from app.schemas.review import HallucinationReport
        
        mock_check.return_value = HallucinationReport(
            has_hallucinations=False,
            items=[],
            summary="No issues"
        )
        
        state = {
            "resume_text": SAMPLE_RESUME,
            "current_cv_dict": {"name": "John"},
        }
        
        result = await hallucination_check_node(state, mock_config)
        
        # Verify events
        assert len(mock_writer.events) == 2
        
        assert mock_writer.events[0]["type"] == "step.started"
        assert mock_writer.events[0]["data"]["step_name"] == "hallucination_check"
        
        assert mock_writer.events[1]["type"] == "step.completed"
        assert mock_writer.events[1]["data"]["step_name"] == "hallucination_check"


@pytest.mark.asyncio
async def test_synthesis_node_emits_step_events(
    mock_config, sample_cv, mock_writer, sample_review_memo
):
    """Test synthesis_node emits step lifecycle events."""
    with patch("app.graph.nodes_generation.get_stream_writer", return_value=mock_writer), \
         patch("app.graph.nodes_generation.synthesize_cv", new_callable=AsyncMock) as mock_synth:
        
        mock_synth.return_value = sample_cv
        
        state = {
            "resume_text": SAMPLE_RESUME,
            "job_description": SAMPLE_JOB_DESCRIPTION,
            "current_cv_dict": {"name": "John"},
            "reviews": [sample_review_memo],
        }
        
        result = await synthesis_node(state, mock_config)
        
        # Verify events
        assert len(mock_writer.events) == 2
        
        assert mock_writer.events[0]["type"] == "step.started"
        assert mock_writer.events[0]["data"]["step_name"] == "synthesis"
        
        assert mock_writer.events[1]["type"] == "step.completed"
        assert mock_writer.events[1]["data"]["step_name"] == "synthesis"


# ============================================================================
# Test: Multiple Reviewer Paths
# ============================================================================


@pytest.mark.asyncio
async def test_parallel_reviewers_emit_independent_events(
    mock_config, sample_review_memo
):
    """Test that multiple reviewer nodes emit independent events."""
    hr_writer = []
    tech_writer = []
    
    def hr_writer_func(event):
        hr_writer.append(event)
    
    def tech_writer_func(event):
        tech_writer.append(event)
    
    hr_writer_func.events = hr_writer
    tech_writer_func.events = tech_writer
    
    with patch("app.graph.nodes_generation.get_stream_writer") as mock_get_writer:
        # Simulate get_stream_writer being called separately for each reviewer
        mock_get_writer.side_effect = [hr_writer_func, tech_writer_func]
        
        with patch("app.graph.nodes_generation.review_as_hr", new_callable=AsyncMock) as mock_hr, \
             patch("app.graph.nodes_generation.review_as_technical", new_callable=AsyncMock) as mock_tech:
            
            mock_hr.return_value = sample_review_memo
            sample_review_memo.reviewer_role = "technical"
            mock_tech.return_value = sample_review_memo
            
            state = {
                "current_cv_dict": {"name": "John"},
                "job_description": SAMPLE_JOB_DESCRIPTION,
            }
            
            # Call both reviewers
            await hr_review_node(state, mock_config)
            await technical_review_node(state, mock_config)
            
            # Verify both emitted events
            assert len(hr_writer) == 3
            assert len(tech_writer) == 3
            
            # Verify correct reviewer roles
            assert hr_writer[1]["data"]["reviewer_role"] == "hr"
            assert tech_writer[1]["data"]["reviewer_role"] == "technical"
