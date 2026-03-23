from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict

from app.schemas.chat import ChatMessage


class IntakeState(TypedDict, total=False):
    """LangGraph state for pre-generation intake conversation.

    Attributes:
        messages: Conversation history (reducer: append)
        resume_text: Original resume text
        job_description: Target job description
        user_instructions: Optional user instructions
        extracted_constraints: Constraints extracted from conversation
        missing_fields: Fields still needing clarification
        ready_to_generate: Whether sufficient context gathered
        assistant_reply: Latest assistant response
    """
    messages: Annotated[list[ChatMessage], operator.add]
    resume_text: str
    job_description: str
    user_instructions: str | None
    extracted_constraints: list[str]
    missing_fields: list[str]
    ready_to_generate: bool
    assistant_reply: str | None


class RefinementState(TypedDict, total=False):
    """LangGraph state for post-generation CV refinement.

    Attributes:
        messages: Conversation history (reducer: append)
        current_cv_dict: Current CV data as dict
        resume_text: Original resume text (for anti-hallucination)
        job_description: Target job description (context)
        latest_user_message: User's refinement request
        updated_cv_dict: Modified CV data after refinement
        assistant_reply: Assistant explanation of changes
    """
    messages: Annotated[list[ChatMessage], operator.add]
    current_cv_dict: dict[str, Any]
    resume_text: str
    job_description: str
    latest_user_message: str
    updated_cv_dict: dict[str, Any] | None
    assistant_reply: str | None
