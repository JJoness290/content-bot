from __future__ import annotations

import json
import random
from datetime import datetime
from typing import Any

from app.core.db import get_connection

PLATFORM_TOPICS: dict[str, list[tuple[str, int, str]]] = {
    "tiktok": [
        ("Everyone fakes productivity before 10am", 3, "hot take"),
        ("Why your group chat is a full-time job", 2, "relatable chaos"),
        ("The phone battery ritual we all do", 2, "relatable confession"),
        ("If you do this at 2am, you’re not okay", 2, "bold statement"),
        ("The main character habits that are actually cringe", 2, "opinion"),
        ("This is why your to-do list hates you", 2, "rant"),
        ("The secret war between you and your alarm", 3, "relatable"),
        ("Your ‘little treat’ era is out of control", 2, "chaos"),
        ("Nobody talks about the gym mirror economy", 1, "funny observation"),
        ("The fake ‘soft life’ checklist we all lie about", 2, "relatable"),
    ],
    "youtube": [
        ("Why everyone pretends to love waking up early", 2, "hot take"),
        ("The daily routines that quietly waste your time", 2, "relatable"),
        ("The unspoken rules of group chats", 2, "funny observation"),
        ("Why your brain hates your to-do list", 1, "rant"),
        ("The tiny habits that feel illegal but work", 2, "curiosity"),
        ("What ‘being productive’ actually looks like", 1, "story"),
        ("The weird habits we all pretend are normal", 2, "relatable"),
        ("Why your phone runs your life now", 2, "bold statement"),
        ("Small chaos that makes mornings impossible", 2, "relatable"),
        ("The little lies in your daily routine", 1, "confession"),
    ],
}
HOOK_POOL = [
    "You’re doing this every day and it’s wild.",
    "Nobody tells you this part out loud.",
    "This is why you feel behind all the time.",
    "Real talk: this is embarrassing for all of us.",
    "If you do this, you’re in the club.",
]
STYLE_POOL = [
    "rant",
    "relatable confession",
    "hot take",
    "funny observation",
]
HASHTAGS = "#tiktok #relatable #dailychaos #fyp #storytime"
CTA_POOL = {
    "tiktok": [
        "Follow for more chaos like this.",
        "Comment if this is literally you.",
    ],
    "youtube": [
        "Subscribe for more chaos like this.",
        "Drop a comment if you relate.",
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


def _count_words(text: str) -> int:
    return len(text.split())


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
    cta = random.choice(CTA_POOL.get(platform, ["Follow for more chaos."]))

    return {
        "topic": topic,
        "hook": hook,
        "angle": angle or style,
        "cta": cta,
        "platform": platform,
    }


def _unique_lines(lines: list[str]) -> list[str]:
    seen = set()
    result = []
    for line in lines:
        key = line.lower().strip()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(line)
    return result


def _beat(text: str, min_words: int, max_words: int) -> str:
    words = text.split()
    if len(words) < min_words:
        return ""
    if len(words) > max_words:
        return " ".join(words[:max_words])
    return text


def build_script(idea: dict[str, Any], platform: str) -> str:
    beats = [
        "[Beat 1]\nStop, you’re not lazy, your phone is just way too convincing.",
        "[Beat 2]\nYou open one app, suddenly it’s three hours later and dinner’s cold.",
        "[Beat 3]\nThe wild part is the tiny swipe you do before bed controls your whole morning.",
        "[Beat 4]\nTwist is, you don’t even like what you watched, you just kept moving.",
        "[Beat 5]\nThat one swipe turns into a loop and your brain calls it “relaxing.”",
        "[Beat 6]\nThen you wake up tired, blame yourself, and repeat the exact same scroll spiral.",
        "[Beat 7]\nHere’s the punchline: the app isn’t addictive, your autopilot is.",
        "[Beat 8]\nAnyway, I’m deleting it tonight, no speeches, just vibes.",
    ]
    beats = _unique_lines(beats)
    script = "\n".join(beats)
    word_count = _count_words(script)
    if platform == "tiktok" and (word_count < 90 or word_count > 110 or len(beats) != 8):
        raise RuntimeError("script_beats_invalid")
    return script
