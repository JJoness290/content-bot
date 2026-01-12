import json
from datetime import datetime
from typing import Any

from app.core.db import get_connection


def log_action(name: str, action_type: str, metadata: dict[str, Any], decision: str, reason: str) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO actions (name, type, metadata_json, decision, reason, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                action_type,
                json.dumps(metadata),
                decision,
                reason,
                datetime.utcnow().isoformat(),
            ),
        )
        conn.commit()


def list_actions(limit: int = 50) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM actions ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(row) for row in rows]
