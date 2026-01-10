from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from app.core.db import get_connection

PLATFORMS = ["tiktok", "youtube"]
TOPIC_POOL = [
    "Budgeting apps that save you money fast",
    "Side hustles that pay weekly in the UK",
    "How to cut subscriptions without losing value",
    "Best cash-back cards for everyday spend",
    "The 50/30/20 budget explained simply",
    "Emergency fund steps that work on low income",
    "Money habits that compound faster than interest",
    "Debt snowball vs avalanche: which clears faster",
    "Avoid these three money leaks every month",
    "Smart grocery swaps that cut your bill in half",
    "How to negotiate bills in under 10 minutes",
    "Passive income myths that cost you money",
]
HOOK_POOL = [
    "This one change saved me £300 this month.",
    "Stop doing this if you want to keep more cash.",
    "Here’s the money mistake most people make.",
    "Do this before your next payday.",
]
STYLE_POOL = [
    "fast checklist",
    "myth-busting",
    "step-by-step",
    "buyer guide",
]


def _recent_topics(platform: str, limit: int = 10) -> set[str]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT payload_json
            FROM content_queue
            WHERE platform = ? AND kind = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (platform, "SCRIPT", limit),
        ).fetchall()
    topics: set[str] = set()
    for row in rows:
        try:
            payload = json.loads(row["payload_json"] or "{}")
        except json.JSONDecodeError:
            payload = {}
        topic = payload.get("topic")
        if topic:
            topics.add(topic)
    return topics


def _rotate_pool(pool: list[str], seed: int) -> list[str]:
    if not pool:
        return pool
    offset = seed % len(pool)
    return pool[offset:] + pool[:offset]


def decide_next_content(platform: str | None = None) -> dict[str, Any]:
    now = datetime.utcnow()
    seed = int(now.strftime("%Y%j"))
    chosen_platform = platform or PLATFORMS[seed % len(PLATFORMS)]
    recent = _recent_topics(chosen_platform)

    rotated_topics = _rotate_pool(TOPIC_POOL, seed)
    topic = next((item for item in rotated_topics if item not in recent), rotated_topics[0])
    hook = _rotate_pool(HOOK_POOL, seed + 3)[0]
    style = _rotate_pool(STYLE_POOL, seed + 7)[0]

    return {
        "platform": chosen_platform,
        "topic": topic,
        "hook": hook,
        "style": style,
    }
