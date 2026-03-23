"""LangGraph streaming event helpers for progress tracking.

This module provides helper functions for emitting custom progress events during
graph execution. Events are designed for Server-Sent Events (SSE) streaming and
provide real-time feedback on generation pipeline progress.

Event Schema:
    {
        "type": str,           # Event identifier (e.g., "run.started", "step.completed")
        "timestamp": str,      # ISO 8601 UTC timestamp
        "data": dict,          # Event-specific payload
    }

Usage:
    async def my_node(state, config):
        writer = get_stream_writer()  # From langgraph.config
        emit_run_started(writer, state["request_id"], state["review_mode"])
        # ... do work ...
        emit_step_completed(writer, "generation")
        return {"final_response": {...}}

Each helper wraps the writer callable from langgraph.config.get_stream_writer(),
which accepts a single JSON-serializable dict argument.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable


def _now_iso() -> str:
    """Return current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


def emit_run_started(writer: Callable[[dict[str, Any]], None], thread_id: str, review_mode: bool) -> None:
    """Emit event when a generation run starts.

    Event type: "run.started"

    Args:
        writer: Stream writer callable from langgraph.config.get_stream_writer()
        thread_id: Unique identifier for this run
        review_mode: Whether review committee mode is enabled
    """
    writer({
        "type": "run.started",
        "timestamp": _now_iso(),
        "data": {
            "thread_id": thread_id,
            "review_mode": review_mode,
        }
    })


def emit_step_started(writer: Callable[[dict[str, Any]], None], step_name: str) -> None:
    """Emit event when a pipeline step begins.

    Event type: "step.started"

    Args:
        writer: Stream writer callable from langgraph.config.get_stream_writer()
        step_name: Name of the step (e.g., "generation", "review", "validation")
    """
    writer({
        "type": "step.started",
        "timestamp": _now_iso(),
        "data": {
            "step_name": step_name,
        }
    })


def emit_step_completed(writer: Callable[[dict[str, Any]], None], step_name: str) -> None:
    """Emit event when a pipeline step finishes.

    Event type: "step.completed"

    Args:
        writer: Stream writer callable from langgraph.config.get_stream_writer()
        step_name: Name of the step (e.g., "generation", "review", "validation")
    """
    writer({
        "type": "step.completed",
        "timestamp": _now_iso(),
        "data": {
            "step_name": step_name,
        }
    })


def emit_review_memo(
    writer: Callable[[dict[str, Any]], None],
    reviewer_role: str,
    memo: dict[str, Any],
    item_keys: list[str] | None = None
) -> None:
    """Emit a review memo from a reviewer agent.

    Event type: "review.memo"

    Args:
        writer: Stream writer callable from langgraph.config.get_stream_writer()
        reviewer_role: Role of the reviewer (e.g., "hr", "technical", "ats")
        memo: ReviewMemo object as dict (use ReviewMemo.model_dump())
        item_keys: Optional list of normalized item keys (e.g., ["hr:0", "hr:1"]) for frontend tracking.
                   If None, omitted from payload for backward compatibility.
    """
    data = {
        "reviewer_role": reviewer_role,
        "memo": memo,
    }
    if item_keys is not None:
        data["item_keys"] = item_keys
    
    writer({
        "type": "review.memo",
        "timestamp": _now_iso(),
        "data": data,
    })


def emit_review_failed(writer: Callable[[dict[str, Any]], None], reviewer_role: str, error: str) -> None:
    """Emit event when a reviewer agent fails.

    Event type: "review.failed"

    Args:
        writer: Stream writer callable from langgraph.config.get_stream_writer()
        reviewer_role: Role of the reviewer that failed (e.g., "hr", "technical", "ats")
        error: Error message describing the failure
    """
    writer({
        "type": "review.failed",
        "timestamp": _now_iso(),
        "data": {
            "reviewer_role": reviewer_role,
            "error": error,
        }
    })


def emit_validation_completed(
    writer: Callable[[dict[str, Any]], None],
    ats_issues: list[dict[str, Any]],
    hallucination_warnings: list[dict[str, Any]]
) -> None:
    """Emit validation results from the validator.

    Event type: "validation.completed"

    Args:
        writer: Stream writer callable from langgraph.config.get_stream_writer()
        ats_issues: List of ATS compliance issues found
        hallucination_warnings: List of detected hallucinations
    """
    writer({
        "type": "validation.completed",
        "timestamp": _now_iso(),
        "data": {
            "ats_issues": ats_issues,
            "hallucination_warnings": hallucination_warnings,
        }
    })


def emit_result(writer: Callable[[dict[str, Any]], None], response: dict[str, Any]) -> None:
    """Emit the final generation result.

    Event type: "result"

    Args:
        writer: Stream writer callable from langgraph.config.get_stream_writer()
        response: Final response dict (full final_response from state)
    """
    writer({
        "type": "result",
        "timestamp": _now_iso(),
        "data": response,
    })


def emit_interrupt_pending(writer: Callable[[dict[str, Any]], None], payload: dict[str, Any]) -> None:
    """Emit interrupt.pending event when review approval is required."""
    writer({
        "type": "interrupt.pending",
        "timestamp": _now_iso(),
        "data": payload,
    })


def emit_error(writer: Callable[[dict[str, Any]], None], message: str) -> None:
    """Emit an error event.

    Event type: "error"

    Args:
        writer: Stream writer callable from langgraph.config.get_stream_writer()
        message: Error message
    """
    writer({
        "type": "error",
        "timestamp": _now_iso(),
        "data": {
            "message": message,
        }
    })


def emit_run_completed(writer: Callable[[dict[str, Any]], None], thread_id: str, status: str) -> None:
    """Emit event when a generation run completes.

    Event type: "run.completed"

    Args:
        writer: Stream writer callable from langgraph.config.get_stream_writer()
        thread_id: Unique identifier for this run
        status: Final status ("success" or "error")
    """
    writer({
        "type": "run.completed",
        "timestamp": _now_iso(),
        "data": {
            "thread_id": thread_id,
            "status": status,
        }
    })
