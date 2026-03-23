from pydantic import BaseModel, Field
from datetime import datetime
from typing import Any


class ChatMessage(BaseModel):
    """A single message in a chat conversation."""
    id: str = Field(..., description="Unique identifier for the message")
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="The message text content")
    kind: str = Field(..., description="Message kind/type: 'text', 'cv_update', etc.")
    timestamp: datetime = Field(..., description="ISO 8601 timestamp of when the message was created")


class IntakeTurnResult(BaseModel):
    """Output from the intake agent during conversation."""
    assistant_reply: str = Field(..., description="The assistant's conversational response to the user")
    ready_to_generate: bool = Field(..., description="Whether sufficient information has been collected to generate CV")
    extracted_constraints: list[str] = Field(default_factory=list, description="List of user requirements and constraints extracted from the conversation")
    missing_fields: list[str] = Field(default_factory=list, description="List of CV fields or information still needed from the user")


class RefinementResult(BaseModel):
    """Output from the refinement agent during CV editing."""
    assistant_reply: str = Field(..., description="The assistant's explanation of the changes made to the CV")
    updated_cv_dict: dict[str, Any] = Field(..., description="The modified CV data with refinements applied")


class ArtifactUpdate(BaseModel):
    """Represents an artifact update message with structured data."""
    type: str = Field(..., description="Type of artifact: 'cv', 'cover_letter', etc.")
    cv_data: dict[str, Any] = Field(..., description="The CV data payload")
