from datetime import datetime

from moneyos.app.core.db import get_connection


def add_notification(level: str, message: str) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO notifications (level, message, created_at)
            VALUES (?, ?, ?)
            """,
            (level, message, datetime.utcnow().isoformat()),
        )
        conn.commit()


def list_notifications(limit: int = 20) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM notifications ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(row) for row in rows]
