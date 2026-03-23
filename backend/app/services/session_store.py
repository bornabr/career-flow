from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import ClassVar, cast


class SessionStore:
    _RUN_TABLE_SCHEMA: ClassVar[str] = """
    CREATE TABLE IF NOT EXISTS session_runs (
      thread_id TEXT PRIMARY KEY,
      title TEXT,
      mode TEXT NOT NULL,
      status TEXT NOT NULL,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      model_name TEXT,
      review_model TEXT,
      requires_api_key_on_resume INTEGER NOT NULL DEFAULT 0,
      latest_assistant_message TEXT,
      has_cv INTEGER NOT NULL DEFAULT 0
    )
    """

    _MESSAGE_TABLE_SCHEMA: ClassVar[str] = """
    CREATE TABLE IF NOT EXISTS session_messages (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      thread_id TEXT NOT NULL,
      message_id TEXT NOT NULL,
      role TEXT NOT NULL,
      content TEXT NOT NULL,
      kind TEXT,
      timestamp TEXT NOT NULL,
      FOREIGN KEY (thread_id) REFERENCES session_runs (thread_id) ON DELETE CASCADE
    )
    """

    def __init__(self, db_path: str):
        self.db_path: str
        self.db_path = db_path
        self._init_tables()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        _ = conn.execute("PRAGMA foreign_keys = ON")
        return conn

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _row_to_session_dict(row: sqlite3.Row) -> dict[str, object]:
        session = cast(dict[str, object], dict(row))
        requires_api_key = cast(int, session["requires_api_key_on_resume"])
        has_cv = cast(int, session["has_cv"])
        session["requires_api_key_on_resume"] = bool(requires_api_key)
        session["has_cv"] = bool(has_cv)
        return session

    def _init_tables(self) -> None:
        with self._get_connection() as conn:
            _ = conn.execute(self._RUN_TABLE_SCHEMA)
            _ = conn.execute(self._MESSAGE_TABLE_SCHEMA)

    def create_session(
        self,
        thread_id: str,
        title: str,
        mode: str,
        status: str,
        model_name: str | None = None,
        review_model: str | None = None,
        requires_api_key_on_resume: bool = False,
    ) -> None:
        now = self._now_iso()
        with self._get_connection() as conn:
            _ = conn.execute(
                """
                INSERT INTO session_runs (
                    thread_id,
                    title,
                    mode,
                    status,
                    created_at,
                    updated_at,
                    model_name,
                    review_model,
                    requires_api_key_on_resume,
                    latest_assistant_message,
                    has_cv
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    thread_id,
                    title,
                    mode,
                    status,
                    now,
                    now,
                    model_name,
                    review_model,
                    int(requires_api_key_on_resume),
                    None,
                    0,
                ),
            )

    def update_session(self, thread_id: str, **kwargs: object) -> None:
        allowed_fields = {
            "title",
            "status",
            "latest_assistant_message",
            "has_cv",
            "model_name",
            "review_model",
        }
        unknown_fields = set(kwargs) - allowed_fields
        if unknown_fields:
            unknown_sorted = ", ".join(sorted(unknown_fields))
            raise ValueError(f"Unsupported update fields: {unknown_sorted}")

        if not kwargs:
            return

        values: list[object] = []
        assignments: list[str] = []

        for field, value in kwargs.items():
            if field == "has_cv":
                normalized_value = int(cast(bool, value))
            else:
                normalized_value = value
            assignments.append(f"{field} = ?")
            values.append(normalized_value)

        assignments.append("updated_at = ?")
        values.append(self._now_iso())
        values.append(thread_id)

        query = f"UPDATE session_runs SET {', '.join(assignments)} WHERE thread_id = ?"
        with self._get_connection() as conn:
            _ = conn.execute(query, values)

    def list_sessions(
        self,
        limit: int = 20,
        cursor: str | None = None,
    ) -> tuple[list[dict[str, object]], str | None]:
        if limit <= 0:
            raise ValueError("limit must be greater than 0")

        query = "SELECT * FROM session_runs"
        params: list[object] = []
        if cursor:
            query += " WHERE updated_at < ?"
            params.append(cursor)

        query += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit + 1)

        with self._get_connection() as conn:
            rows = cast(list[sqlite3.Row], conn.execute(query, params).fetchall())

        has_more = len(rows) > limit
        selected_rows = rows[:limit]
        sessions = [self._row_to_session_dict(row) for row in selected_rows]
        next_cursor = cast(str, sessions[-1]["updated_at"]) if has_more and sessions else None
        return sessions, next_cursor

    def get_session(self, thread_id: str) -> dict[str, object] | None:
        with self._get_connection() as conn:
            session_row = cast(
                sqlite3.Row | None,
                conn.execute(
                "SELECT * FROM session_runs WHERE thread_id = ?",
                (thread_id,),
                ).fetchone(),
            )
            if session_row is None:
                return None

            message_rows = cast(
                list[sqlite3.Row],
                conn.execute(
                """
                SELECT message_id, role, content, kind, timestamp
                FROM session_messages
                WHERE thread_id = ?
                ORDER BY timestamp ASC, id ASC
                """,
                (thread_id,),
                ).fetchall(),
            )

        session = self._row_to_session_dict(session_row)
        session["messages"] = [cast(dict[str, object], dict(row)) for row in message_rows]
        return session

    def add_message(
        self,
        thread_id: str,
        message_id: str,
        role: str,
        content: str,
        kind: str | None = None,
        timestamp: str | None = None,
    ) -> None:
        recorded_at = timestamp or self._now_iso()
        with self._get_connection() as conn:
            _ = conn.execute(
                """
                INSERT INTO session_messages (
                    thread_id,
                    message_id,
                    role,
                    content,
                    kind,
                    timestamp
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (thread_id, message_id, role, content, kind, recorded_at),
            )
