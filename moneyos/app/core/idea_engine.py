from __future__ import annotations

import json
import random
from datetime import datetime
from typing import Any

from app.core.db import get_connection

PLATFORM_TOPICS: dict[str, list[tuple[str, int, str]]] = {
    "tiktok": [
        ("The £5 habit that saves £150/month", 3, "quick win"),
        ("Top 3 AI tools to earn extra income fast", 2, "tool stack"),
        ("Side hustles you can start in 30 minutes", 3, "step-by-step"),
        ("The 50/30/20 budget that actually sticks", 2, "framework"),
        ("Best UK cashback apps in 2025", 2, "buyer guide"),
        ("Life hacks to cut grocery bills in half", 2, "life hack"),
        ("Debt snowball vs avalanche in 60 seconds", 1, "comparison"),
        ("How to negotiate bills and keep the discount", 2, "scripted pitch"),
        ("Avoid these 3 money leaks every payday", 3, "myth-busting"),
        ("Beginner investing mistakes to avoid", 1, "avoidance"),
    ],
    "youtube": [
        ("The fastest way to build an emergency fund", 3, "step-by-step"),
        ("AI tools that save you hours each week", 2, "tool stack"),
        ("The no-stress budget for busy people", 2, "framework"),
        ("How to cut subscriptions without losing value", 2, "life hack"),
        ("Cashback cards that pay for your groceries", 2, "buyer guide"),
        ("Trending money myths to stop believing", 2, "myth-busting"),
        ("The simple side-hustle stack for beginners", 2, "stacked plan"),
        ("Life hacks that reduce monthly bills today", 2, "life hack"),
        ("How to automate saving without thinking", 3, "automation"),
        ("The buyer guide to better money apps", 1, "buyer guide"),
    ],
}
HOOK_POOL = [
    "This one change saved me £300 last month.",
    "Stop doing this if you want to keep more cash.",
    "Here’s the money mistake most people make.",
    "Do this before your next payday.",
    "A 60-second fix to boost your savings.",
]
STYLE_POOL = [
    "fast checklist",
    "myth-busting",
    "step-by-step",
    "buyer guide",
]
HASHTAGS = "#money #personalfinance #sidehustle #budgeting #ai"
CTA_POOL = {
    "tiktok": [
        "Follow for more no-fluff money wins.",
        "Save this and try one step today.",
    ],
    "youtube": [
        "Subscribe for more no-fluff money wins.",
        "Like and subscribe for weekly money plays.",
    ],
}


def _recent_topics(platform: str, limit: int = 12) -> set[str]:
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


def _rotate(pool: list[str], seed: int) -> list[str]:
    if not pool:
        return pool
    offset = seed % len(pool)
    return pool[offset:] + pool[:offset]


def _word_limit(text: str, min_words: int, max_words: int) -> str:
    words = text.split()
    if len(words) < min_words:
        filler = (
            " Keep it simple: track spending, cut one leak, and automate a small transfer each payday."
        )
        while len(words) < min_words:
            text = f"{text} {filler}"
            words = text.split()
    if len(words) > max_words:
        text = " ".join(words[:max_words])
    return text


def decide_next_content(platform: str) -> dict[str, Any]:
    """
    Returns a dict with:
    - topic
    - hook
    - angle
    - cta
    - platform
    """
    now = datetime.utcnow()
    seed = int(now.strftime("%Y%j"))
    pool = PLATFORM_TOPICS.get(platform, [])
    if not pool:
        raise ValueError(f"Unsupported platform: {platform}")
    recent = _recent_topics(platform)

    topics = [(topic, weight, angle) for topic, weight, angle in pool if topic not in recent]
    if not topics:
        topics = pool
    weights = [item[1] for item in topics]
    topic, _, angle = random.choices(topics, weights=weights, k=1)[0]
    hook = _rotate(HOOK_POOL, seed + random.randint(1, 7))[0]
    style = _rotate(STYLE_POOL, seed + random.randint(3, 9))[0]
    cta = random.choice(CTA_POOL.get(platform, ["Follow for more money wins."]))

    return {
        "topic": topic,
        "hook": hook,
        "angle": angle or style,
        "cta": cta,
        "platform": platform,
    }


def build_script(idea: dict[str, Any], platform: str) -> str:
    intro = f"{idea['hook']} Today’s topic: {idea['topic']}."
    body = (
        f"Angle: {idea.get('angle', 'quick win')}. Here’s the quick plan: "
        "1) pick one money win, "
        "2) automate it, "
        "3) review weekly, "
        "4) repeat for 30 days. "
        "Keep your biggest expense visible so you feel the progress."
    )
    script = _word_limit(
        f"{intro} {body} {idea.get('cta', '')}",
        80 if platform == "tiktok" else 120,
        120 if platform == "tiktok" else 180,
    )
    return script
