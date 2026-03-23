"""Tests for session API endpoints: list and detail."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import patch, MagicMock

import pytest


def _make_session_dict(
    thread_id: str = "t-1",
    title: str = "Test",
    mode: str = "standard",
    status: str = "completed",
    **overrides: Any,
) -> dict[str, Any]:
    return {
        "thread_id": thread_id,
        "title": title,
        "mode": mode,
        "status": status,
        "created_at": "2026-03-23T10:00:00+00:00",
        "updated_at": "2026-03-23T10:05:00+00:00",
        "latest_assistant_message": None,
        "has_cv": False,
        "requires_api_key_on_resume": False,
        "model_name": "google:gemini-2.5-pro",
        "review_model": None,
        **overrides,
    }


@pytest.fixture
def mock_session_store():
    store = MagicMock()
    with patch.object(
        type(MagicMock()), "state", new_callable=lambda: property(lambda self: self._state)
    ):
        pass
    return store


class TestListSessions:
    def test_list_returns_empty(self, client):
        client.app.state.session_store.list_sessions = MagicMock(return_value=([], None))
        response = client.get("/api/sessions")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["next_cursor"] is None

    def test_list_returns_sessions(self, client):
        sessions = [_make_session_dict("t-1", "A"), _make_session_dict("t-2", "B")]
        client.app.state.session_store.list_sessions = MagicMock(return_value=(sessions, None))
        response = client.get("/api/sessions")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["items"][0]["thread_id"] == "t-1"
        assert data["items"][1]["thread_id"] == "t-2"

    def test_list_passes_limit_and_cursor(self, client):
        mock_fn = MagicMock(return_value=([], None))
        client.app.state.session_store.list_sessions = mock_fn
        client.get("/api/sessions?limit=5&cursor=2026-03-23T10:00:00")
        mock_fn.assert_called_once_with(limit=5, cursor="2026-03-23T10:00:00")

    def test_list_pagination_cursor(self, client):
        sessions = [_make_session_dict("t-1")]
        client.app.state.session_store.list_sessions = MagicMock(
            return_value=(sessions, "2026-03-23T09:00:00+00:00")
        )
        response = client.get("/api/sessions?limit=1")
        data = response.json()
        assert data["next_cursor"] == "2026-03-23T09:00:00+00:00"


class TestGetSession:
    def test_get_existing_session(self, client):
        session = {
            **_make_session_dict("t-42", "Detail"),
            "messages": [
                {"message_id": "m-1", "role": "user", "content": "Hi", "kind": "text", "timestamp": "2026-03-23T10:00:00+00:00"}
            ],
        }
        client.app.state.session_store.get_session = MagicMock(return_value=session)
        response = client.get("/api/sessions/t-42")
        assert response.status_code == 200
        data = response.json()
        assert data["thread_id"] == "t-42"
        assert len(data["messages"]) == 1

    def test_get_missing_session_returns_404(self, client):
        client.app.state.session_store.get_session = MagicMock(return_value=None)
        response = client.get("/api/sessions/missing-id")
        assert response.status_code == 404
