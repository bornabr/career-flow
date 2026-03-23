"""Session history API endpoints — list and detail views for past sessions."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Query

from app.config import get_settings
from app.schemas.session import SessionSummary, SessionDetail, SessionListResponse
from app.services.session_store import SessionStore

router = APIRouter()


def _get_session_store(request: Request) -> SessionStore:
    return request.app.state.session_store


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    request: Request,
    limit: int = Query(default=None, ge=1, le=100),
    cursor: str | None = Query(default=None),
):
    """Return paginated list of sessions, most recent first."""
    settings = get_settings()
    page_size = limit or settings.session_page_size_default
    store = _get_session_store(request)
    items, next_cursor = store.list_sessions(limit=page_size, cursor=cursor)
    summaries = [SessionSummary(**item) for item in items]
    return SessionListResponse(items=summaries, next_cursor=next_cursor)


@router.get("/sessions/{thread_id}", response_model=SessionDetail)
async def get_session(thread_id: str, request: Request):
    """Return full session detail including messages."""
    store = _get_session_store(request)
    session = store.get_session(thread_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionDetail(**session)
