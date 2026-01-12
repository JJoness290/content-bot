import json
import sqlite3
import uuid
from datetime import datetime
from typing import Any

from app.core.db import get_connection


def init_video_queue_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS content_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uuid TEXT NOT NULL,
                platform TEXT NOT NULL,
                kind TEXT NOT NULL,
                status TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


def _ensure_video_queue_ready() -> None:
    try:
        init_video_queue_db()
    except sqlite3.Error:
        return


def create_script_item(platform: str, topic: str, script: dict[str, Any]) -> dict[str, Any]:
    _ensure_video_queue_ready()
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
    try:
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
    except sqlite3.Error:
        return {}
    return dict(row) if row else {}


def list_scripts(platform: str) -> list[dict[str, Any]]:
    _ensure_video_queue_ready()
    try:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM content_queue
                WHERE platform = ? AND kind = ?
                ORDER BY created_at DESC
                """,
                (platform, "SCRIPT"),
            ).fetchall()
    except sqlite3.Error:
        return []
    return [dict(row) for row in rows]


def list_outputs_for_script(script_id: int) -> list[dict[str, Any]]:
    _ensure_video_queue_ready()
    try:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM content_queue
                WHERE kind != ? AND json_extract(payload_json, '$.script_id') = ?
                ORDER BY created_at DESC
                """,
                ("SCRIPT", script_id),
            ).fetchall()
    except sqlite3.Error:
        return []
    return [dict(row) for row in rows]


def insert_output(platform: str, kind: str, payload: dict[str, Any]) -> dict[str, Any]:
    _ensure_video_queue_ready()
    now = datetime.utcnow().isoformat()
    try:
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
    except sqlite3.Error:
        return {}
    return dict(row) if row else {}


def update_script_payload(script_id: int, updates: dict[str, Any]) -> None:
    _ensure_video_queue_ready()
    try:
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
    except sqlite3.Error:
        return
