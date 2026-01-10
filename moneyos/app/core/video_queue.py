import json
import uuid
from datetime import datetime
from typing import Any

from moneyos.app.core.db import get_connection


def create_script_item(platform: str, topic: str, script: dict[str, Any]) -> dict[str, Any]:
    now = datetime.utcnow().isoformat()
    payload = {
        "topic": topic,
        "hook": script["hook"],
        "body": script["body"],
        "cta": script["cta"],
        "caption": script["caption"],
        "hashtags": script["hashtags"],
        "title": script.get("title"),
    }
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO content_queue (
                uuid, platform, kind, status, payload_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                platform,
                "SCRIPT",
                "READY",
                json.dumps(payload),
                now,
                now,
            ),
        )
        conn.commit()
        item_id = int(cur.lastrowid)
        row = conn.execute("SELECT * FROM content_queue WHERE id = ?", (item_id,)).fetchone()
    return dict(row)


def list_scripts(platform: str) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM content_queue
            WHERE platform = ? AND kind = ?
            ORDER BY created_at DESC
            """,
            (platform, "SCRIPT"),
        ).fetchall()
    return [dict(row) for row in rows]


def list_outputs_for_script(script_id: int) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM content_queue
            WHERE kind != ? AND json_extract(payload_json, '$.script_id') = ?
            ORDER BY created_at DESC
            """,
            ("SCRIPT", script_id),
        ).fetchall()
    return [dict(row) for row in rows]


def insert_output(platform: str, kind: str, payload: dict[str, Any]) -> dict[str, Any]:
    now = datetime.utcnow().isoformat()
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO content_queue (
                uuid, platform, kind, status, payload_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                platform,
                kind,
                "READY",
                json.dumps(payload),
                now,
                now,
            ),
        )
        conn.commit()
        item_id = int(cur.lastrowid)
        row = conn.execute("SELECT * FROM content_queue WHERE id = ?", (item_id,)).fetchone()
    return dict(row)


def update_script_payload(script_id: int, updates: dict[str, Any]) -> None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT payload_json FROM content_queue WHERE id = ?",
            (script_id,),
        ).fetchone()
        if not row:
            return
        payload = json.loads(row["payload_json"] or "{}")
        payload.update(updates)
        conn.execute(
            "UPDATE content_queue SET payload_json = ?, updated_at = ? WHERE id = ?",
            (json.dumps(payload), datetime.utcnow().isoformat(), script_id),
        )
        conn.commit()
