from pydantic import BaseModel, Field
from enum import Enum


class ReviewerRole(str, Enum):
    HR = "hr"
    TECHNICAL = "technical"
    ATS = "ats"


class ReviewItem(BaseModel):
    """A single review finding."""
    category: str = Field(..., description="Category of the finding (e.g., 'skills_gap', 'formatting', 'keyword_missing')")
    severity: str = Field(..., description="Severity: 'critical', 'warning', or 'suggestion'")
    section: str = Field(..., description="CV section this applies to (e.g., 'Experience', 'Skills', 'Summary')")
    finding: str = Field(..., description="Description of what was found")
    recommendation: str = Field(..., description="Specific actionable recommendation")


class ReviewMemo(BaseModel):
    """Structured output from a reviewer agent."""
    reviewer_role: str = Field(..., description="Role of the reviewer: 'hr', 'technical', or 'ats'")
    overall_score: int = Field(..., ge=1, le=10, description="Overall score 1-10 for how well the CV matches the JD from this reviewer's perspective")
    strengths: list[str] = Field(..., description="Top 3-5 strengths of the CV for this role")
    weaknesses: list[str] = Field(..., description="Top 3-5 weaknesses or gaps")
    items: list[ReviewItem] = Field(..., description="Detailed review findings with actionable recommendations")
    priority_changes: list[str] = Field(..., description="Top 3 highest-priority changes to make, in order of importance")


class HallucinationItem(BaseModel):
    """A single detected hallucination."""
    field_path: str = Field(..., description="Dot-notation path to the hallucinated field (e.g., 'sections.Skills[0].details')")
    hallucinated_content: str = Field(..., description="The content that appears hallucinated")
    confidence: str = Field(..., description="Confidence level: 'high', 'medium', or 'low'")
    reasoning: str = Field(..., description="Why this is considered hallucinated")


class HallucinationReport(BaseModel):
    """Output from the AI hallucination validator."""
    has_hallucinations: bool = Field(..., description="Whether any hallucinations were detected")
    items: list[HallucinationItem] = Field(default_factory=list, description="List of detected hallucinations")
    summary: str = Field(..., description="Brief summary of hallucination analysis")


class ReviewPanelResult(BaseModel):
    """Aggregated result from all reviewer agents."""
    reviews: list[ReviewMemo] = Field(..., description="Individual review memos from each reviewer")
    hallucination_report: HallucinationReport | None = Field(default=None, description="AI hallucination analysis if enabled")
    consensus_score: float = Field(..., description="Weighted average score across all reviewers")


class InteractiveReviewItem(BaseModel):
    """A single actionable review recommendation with deterministic key."""
    item_key: str = Field(..., description="Unique key: {reviewer_role}:{index} (e.g., 'hr:0', 'technical:1')")
    recommendation: str = Field(..., description="Specific actionable recommendation text")
    rationale: str = Field(..., description="Why this change is recommended")
    severity: str = Field(..., description="Severity: 'critical', 'warning', or 'suggestion'")


class InteractiveReviewMemo(BaseModel):
    """Normalized review memo with interactive items for HITL approval."""
    reviewer_role: str = Field(..., description="Role of reviewer: 'hr', 'technical', or 'ats'")
    items: list[InteractiveReviewItem] = Field(..., description="Interactive review items with unique keys")
    overall_score: int = Field(..., ge=1, le=10, description="Overall score 1-10")
    overall_rationale: str = Field(..., description="Summary rationale for the score and recommendations")


class ReviewDecision(BaseModel):
    """User's decision to accept or reject a single review recommendation."""
    item_key: str = Field(..., description="Unique item key (e.g., 'hr:0')")
    accepted: bool = Field(..., description="True if accepted, False if rejected")


class ReviewApprovalPayload(BaseModel):
    """Complete payload sent to frontend during review interrupt."""
    interactive_reviews: list[InteractiveReviewMemo] = Field(..., description="Normalized reviews for all reviewers")
    hallucination_report: dict[str, object] | None = Field(default=None, description="Hallucination analysis if available")
    consensus_score: float = Field(..., description="Weighted average score across reviewers")


# Rebuild for forward references
ReviewMemo.model_rebuild()
HallucinationReport.model_rebuild()
ReviewPanelResult.model_rebuild()
InteractiveReviewItem.model_rebuild()
InteractiveReviewMemo.model_rebuild()
ReviewDecision.model_rebuild()
ReviewApprovalPayload.model_rebuild()
