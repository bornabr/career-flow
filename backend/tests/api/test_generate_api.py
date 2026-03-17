"""Tests for FastAPI /generate endpoint.

Tests the current asyncio.gather orchestration pipeline behavior:
- Standard mode: tailor → validate (no reviewers)
- Review mode: tailor → parallel reviewers → synthesis → validate
- Partial reviewer failures: one fails, others succeed
- Response schema validation: GenerateResponse structure

All LLM agent calls are mocked to ensure deterministic testing without API calls.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from pydantic import ValidationError

from app.schemas.cv import CV
from app.schemas.review import ReviewMemo, HallucinationReport, ReviewPanelResult
from tests.fixtures.mock_data import (
    SAMPLE_RESUME,
    SAMPLE_JOB_DESCRIPTION,
    SAMPLE_CV_OUTPUT,
)


# ============================================================================
# Fixtures for mock objects
# ============================================================================


@pytest.fixture
def mock_cv():
    """Create a valid CV object from sample output."""
    return CV.model_validate({
        "name": "John Doe",
        "location": "San Francisco, CA",
        "email": "john.doe@example.com",
        "phone": "+15551234567",
        "website": None,
        "social_networks": None,
        "sections": {
            "Summary": [
                "Senior Software Engineer with 5+ years of experience",
                "building scalable microservices and AI-powered systems.",
            ],
            "Skills": [
                {"label": "Languages", "details": "Python, JavaScript, TypeScript, Go"},
                {"label": "Frameworks", "details": "FastAPI, React, Next.js"},
                {"label": "Tools", "details": "Docker, Kubernetes, PostgreSQL, Redis"},
            ],
            "Experience": [
                {
                    "company": "TechCorp",
                    "position": "Senior Software Engineer",
                    "location": "San Francisco, CA",
                    "start_date": "2020-01",
                    "end_date": "present",
                    "highlights": [
                        "Led development of microservices architecture serving 10M+ users",
                        "Reduced API latency by 40% through optimization initiatives",
                        "Mentored 5 junior engineers on system design and Python best practices",
                    ],
                    "summary": "Led high-impact backend systems team.",
                }
            ],
            "Education": [
                {
                    "institution": "State University",
                    "area": "Computer Science",
                    "degree": "BS",
                    "location": "State, USA",
                    "start_date": "2014-09",
                    "end_date": "2018-05",
                    "highlights": ["GPA: 3.8/4.0", "Dean's List"],
                }
            ],
        }
    })


@pytest.fixture
def mock_hr_review():
    """Create a valid HR reviewer ReviewMemo."""
    return ReviewMemo(
        reviewer_role="hr",
        overall_score=8,
        strengths=[
            "Strong career progression",
            "Clear achievements with quantified impact",
            "Demonstrates leadership and mentorship",
        ],
        weaknesses=[
            "Could highlight soft skills more explicitly",
            "Limited diversity of companies",
        ],
        items=[
            {
                "category": "career_progression",
                "severity": "suggestion",
                "section": "Experience",
                "finding": "Strong progression from engineer to senior role",
                "recommendation": "Add more context on transition timeline",
            }
        ],
        priority_changes=[
            "Emphasize cross-team collaboration in summary",
            "Add team size information for each role",
            "Include any certifications or awards",
        ]
    )


@pytest.fixture
def mock_technical_review():
    """Create a valid Technical reviewer ReviewMemo."""
    return ReviewMemo(
        reviewer_role="technical",
        overall_score=9,
        strengths=[
            "Deep expertise in required tech stack",
            "Proven track record with microservices",
            "Strong async/concurrency experience",
        ],
        weaknesses=["Could add more detail on architecture decisions"],
        items=[
            {
                "category": "tech_depth",
                "severity": "suggestion",
                "section": "Experience",
                "finding": "Strong microservices experience matches JD requirements",
                "recommendation": "Add specific architectural patterns used",
            }
        ],
        priority_changes=[
            "Emphasize LLM/AI integration experience if any",
            "Add specific FastAPI details",
            "Highlight distributed systems expertise",
        ]
    )


@pytest.fixture
def mock_ats_review():
    """Create a valid ATS reviewer ReviewMemo."""
    return ReviewMemo(
        reviewer_role="ats",
        overall_score=7,
        strengths=[
            "Good keyword coverage",
            "Clean formatting for ATS parsing",
            "Standard section organization",
        ],
        weaknesses=[
            "Could add more JD-specific keywords",
            "Summary could be more keyword-rich",
        ],
        items=[
            {
                "category": "keyword_coverage",
                "severity": "warning",
                "section": "Skills",
                "finding": "Missing some JD keywords like GraphQL and LangGraph",
                "recommendation": "Add GraphQL and LangGraph if applicable from resume",
            }
        ],
        priority_changes=[
            "Add missing keywords to Skills section",
            "Ensure all JD keywords appear in CV",
            "Use standard formatting for parsing",
        ]
    )


@pytest.fixture
def mock_hallucination_report():
    """Create a valid HallucinationReport."""
    return HallucinationReport(
        has_hallucinations=False,
        items=[],
        summary="No hallucinations detected. All CV content aligns with source resume.",
    )


# ============================================================================
# Test: Standard Mode (review_mode=false)
# ============================================================================


@pytest.mark.asyncio
async def test_standard_mode_success(
    client,
    mock_cv,
):
    """Test standard pipeline: tailor → validate (no reviewers).

    Verifies:
    - review_panel is None
    - cv_data is populated from tailor agent
    - ats_issues and hallucination_warnings are lists
    - Response matches GenerateResponse schema
    """
    with patch("app.agents.pipeline.tailor_cv") as mock_tailor, \
         patch("app.agents.pipeline.validate_cv") as mock_validate:

        # Setup mocks
        mock_tailor.return_value = mock_cv
        mock_validate.return_value = {
            "cv_data": mock_cv.model_dump(mode="json"),
            "ats_issues": ["Missing LinkedIn URL in contact section"],
            "hallucination_warnings": [],
        }

        # Make request
        response = client.post(
            "/api/generate",
            json={
                "resume_text": SAMPLE_RESUME,
                "job_description": SAMPLE_JOB_DESCRIPTION,
                "review_mode": False,
                "model_name": "google:gemini-2.5-pro",
                "api_key": "test-api-key",
            }
        )

        # Assertions
        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "cv_data" in data
        assert "ats_issues" in data
        assert "hallucination_warnings" in data
        assert data["review_panel"] is None

        # Verify content
        assert data["cv_data"]["name"] == "John Doe"
        assert isinstance(data["ats_issues"], list)
        assert isinstance(data["hallucination_warnings"], list)

        # Verify agents were called correctly
        mock_tailor.assert_called_once()
        mock_validate.assert_called_once()


# ============================================================================
# Test: Review Mode (review_mode=true) — All Reviewers Succeed
# ============================================================================


@pytest.mark.asyncio
async def test_review_mode_all_reviewers_succeed(
    client,
    mock_cv,
    mock_hr_review,
    mock_technical_review,
    mock_ats_review,
    mock_hallucination_report,
):
    """Test review pipeline with all reviewers succeeding.

    Verifies:
    - review_panel contains all three reviews
    - hallucination_report is included
    - consensus_score is calculated correctly (avg of all three scores)
    - synthesis agent is called to refine CV
    - Final CV is validated
    """
    with patch("app.agents.pipeline.tailor_cv") as mock_tailor, \
         patch("app.agents.pipeline.review_as_hr") as mock_review_hr, \
         patch("app.agents.pipeline.review_as_technical") as mock_review_tech, \
         patch("app.agents.pipeline.review_as_ats") as mock_review_ats, \
         patch("app.agents.pipeline.check_hallucinations_ai") as mock_halluc, \
         patch("app.agents.pipeline.synthesize_cv") as mock_synthesize, \
         patch("app.agents.pipeline.validate_cv") as mock_validate:

        # Setup mocks
        mock_tailor.return_value = mock_cv
        mock_review_hr.return_value = mock_hr_review
        mock_review_tech.return_value = mock_technical_review
        mock_review_ats.return_value = mock_ats_review
        mock_halluc.return_value = mock_hallucination_report
        mock_synthesize.return_value = mock_cv
        mock_validate.return_value = {
            "cv_data": mock_cv.model_dump(mode="json"),
            "ats_issues": [],
            "hallucination_warnings": [],
        }

        # Make request
        response = client.post(
            "/api/generate",
            json={
                "resume_text": SAMPLE_RESUME,
                "job_description": SAMPLE_JOB_DESCRIPTION,
                "review_mode": True,
                "model_name": "google:gemini-2.5-pro",
                "api_key": "test-api-key",
                "review_model": "google:gemini-2.5-flash",
            }
        )

        # Assertions
        assert response.status_code == 200
        data = response.json()

        # Verify review_panel exists and has expected structure
        assert data["review_panel"] is not None
        assert "reviews" in data["review_panel"]
        assert "hallucination_report" in data["review_panel"]
        assert "consensus_score" in data["review_panel"]

        # Verify all reviews are included
        assert len(data["review_panel"]["reviews"]) == 3
        reviewer_roles = {r["reviewer_role"] for r in data["review_panel"]["reviews"]}
        assert reviewer_roles == {"hr", "technical", "ats"}

        # Verify consensus score calculation: (8 + 9 + 7) / 3 = 8.0
        assert data["review_panel"]["consensus_score"] == 8.0

        # Verify hallucination report
        assert data["review_panel"]["hallucination_report"]["has_hallucinations"] is False

        # Verify synthesis was called (because reviews succeeded)
        mock_synthesize.assert_called_once()

        # Verify final validator was called
        mock_validate.assert_called_once()


# ============================================================================
# Test: Review Mode — Partial Reviewer Failure
# ============================================================================


@pytest.mark.asyncio
async def test_review_mode_partial_reviewer_failure(
    client,
    mock_cv,
    mock_hr_review,
    mock_technical_review,
):
    """Test review pipeline with one reviewer failing.

    Verifies:
    - Successful reviews are still used (HR and Technical pass, ATS fails)
    - Failed reviewer is logged but doesn't stop pipeline
    - Synthesis still runs with successful reviews
    - Final response includes only successful reviews
    - Consensus score uses only successful reviews: (8 + 9) / 2 = 8.5
    """
    with patch("app.agents.pipeline.tailor_cv") as mock_tailor, \
         patch("app.agents.pipeline.review_as_hr") as mock_review_hr, \
         patch("app.agents.pipeline.review_as_technical") as mock_review_tech, \
         patch("app.agents.pipeline.review_as_ats") as mock_review_ats, \
         patch("app.agents.pipeline.check_hallucinations_ai") as mock_halluc, \
         patch("app.agents.pipeline.synthesize_cv") as mock_synthesize, \
         patch("app.agents.pipeline.validate_cv") as mock_validate:

        # Setup mocks
        mock_tailor.return_value = mock_cv
        mock_review_hr.return_value = mock_hr_review
        mock_review_tech.return_value = mock_technical_review
        mock_review_ats.side_effect = RuntimeError("ATS reviewer service unavailable")
        mock_halluc.return_value = HallucinationReport(
            has_hallucinations=False,
            items=[],
            summary="No issues found.",
        )
        mock_synthesize.return_value = mock_cv
        mock_validate.return_value = {
            "cv_data": mock_cv.model_dump(mode="json"),
            "ats_issues": [],
            "hallucination_warnings": [],
        }

        # Make request
        response = client.post(
            "/api/generate",
            json={
                "resume_text": SAMPLE_RESUME,
                "job_description": SAMPLE_JOB_DESCRIPTION,
                "review_mode": True,
                "model_name": "google:gemini-2.5-pro",
                "api_key": "test-api-key",
                "review_model": "google:gemini-2.5-flash",
            }
        )

        # Assertions
        assert response.status_code == 200
        data = response.json()

        # Verify only successful reviews are included (2 out of 3)
        assert len(data["review_panel"]["reviews"]) == 2
        reviewer_roles = {r["reviewer_role"] for r in data["review_panel"]["reviews"]}
        assert reviewer_roles == {"hr", "technical"}
        assert "ats" not in reviewer_roles

        # Verify consensus score is calculated from successful reviews: (8 + 9) / 2 = 8.5
        assert data["review_panel"]["consensus_score"] == 8.5

        # Verify synthesis still ran (because we got reviews)
        mock_synthesize.assert_called_once()


# ============================================================================
# Test: Review Mode — All Reviewers Fail (Edge Case)
# ============================================================================


@pytest.mark.asyncio
async def test_review_mode_all_reviewers_fail(
    client,
    mock_cv,
):
    """Test review pipeline when all reviewers fail.

    Verifies:
    - Synthesis is skipped (no reviews to synthesize from)
    - Original CV draft is returned (not refined)
    - review_panel contains empty reviews list
    - consensus_score is 0.0
    - Pipeline logs warning but completes
    """
    with patch("app.agents.pipeline.tailor_cv") as mock_tailor, \
         patch("app.agents.pipeline.review_as_hr") as mock_review_hr, \
         patch("app.agents.pipeline.review_as_technical") as mock_review_tech, \
         patch("app.agents.pipeline.review_as_ats") as mock_review_ats, \
         patch("app.agents.pipeline.check_hallucinations_ai") as mock_halluc, \
         patch("app.agents.pipeline.synthesize_cv") as mock_synthesize, \
         patch("app.agents.pipeline.validate_cv") as mock_validate:

        # Setup mocks
        mock_tailor.return_value = mock_cv
        mock_review_hr.side_effect = RuntimeError("HR reviewer failed")
        mock_review_tech.side_effect = RuntimeError("Technical reviewer failed")
        mock_review_ats.side_effect = RuntimeError("ATS reviewer failed")
        mock_halluc.side_effect = RuntimeError("Hallucination check failed")
        mock_synthesize.return_value = mock_cv  # Should NOT be called
        mock_validate.return_value = {
            "cv_data": mock_cv.model_dump(mode="json"),
            "ats_issues": [],
            "hallucination_warnings": [],
        }

        # Make request
        response = client.post(
            "/api/generate",
            json={
                "resume_text": SAMPLE_RESUME,
                "job_description": SAMPLE_JOB_DESCRIPTION,
                "review_mode": True,
                "model_name": "google:gemini-2.5-pro",
                "api_key": "test-api-key",
                "review_model": "google:gemini-2.5-flash",
            }
        )

        # Assertions
        assert response.status_code == 200
        data = response.json()

        # Verify review_panel has empty reviews and zero consensus
        assert len(data["review_panel"]["reviews"]) == 0
        assert data["review_panel"]["consensus_score"] == 0.0
        assert data["review_panel"]["hallucination_report"] is None

        # Verify synthesis was NOT called (no reviews to synthesize from)
        mock_synthesize.assert_not_called()

        # Verify validator was still called with original CV
        mock_validate.assert_called_once()


# ============================================================================
# Test: Response Schema Validation
# ============================================================================


@pytest.mark.asyncio
async def test_generate_response_schema_validation(
    client,
    mock_cv,
):
    """Test that response strictly conforms to GenerateResponse schema.

    Verifies:
    - cv_data is dict with proper structure
    - ats_issues is list of strings
    - hallucination_warnings is list of strings
    - review_panel is None or dict with reviews, hallucination_report, consensus_score
    - Response can be deserialized to GenerateResponse Pydantic model
    """
    with patch("app.agents.pipeline.tailor_cv") as mock_tailor, \
         patch("app.agents.pipeline.validate_cv") as mock_validate:

        # Setup mocks
        mock_tailor.return_value = mock_cv
        mock_validate.return_value = {
            "cv_data": mock_cv.model_dump(mode="json"),
            "ats_issues": ["Issue 1", "Issue 2"],
            "hallucination_warnings": ["Warning 1"],
        }

        # Make request
        response = client.post(
            "/api/generate",
            json={
                "resume_text": SAMPLE_RESUME,
                "job_description": SAMPLE_JOB_DESCRIPTION,
                "review_mode": False,
                "model_name": "google:gemini-2.5-pro",
                "api_key": "test-api-key",
            }
        )

        # Assertions
        assert response.status_code == 200
        data = response.json()

        # Verify schema: cv_data structure
        assert isinstance(data["cv_data"], dict)
        assert "name" in data["cv_data"]
        assert "sections" in data["cv_data"]

        # Verify schema: ats_issues
        assert isinstance(data["ats_issues"], list)
        assert all(isinstance(issue, str) for issue in data["ats_issues"])

        # Verify schema: hallucination_warnings
        assert isinstance(data["hallucination_warnings"], list)
        assert all(isinstance(warning, str) for warning in data["hallucination_warnings"])

        # Verify schema: review_panel
        assert data["review_panel"] is None

        # Verify Pydantic can deserialize the full response
        from app.api.generate import GenerateResponse
        response_model = GenerateResponse(**data)
        assert response_model.review_panel is None
