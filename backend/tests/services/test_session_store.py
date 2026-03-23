from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import cast

from app.services.session_store import SessionStore


def _create_session_store(tmp_path: Path) -> SessionStore:
    db_path = tmp_path / "test_sessions.db"
    return SessionStore(str(db_path))


def test_init_creates_tables(tmp_path: Path):
    db_path = tmp_path / "init_tables.db"
    store = SessionStore(str(db_path))

    with sqlite3.connect(store.db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = cast(
            list[sqlite3.Row],
            conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall(),
        )

    table_names = {row["name"] for row in rows}
    assert "session_runs" in table_names
    assert "session_messages" in table_names


def test_create_session(tmp_path: Path):
    session_store = _create_session_store(tmp_path)
    session_store.create_session(
        thread_id="thread-1",
        title="Initial Run",
        mode="standard",
        status="running",
        model_name="google:gemini-2.5-pro",
        review_model="google:gemini-2.5-flash",
        requires_api_key_on_resume=True,
    )

    session = session_store.get_session("thread-1")

    assert session is not None
    assert session["thread_id"] == "thread-1"
    assert session["title"] == "Initial Run"
    assert session["mode"] == "standard"
    assert session["status"] == "running"
    assert session["model_name"] == "google:gemini-2.5-pro"
    assert session["review_model"] == "google:gemini-2.5-flash"
    assert session["requires_api_key_on_resume"] is True
    assert session["has_cv"] is False
    assert session["latest_assistant_message"] is None
    _ = datetime.fromisoformat(str(session["created_at"]))
    _ = datetime.fromisoformat(str(session["updated_at"]))


def test_update_session(tmp_path: Path):
    session_store = _create_session_store(tmp_path)
    session_store.create_session(
        thread_id="thread-1",
        title="Initial",
        mode="standard",
        status="running",
    )
    before = session_store.get_session("thread-1")
    assert before is not None

    session_store.update_session(
        "thread-1",
        title="Updated",
        status="completed",
        latest_assistant_message="Done",
        has_cv=True,
    )
    after = session_store.get_session("thread-1")
    assert after is not None

    assert after["title"] == "Updated"
    assert after["status"] == "completed"
    assert after["latest_assistant_message"] == "Done"
    assert after["has_cv"] is True
    assert after["updated_at"] != before["updated_at"]


def test_list_sessions_empty(tmp_path: Path):
    session_store = _create_session_store(tmp_path)
    sessions, next_cursor = session_store.list_sessions(limit=20)

    assert sessions == []
    assert next_cursor is None


def test_list_sessions_pagination(tmp_path: Path):
    session_store = _create_session_store(tmp_path)
    session_store.create_session("thread-1", "A", "standard", "completed")
    session_store.create_session("thread-2", "B", "standard", "completed")
    session_store.create_session("thread-3", "C", "review", "completed")

    with sqlite3.connect(session_store.db_path) as conn:
        _ = conn.execute(
            "UPDATE session_runs SET updated_at = ? WHERE thread_id = ?",
            ("2026-03-23T10:00:00+00:00", "thread-1"),
        )
        _ = conn.execute(
            "UPDATE session_runs SET updated_at = ? WHERE thread_id = ?",
            ("2026-03-23T11:00:00+00:00", "thread-2"),
        )
        _ = conn.execute(
            "UPDATE session_runs SET updated_at = ? WHERE thread_id = ?",
            ("2026-03-23T12:00:00+00:00", "thread-3"),
        )

    page_one, cursor = session_store.list_sessions(limit=2)
    assert [item["thread_id"] for item in page_one] == ["thread-3", "thread-2"]
    assert cursor == "2026-03-23T11:00:00+00:00"

    page_two, next_cursor = session_store.list_sessions(limit=2, cursor=cursor)
    assert [item["thread_id"] for item in page_two] == ["thread-1"]
    assert next_cursor is None


def test_get_session(tmp_path: Path):
    session_store = _create_session_store(tmp_path)
    session_store.create_session("thread-42", "Lookup", "review", "running")

    session = session_store.get_session("thread-42")

    assert session is not None
    assert session["thread_id"] == "thread-42"
    assert session["title"] == "Lookup"
    assert session["mode"] == "review"
    assert session["messages"] == []


def test_get_session_not_found(tmp_path: Path):
    session_store = _create_session_store(tmp_path)
    assert session_store.get_session("missing") is None


def test_add_message(tmp_path: Path):
    session_store = _create_session_store(tmp_path)
    session_store.create_session("thread-1", "Chat", "standard", "running")

    session_store.add_message(
        thread_id="thread-1",
        message_id="msg-1",
        role="assistant",
        content="Hello",
        kind="text",
    )

    session = session_store.get_session("thread-1")
    assert session is not None
    messages = cast(list[dict[str, object]], session["messages"])
    assert len(messages) == 1

    message = messages[0]
    assert message["message_id"] == "msg-1"
    assert message["role"] == "assistant"
    assert message["content"] == "Hello"
    assert message["kind"] == "text"

    recorded = datetime.fromisoformat(str(message["timestamp"]))
    assert recorded.tzinfo is not None
    assert recorded <= datetime.now(timezone.utc)
