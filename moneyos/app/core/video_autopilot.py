from __future__ import annotations

import json
import random
from datetime import datetime, timedelta
from typing import Any

from app.core import notifier
from app.core.db import get_connection
from app.core.video_pipeline import ScriptItem, generate_script, generate_video_for_script
from app.core.video_queue import (
    create_script_item,
    init_video_queue_db,
    list_outputs_for_script,
    list_scripts,
)

DEFAULT_INTERVAL_MINUTES = 15
JOB_ID = "video_autopilot_tick"
LOCK_TIMEOUT = timedelta(minutes=30)
DEFAULT_PLATFORMS = ["tiktok", "youtube"]
DEFAULT_TOPICS = [
    "Budgeting apps that save you money",
    "Best cash-back cards for everyday spend",
    "Avoid these 3 money leaks every month",
    "The fastest way to build an emergency fund",
]


def _now() -> datetime:
    return datetime.utcnow()


def _load_autopilot_config() -> dict[str, Any]:
    interval = DEFAULT_INTERVAL_MINUTES
    platforms = list(DEFAULT_PLATFORMS)
    config_path = (
        __import__("pathlib").Path(__file__).resolve().parents[2]
        / "config"
        / "settings.yaml"
    )
    if not config_path.exists():
        return {"interval_minutes": interval, "platforms": platforms}

    in_autopilot = False
    reading_platforms = False
    parsed_platforms: list[str] = []
    for raw_line in config_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if not raw_line.startswith(" "):
            in_autopilot = line.startswith("autopilot:")
            reading_platforms = False
            continue
        if not in_autopilot:
            continue
        if line.startswith("interval_minutes:"):
            value = line.split(":", 1)[1].strip()
            if value.isdigit():
                interval = int(value)
            reading_platforms = False
            continue
        if line.startswith("platforms:"):
            reading_platforms = True
            parsed_platforms = []
            continue
        if reading_platforms and line.startswith("-"):
            platform = line.lstrip("-").strip().lower()
            if platform:
                parsed_platforms.append(platform)
            continue
        if reading_platforms and ":" in line:
            reading_platforms = False
    if parsed_platforms:
        platforms = parsed_platforms
    return {"interval_minutes": interval, "platforms": platforms}


def init_video_autopilot_state() -> dict[str, Any]:
    init_video_queue_db()
    config = _load_autopilot_config()
    interval = config["interval_minutes"]
    platforms = config["platforms"]
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS video_autopilot_state (
                platform TEXT PRIMARY KEY,
                enabled INTEGER NOT NULL DEFAULT 1,
                interval_minutes INTEGER NOT NULL DEFAULT 15,
                last_run_at TEXT,
                last_action TEXT,
                last_error TEXT,
                locked_at TEXT,
                last_script_id INTEGER,
                last_video_payload_json TEXT
            )
            """
        )
        for platform in platforms:
            row = conn.execute(
                "SELECT platform FROM video_autopilot_state WHERE platform = ?",
                (platform,),
            ).fetchone()
            if row:
                conn.execute(
                    "UPDATE video_autopilot_state SET interval_minutes = ? WHERE platform = ?",
                    (interval, platform),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO video_autopilot_state (
                        platform, enabled, interval_minutes, last_run_at, last_action, last_error,
                        locked_at, last_script_id, last_video_payload_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (platform, 1, interval, None, None, None, None, None, None),
                )
        conn.commit()
    return config


def _load_platform_state(conn, platform: str) -> dict[str, Any]:
    row = conn.execute(
        "SELECT * FROM video_autopilot_state WHERE platform = ?",
        (platform,),
    ).fetchone()
    return dict(row) if row else {}


def _update_platform_state(conn, platform: str, **updates: Any) -> None:
    fields = ", ".join([f"{key} = ?" for key in updates])
    values = list(updates.values())
    values.append(platform)
    conn.execute(
        f"UPDATE video_autopilot_state SET {fields} WHERE platform = ?",
        values,
    )
    conn.commit()


def enable_autopilot() -> dict[str, Any]:
    config = init_video_autopilot_state()
    with get_connection() as conn:
        conn.execute("UPDATE video_autopilot_state SET enabled = 1")
        conn.commit()
    return config


def disable_autopilot() -> None:
    init_video_autopilot_state()
    with get_connection() as conn:
        conn.execute("UPDATE video_autopilot_state SET enabled = 0")
        conn.commit()


def schedule_job(scheduler, interval_minutes: int) -> None:
    if scheduler.get_job(JOB_ID):
        scheduler.remove_job(JOB_ID)
    scheduler.add_job(
        tick,
        "interval",
        minutes=interval_minutes,
        id=JOB_ID,
        replace_existing=True,
    )


def remove_job(scheduler) -> None:
    if scheduler.get_job(JOB_ID):
        scheduler.remove_job(JOB_ID)


def _queue_has_video(script_id: int, platform: str) -> bool:
    outputs = list_outputs_for_script(script_id)
    video_kind = "VIDEO_MP4" if platform == "tiktok" else "SHORT_VIDEO_MP4"
    return any(output.get("kind") == video_kind for output in outputs)


def _generate_topic(platform: str) -> str:
    base = random.choice(DEFAULT_TOPICS)
    suffix = "for TikTok" if platform == "tiktok" else "for YouTube Shorts"
    return f"{base} ({suffix})"


def _run_for_platform(platform: str) -> None:
    init_video_queue_db()
    with get_connection() as conn:
        state = _load_platform_state(conn, platform)
        if not state:
            return
        if not state.get("enabled", 1):
            _update_platform_state(
                conn,
                platform,
                last_run_at=_now().isoformat(),
                last_action="Disabled",
                last_error=None,
            )
            return
        locked_at = state.get("locked_at")
        if locked_at:
            lock_time = datetime.fromisoformat(locked_at)
            if _now() - lock_time < LOCK_TIMEOUT:
                return
        _update_platform_state(conn, platform, locked_at=_now().isoformat())

    try:
        scripts = list_scripts(platform)
        if not scripts:
            topic = _generate_topic(platform)
            payload = generate_script(topic, platform)
            new_script = create_script_item(platform, topic, payload)
            script_id = new_script.get("id")
            if script_id is None:
                raise RuntimeError("Failed to create script item.")
            with get_connection() as conn:
                _update_platform_state(
                    conn,
                    platform,
                    last_run_at=_now().isoformat(),
                    last_action=f"Created script #{script_id}",
                    last_error=None,
                    last_script_id=script_id,
                )
            scripts = [new_script]

        next_script = None
        for script in scripts:
            if not _queue_has_video(script["id"], platform):
                next_script = script
                break
        if next_script:
            payload = next_script.get("payload_json")
            script_payload = payload if isinstance(payload, dict) else json.loads(payload)
            output = generate_video_for_script(
                ScriptItem(
                    id=next_script["id"],
                    platform=platform,
                    payload=script_payload,
                )
            )
            with get_connection() as conn:
                _update_platform_state(
                    conn,
                    platform,
                    last_run_at=_now().isoformat(),
                    last_action=f"Generated video for script #{next_script['id']}",
                    last_error=None,
                    last_script_id=next_script["id"],
                    last_video_payload_json=json.dumps(output),
                )
        else:
            with get_connection() as conn:
                _update_platform_state(
                    conn,
                    platform,
                    last_run_at=_now().isoformat(),
                    last_action="Queue already populated",
                    last_error=None,
                )
    except Exception as exc:
        notifier.add_notification("ERROR", f"Video autopilot failed for {platform}: {exc}")
        with get_connection() as conn:
            _update_platform_state(
                conn,
                platform,
                last_run_at=_now().isoformat(),
                last_action="Error",
                last_error=str(exc),
            )
    finally:
        with get_connection() as conn:
            _update_platform_state(conn, platform, locked_at=None)


def tick() -> None:
    config = init_video_autopilot_state()
    for platform in config["platforms"]:
        _run_for_platform(platform)


def autopilot_status() -> dict[str, Any]:
    config = init_video_autopilot_state()
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM video_autopilot_state").fetchall()
    platforms = [dict(row) for row in rows]
    last_run = None
    last_action = None
    last_error = None
    enabled = any(row.get("enabled", 1) for row in platforms)
    for row in platforms:
        if row.get("last_run_at") and (not last_run or row["last_run_at"] > last_run):
            last_run = row["last_run_at"]
            last_action = row.get("last_action")
            last_error = row.get("last_error")
    return {
        "enabled": enabled,
        "interval_minutes": config["interval_minutes"],
        "last_run_at": last_run,
        "last_run_result": last_action,
        "last_action": last_action,
        "last_error": last_error,
        "platforms": platforms,
    }
