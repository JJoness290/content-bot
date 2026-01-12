import json
from datetime import datetime
from typing import Any

from app.core.db import get_connection


def list_tasks() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM tasks ORDER BY created_at DESC").fetchall()
        return [dict(row) for row in rows]


def get_task(task_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if not row:
            return None
        task = dict(row)
        task["details"] = json.loads(task["details_json"])
        return task


def create_task(title: str, status: str, category: str, details: dict[str, Any]) -> int:
    now = datetime.utcnow().isoformat()
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO tasks (title, status, category, details_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (title, status, category, json.dumps(details), now, now),
        )
        conn.commit()
        return int(cur.lastrowid)


def update_status(task_id: int, status: str) -> None:
    now = datetime.utcnow().isoformat()
    with get_connection() as conn:
        conn.execute(
            "UPDATE tasks SET status = ?, updated_at = ? WHERE id = ?",
            (status, now, task_id),
        )
        conn.commit()
