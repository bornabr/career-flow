from pydantic import BaseModel, Field
from typing import Any, Optional


class SessionSummary(BaseModel):
    """Session metadata for list views."""
    thread_id: str = Field(..., description="Unique thread identifier for this session")
    title: str = Field(..., description="User-visible session title")
    mode: str = Field(..., description="Generation mode: 'standard' or 'review'")
    status: str = Field(..., description="Session status: 'running', 'completed', 'failed', 'interrupted'")
    created_at: str = Field(..., description="ISO 8601 timestamp when session was created")
    updated_at: str = Field(..., description="ISO 8601 timestamp when session was last updated")
    latest_assistant_message: Optional[str] = Field(None, description="Latest assistant message for preview")
    has_cv: bool = Field(..., description="Whether this session has generated a CV")
    requires_api_key_on_resume: bool = Field(..., description="Whether resuming this session requires an API key")


class SessionDetail(SessionSummary):
    """Full session detail including messages and artifacts."""
    messages: list[dict[str, Any]] = Field(default_factory=list, description="Full conversation history")
    cv_data: Optional[dict[str, Any]] = Field(None, description="Generated CV data if available")
    review_panel: Optional[dict[str, Any]] = Field(None, description="Review committee results if in review mode")
    pending_interrupt: Optional[dict[str, Any]] = Field(None, description="Details of pending HITL interrupt if any")


class SessionListResponse(BaseModel):
    """Paginated session list response."""
    items: list[SessionSummary] = Field(..., description="Session summaries for this page")
    next_cursor: Optional[str] = Field(None, description="Cursor for next page, None if last page")
