from __future__ import annotations

import logging
from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.config import get_stream_writer

from app.agents.intake import run_intake_turn
from app.agents.refinement import run_refinement_turn
from app.graph.chat_state import IntakeState, RefinementState
from app.graph.runtime import GraphRuntimeConfig

logger = logging.getLogger(__name__)


async def intake_node(state: IntakeState, config: RunnableConfig) -> dict[str, Any]:
    """Process one intake conversation turn.

    Calls the intake agent to ask clarifying questions, extract constraints,
    and determine readiness for CV generation. Returns state updates with the
    latest assistant reply, readiness flag, and extracted context.
    """
    writer = get_stream_writer()
    writer({
        "type": "chat.intake.started",
        "data": {
            "step": "intake",
        },
    })

    runtime: GraphRuntimeConfig = config["configurable"]["runtime"]

    conversation_history = [
        {"role": message.role, "content": message.content}
        for message in state.get("messages", [])
    ]

    result = await run_intake_turn(
        conversation_history=conversation_history,
        resume_text=state.get("resume_text", ""),
        job_description=state.get("job_description", ""),
        model_name=runtime.model_name,
        api_key=runtime.api_key,
        user_instructions=state.get("user_instructions"),
    )

    writer({
        "type": "chat.intake.completed",
        "data": {
            "ready_to_generate": result.ready_to_generate,
        },
    })

    return {
        "assistant_reply": result.assistant_reply,
        "ready_to_generate": result.ready_to_generate,
        "extracted_constraints": result.extracted_constraints,
        "missing_fields": result.missing_fields,
    }


async def refinement_node(state: RefinementState, config: RunnableConfig) -> dict[str, Any]:
    """Process one post-generation refinement turn.

    Applies user-requested CV edits through the refinement agent and returns
    updated CV JSON plus the assistant explanation of changes made.
    """
    writer = get_stream_writer()
    writer({
        "type": "chat.refinement.started",
        "data": {
            "step": "refinement",
        },
    })

    runtime: GraphRuntimeConfig = config["configurable"]["runtime"]

    result = await run_refinement_turn(
        current_cv_dict=state.get("current_cv_dict", {}),
        resume_text=state.get("resume_text", ""),
        job_description=state.get("job_description", ""),
        user_message=state.get("latest_user_message", ""),
        model_name=runtime.model_name,
        api_key=runtime.api_key,
    )

    writer({
        "type": "chat.refinement.completed",
        "data": {
            "step": "refinement",
        },
    })

    return {
        "updated_cv_dict": result.updated_cv_dict,
        "assistant_reply": result.assistant_reply,
    }
