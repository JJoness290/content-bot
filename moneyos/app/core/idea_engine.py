from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from app.core.db import get_connection

PLATFORM_TOPICS: dict[str, list[str]] = {
    "tiktok": [
        "The £5 habit that saves £150/month",
        "Top 3 AI tools to earn extra income fast",
        "Side hustles you can start in 30 minutes",
        "The 50/30/20 budget that actually sticks",
        "Best UK cashback apps in 2025",
        "Life hacks to cut grocery bills in half",
        "Debt snowball vs avalanche in 60 seconds",
        "How to negotiate bills and keep the discount",
        "Avoid these 3 money leaks every payday",
        "Beginner investing mistakes to avoid",
    ],
    "youtube": [
        "The fastest way to build an emergency fund",
        "AI tools that save you hours each week",
        "The no-stress budget for busy people",
        "How to cut subscriptions without losing value",
        "Cashback cards that pay for your groceries",
        "Trending money myths to stop believing",
        "The simple side-hustle stack for beginners",
        "Life hacks that reduce monthly bills today",
        "How to automate saving without thinking",
        "The buyer guide to better money apps",
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
    - script
    - voice_text
    """
    now = datetime.utcnow()
    seed = int(now.strftime("%Y%j"))
    pool = PLATFORM_TOPICS.get(platform, [])
    if not pool:
        raise ValueError(f"Unsupported platform: {platform}")
    recent = _recent_topics(platform)

    topics = _rotate(pool, seed)
    topic = next((item for item in topics if item not in recent), topics[0])
    hook = _rotate(HOOK_POOL, seed + 3)[0]
    style = _rotate(STYLE_POOL, seed + 7)[0]

    intro = f"{hook} Today’s topic: {topic}."
    body = (
        f"Style: {style}. Here’s the quick plan: "
        "1) Pick one money win, "
        "2) automate it, "
        "3) review weekly, "
        "4) repeat for 30 days. "
        "Keep your biggest expense visible so you feel the progress."
    )
    cta = "Follow for more no-fluff money wins."
    script = _word_limit(f"{intro} {body} {cta}", 80 if platform == "tiktok" else 120, 120 if platform == "tiktok" else 180)
    voice_text = script

    return {
        "topic": topic,
        "hook": hook,
        "script": script,
        "voice_text": voice_text,
        "style": style,
        "hashtags": HASHTAGS,
    }
