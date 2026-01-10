import asyncio
import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from app.core import audit, notifier
from app.core.asset_strategy import choose_strategy
from app.core.idea_engine import decide_next_content
from app.core.content_generator import (
    extract_keywords,
    generate_autopilot_draft,
    generate_custom_medium_article,
)
from app.core.db import get_connection
from app.core.task_manager import create_task
from app.core.video_pipeline import generate_script
from app.core.video_queue import create_script_item, init_video_queue_db, list_scripts


@dataclass
class AutopilotSettings:
    enabled: bool = True
    drafts_per_week: int = 3
    preferred_days: tuple[int, ...] = (0, 2, 4)  # Mon/Wed/Fri
    preferred_hour: int = 10
    triggers_no_drafts_days: int = 7
    traffic_threshold: float = 50.0
    ctr_threshold: float = 0.015
    max_ready_to_publish: int = 5
    max_drafts: int = 10
    platform_default: str = "medium"


SETTINGS = AutopilotSettings()
JOB_ID = "content_autopilot_tick"
AUTOPILOT_INTERVAL_SECONDS = 60
VIDEO_QUEUE_TARGET = 3
logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.utcnow()


def _start_of_week(now: datetime) -> datetime:
    return now - timedelta(days=now.weekday())


def _load_scheduler_state(conn) -> dict[str, Any]:
    row = conn.execute("SELECT * FROM scheduler_state WHERE id = 1").fetchone()
    if not row:
        conn.execute(
            """
            INSERT INTO scheduler_state (
                id, last_run_at, last_draft_at, drafts_this_week, next_scheduled_draft_at, locked_at,
                enabled, interval_minutes, last_run_result, autopilot_time_local, autopilot_platform,
                autopilot_draft_only, autopilot_topics_json, autopilot_topic_index
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                1,
                None,
                None,
                0,
                None,
                None,
                1,
                15,
                None,
                "09:00",
                "medium",
                1,
                json.dumps(_default_topics()),
                0,
            ),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM scheduler_state WHERE id = 1").fetchone()
    return dict(row)


def _update_scheduler_state(conn, **updates: Any) -> None:
    fields = ", ".join([f"{key} = ?" for key in updates])
    values = list(updates.values())
    values.append(1)
    conn.execute(f"UPDATE scheduler_state SET {fields} WHERE id = ?", values)
    conn.commit()


def get_autopilot_state() -> dict[str, Any]:
    with get_connection() as conn:
        state = _load_scheduler_state(conn)
    return {
        "enabled": bool(state.get("enabled", 1)),
        "interval_minutes": int(state.get("interval_minutes", 15)),
        "last_run_at": state.get("last_run_at"),
        "last_run_result": state.get("last_run_result"),
        "autopilot_time_local": state.get("autopilot_time_local") or "09:00",
        "autopilot_platform": state.get("autopilot_platform") or "medium",
        "autopilot_draft_only": bool(state.get("autopilot_draft_only", 1)),
        "autopilot_topics_json": state.get("autopilot_topics_json"),
        "autopilot_topic_index": int(state.get("autopilot_topic_index", 0)),
    }


def set_autopilot_state(**updates: Any) -> None:
    with get_connection() as conn:
        _update_scheduler_state(conn, **updates)


def _default_topics() -> list[str]:
    return [
        "NordVPN vs Surfshark: Which VPN Is Better in 2026?",
        "Budgeting tips for beginners",
        "Personal finance apps that simplify tracking",
        "Investing basics for cautious starters",
    ]


def _next_topic(state: dict[str, Any]) -> tuple[str, int]:
    topics = state.get("autopilot_topics_json")
    if topics:
        topics_list = json.loads(topics)
    else:
        topics_list = _default_topics()
    index = state.get("autopilot_topic_index", 0) % len(topics_list)
    topic = topics_list[index]
    return topic, (index + 1) % len(topics_list)


def enable_autopilot() -> int:
    interval = get_autopilot_state()["interval_minutes"]
    set_autopilot_state(enabled=1)
    return interval


def disable_autopilot() -> None:
    set_autopilot_state(enabled=0)


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


def _count_assets(conn) -> dict[str, int]:
    counts = {
        "drafts": 0,
        "ready": 0,
        "published": 0,
    }
    rows = conn.execute(
        "SELECT status, COUNT(*) as count FROM assets GROUP BY status"
    ).fetchall()
    for row in rows:
        status = row["status"]
        if status == "DRAFT":
            counts["drafts"] = row["count"]
        elif status == "READY_TO_PUBLISH":
            counts["ready"] = row["count"]
        elif status == "PUBLISHED":
            counts["published"] = row["count"]
    return counts


def _metrics_last_7_days(conn) -> dict[str, float]:
    since = (_now() - timedelta(days=7)).date().isoformat()
    rows = conn.execute(
        """
        SELECT metric_name, SUM(value) as total
        FROM metrics_daily
        WHERE date >= ?
        GROUP BY metric_name
        """,
        (since,),
    ).fetchall()
    totals = {row["metric_name"]: row["total"] or 0 for row in rows}
    views = float(totals.get("views", 0))
    clicks = float(totals.get("clicks", 0))
    impressions = float(totals.get("impressions", 0))
    ctr = clicks / impressions if impressions else 0.0
    baseline = conn.execute(
        """
        SELECT value FROM metrics_daily
        WHERE metric_name = ?
        ORDER BY date DESC
        LIMIT 1
        """,
        ("baseline_revenue",),
    ).fetchone()
    baseline_revenue = float(baseline["value"]) if baseline else 0.0
    return {
        "views": views,
        "clicks": clicks,
        "impressions": impressions,
        "ctr": ctr,
        "baseline_revenue": baseline_revenue,
    }


def _scheduled_due(now: datetime, state: dict[str, Any]) -> bool:
    if now.weekday() not in SETTINGS.preferred_days:
        return False
    if now.hour < SETTINGS.preferred_hour:
        return False
    last_draft_at = state.get("last_draft_at")
    if not last_draft_at:
        return True
    last_date = datetime.fromisoformat(last_draft_at).date()
    return last_date < now.date()


def _next_scheduled_draft_at(now: datetime) -> str:
    for day_offset in range(7):
        candidate = now + timedelta(days=day_offset)
        if candidate.weekday() in SETTINGS.preferred_days:
            scheduled = candidate.replace(
                hour=SETTINGS.preferred_hour, minute=0, second=0, microsecond=0
            )
            if scheduled >= now:
                return scheduled.isoformat()
    fallback = now + timedelta(days=1)
    return fallback.replace(hour=SETTINGS.preferred_hour, minute=0, second=0, microsecond=0).isoformat()


def _draft_reason_list(metrics: dict[str, float], counts: dict[str, int], state: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    last_draft_at = state.get("last_draft_at")
    if counts["published"] <= 1:
        reasons.append("Only 0–1 published assets exist; create a foundational post.")
    if not last_draft_at:
        reasons.append("No draft has been created yet.")
    else:
        last = datetime.fromisoformat(last_draft_at)
        if _now() - last > timedelta(days=SETTINGS.triggers_no_drafts_days):
            reasons.append("No drafts created in the last 7 days.")
    if metrics["views"] < SETTINGS.traffic_threshold:
        reasons.append("7-day views below threshold.")
    if metrics["ctr"] < SETTINGS.ctr_threshold:
        reasons.append("CTR below threshold.")
    if metrics["baseline_revenue"] == 0.0:
        reasons.append("Baseline revenue is £0; maintain daily drafting cadence.")
    return reasons


def decide() -> dict[str, Any]:
    now = _now()
    with get_connection() as conn:
        state = _load_scheduler_state(conn)

    last_draft_at = state.get("last_draft_at")
    if not last_draft_at:
        return {
            "decision": "DRAFT_NOW",
            "reasons": ["No draft exists yet; create the first draft."],
        }

    last = datetime.fromisoformat(last_draft_at)
    if now - last > timedelta(hours=24):
        return {
            "decision": "DRAFT_NOW",
            "reasons": ["No draft created in the last 24 hours."],
        }

    return {
        "decision": "SKIP",
        "reasons": ["Draft already created within the last 24 hours."],
    }


def _generate_asset() -> dict[str, Any]:
    strategy = choose_strategy()
    content = generate_autopilot_draft(
        strategy.topic,
        strategy.angle,
        strategy.keywords,
        strategy.affiliate_placeholders,
    )
    return {
        "title": strategy.topic,
        "content_md": content,
        "metadata": {
            "topic": strategy.topic,
            "angle": strategy.angle,
            "keywords": list(strategy.keywords),
            "intent": strategy.intent,
            "monetization_type": strategy.monetization_type,
            "niche": strategy.niche,
            "affiliate_placeholders": list(strategy.affiliate_placeholders),
        },
    }


def generate_custom_asset(
    topic: str,
    tone: str,
    length: str,
    audience: str,
    platform: str,
    draft_only: bool,
) -> dict[str, Any]:
    keywords = extract_keywords(f"{topic} {audience}")
    placeholders = ("[Primary offer – Official Site]", "[Secondary offer – Official Site]")
    content = generate_custom_medium_article(topic, tone, length, audience, keywords, placeholders)
    status = "DRAFT" if draft_only else "READY_TO_PUBLISH"
    metadata = {
        "topic": topic,
        "tone": tone,
        "length": length,
        "audience": audience,
        "keywords": keywords,
        "intent": "comparison",
        "monetization_type": "affiliate",
        "affiliate_placeholders": list(placeholders),
    }
    return {"title": topic, "content_md": content, "metadata": metadata, "status": status, "platform": platform}


def _insert_asset(asset_payload: dict[str, Any]) -> int:
    now = _now().isoformat()
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO assets (
                uuid, type, platform, title, status, content_md, metadata_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                "blog",
                asset_payload.get("platform", SETTINGS.platform_default),
                asset_payload["title"],
                asset_payload.get("status", "DRAFT"),
                asset_payload["content_md"],
                json.dumps(asset_payload["metadata"]),
                now,
                now,
            ),
        )
        conn.commit()
        return int(cur.lastrowid)


def create_asset_from_payload(asset_payload: dict[str, Any]) -> dict[str, Any]:
    asset_id = _insert_asset(asset_payload)
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM assets WHERE id = ?", (asset_id,)).fetchone()
    return dict(row)


def create_blank_asset() -> dict[str, Any]:
    now = _now().isoformat()
    asset_uuid = str(uuid.uuid4())
    title = "Draft blog post (auto)"
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO assets (
                uuid, type, platform, title, status, content_md, metadata_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                asset_uuid,
                "blog",
                SETTINGS.platform_default,
                title,
                "DRAFT",
                "",
                json.dumps({}),
                now,
                now,
            ),
        )
        conn.commit()
        return {"id": int(cur.lastrowid), "uuid": asset_uuid}


def generate_content_for_asset(asset_id: int) -> dict[str, Any]:
    now = _now().isoformat()
    asset_payload = _generate_asset()
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE assets
            SET title = ?, content_md = ?, metadata_json = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                asset_payload["title"],
                asset_payload["content_md"],
                json.dumps(asset_payload["metadata"]),
                now,
                asset_id,
            ),
        )
        conn.commit()
    return asset_payload


def create_draft(decision: dict[str, Any], asset_payload: dict[str, Any] | None = None) -> int:
    now = _now().isoformat()
    asset = asset_payload or _generate_asset()
    asset["status"] = "DRAFT"
    asset.setdefault("metadata", {})
    asset["metadata"]["generated_at"] = now
    with get_connection() as conn:
        state = _load_scheduler_state(conn)
        drafts_this_week = state.get("drafts_this_week", 0) + 1
        asset_id = _insert_asset(asset)
        _update_scheduler_state(conn, last_draft_at=now, drafts_this_week=drafts_this_week)

    task_id = create_task(
        "Review draft asset",
        "WAITING_ON_YOU",
        "Content",
        {
            "need": "Review the draft asset and decide when to publish.",
            "why": "Publishing is always human-gated to remain in £0 Safe Mode.",
            "risk": "Low",
            "steps": [
                "Open the Assets page in MoneyOS.",
                f"Open asset ID {asset_id} and review the draft.",
                "If ready, publish manually on Medium later.",
                "Do not add affiliate links until approved.",
            ],
            "paste_back": "Confirm review complete or provide edits needed.",
            "next": "We will prepare the publish request card when approved.",
        },
    )

    notifier.add_notification("INFO", f"Draft created (asset #{asset_id}).")
    _enqueue_video_script(asset["title"], asset.get("platform", SETTINGS.platform_default))
    audit.log_action(
        name="content_autopilot_tick",
        action_type="decision",
        metadata={
            "decision": decision,
            "asset_id": asset_id,
            "task_id": task_id,
            "topic": asset["title"],
            "generated_at": now,
        },
        decision="DRAFT_NOW",
        reason="; ".join(decision.get("reasons", [])),
    )
    return asset_id


def _enqueue_video_script(topic: str, platform: str) -> None:
    if platform not in {"tiktok", "youtube"}:
        return
    try:
        init_video_queue_db()
        payload = generate_script(topic, platform)
        create_script_item(platform, topic, payload)
    except Exception as exc:
        logger.warning("Failed to enqueue video script for %s: %s", platform, exc)


def _autonomous_video_tick() -> str:
    choice = decide_next_content()
    platform = choice["platform"]
    backlog = list_scripts(platform)
    if len(backlog) >= VIDEO_QUEUE_TARGET:
        return f"Skipped script enqueue for {platform} (queue size {len(backlog)})."
    _enqueue_video_script(choice["topic"], platform)
    return f"Queued {platform} script: {choice['topic']}"


def tick() -> dict[str, Any]:
    now_dt = _now()
    now = now_dt.isoformat()
    state = get_autopilot_state()
    if not state["enabled"]:
        decision = {"decision": "SKIP", "reasons": ["Autopilot disabled."], "locked": False}
        audit.log_action(
            name="content_autopilot_tick",
            action_type="decision",
            metadata=decision,
            decision="SKIP",
            reason="Autopilot disabled.",
        )
        set_autopilot_state(last_run_at=now, last_run_result="Autopilot disabled.")
        return decision
    with get_connection() as conn:
        state = _load_scheduler_state(conn)
        locked_at = state.get("locked_at")
        if locked_at and now_dt - datetime.fromisoformat(locked_at) < timedelta(minutes=30):
            decision = {"decision": "SKIP", "reasons": ["Autopilot already running."], "locked": True}
            audit.log_action(
                name="content_autopilot_tick",
                action_type="decision",
                metadata=decision,
                decision="SKIP",
                reason="Autopilot already running.",
            )
            return decision

        last_run_at = state.get("last_run_at")
        if not last_run_at or datetime.fromisoformat(last_run_at) < _start_of_week(now_dt):
            _update_scheduler_state(conn, drafts_this_week=0)

        _update_scheduler_state(conn, locked_at=now_dt.isoformat())

    time_local = state.get("autopilot_time_local") or "09:00"
    scheduled_hour, scheduled_minute = map(int, time_local.split(":"))
    now_local = datetime.now()
    today_scheduled = now_local.replace(
        hour=scheduled_hour, minute=scheduled_minute, second=0, microsecond=0
    )
    last_run_at = state.get("last_run_at")
    if last_run_at:
        last_date = datetime.fromisoformat(last_run_at).date()
        if last_date == now_local.date():
            set_autopilot_state(last_run_result="Skipped.", last_run_at=now)
            return {"decision": "SKIP", "reasons": ["Already ran today."]}
    if now_local < today_scheduled:
        set_autopilot_state(last_run_result="Skipped.", last_run_at=now)
        return {"decision": "SKIP", "reasons": ["Waiting for scheduled time."]}

    decision = decide()
    with get_connection() as conn:
        _update_scheduler_state(conn, last_run_at=now, locked_at=None)
        _update_scheduler_state(conn, next_scheduled_draft_at=_next_scheduled_draft_at(now_dt))

    if decision["decision"] == "DRAFT_NOW":
        topic, next_index = _next_topic(state)
        custom = generate_custom_asset(
            topic=topic,
            tone="friendly",
            length="medium",
            audience="UK",
            platform=state.get("autopilot_platform") or SETTINGS.platform_default,
            draft_only=bool(state.get("autopilot_draft_only", 1)),
        )
        asset_id = create_draft(decision, asset_payload=custom)
        set_autopilot_state(autopilot_topic_index=next_index)
        set_autopilot_state(last_run_result="Draft created.", last_run_at=now)
        return decision

    with get_connection() as conn:
        draft_count = conn.execute(
            "SELECT COUNT(*) as count FROM assets WHERE status = ?",
            ("DRAFT",),
        ).fetchone()["count"]
    if draft_count == 0:
        create_draft({"decision": "DRAFT_NOW", "reasons": ["No draft assets exist; creating one."]})
        set_autopilot_state(last_run_result="Draft created.", last_run_at=now)
        return {"decision": "DRAFT_NOW", "reasons": ["No draft assets exist; creating one."]}

    if "Backlog" in " ".join(decision.get("reasons", [])):
        notifier.add_notification("WARNING", "Content autopilot skipped due to backlog limits.")

    audit.log_action(
        name="content_autopilot_tick",
        action_type="decision",
        metadata=decision,
        decision=decision["decision"],
        reason="; ".join(decision.get("reasons", [])),
    )
    set_autopilot_state(last_run_result="Skipped.", last_run_at=now)
    return decision


def autopilot_status() -> dict[str, Any]:
    state = get_autopilot_state()
    last_run = state.get("last_run_at")
    stale = True
    if last_run:
        last_dt = datetime.fromisoformat(last_run)
        stale = _now() - last_dt > timedelta(minutes=state["interval_minutes"] * 2)
    return {
        "last_run_at": last_run,
        "stale": stale,
        "settings": SETTINGS,
        "enabled": state["enabled"],
        "interval_minutes": state["interval_minutes"],
        "last_run_result": state["last_run_result"],
    }


async def autopilot_loop(stop_event: asyncio.Event, interval_seconds: int = AUTOPILOT_INTERVAL_SECONDS) -> None:
    logger.info("Content autopilot loop started (interval=%ss).", interval_seconds)
    while not stop_event.is_set():
        state = get_autopilot_state()
        if state["enabled"]:
            result = await asyncio.to_thread(tick)
            logger.info("Content autopilot tick: %s", result.get("decision"))
            enqueue_result = await asyncio.to_thread(_autonomous_video_tick)
            logger.info("Content autopilot video: %s", enqueue_result)
        else:
            logger.info("Content autopilot disabled; skipping tick.")
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval_seconds)
        except asyncio.TimeoutError:
            continue
