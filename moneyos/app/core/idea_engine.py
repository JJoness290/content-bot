from __future__ import annotations

import json
import logging
import random
import re
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
STRICT_MODE_PROMPT = (
    "You are a TikTok-native creator.\n"
    "Output EXACTLY 8 beats.\n"
    "Follow the format exactly.\n"
    "No explanations.\n"
    "No commentary.\n"
    "No repetition.\n"
    "Fast, casual, human tone."
)

logger = logging.getLogger(__name__)


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


def _split_sentences(text: str) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return [sentence.strip() for sentence in sentences if sentence.strip()]


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", text.lower())


def _beat_has_sentence(text: str) -> bool:
    return any(punct in text for punct in (".", "!", "?"))


def _build_beat(label: str, line: str) -> str:
    return f"{label}\n{line}"


def _validate_script(script: str) -> tuple[bool, list[str]]:
    errors: list[str] = []
    lines = [line for line in script.splitlines() if line.strip()]
    if not lines or not lines[0].startswith("[Beat 1]"):
        errors.append("missing_beat_1")
    if not lines or not lines[-1].startswith("[Beat 8]"):
        errors.append("missing_beat_8")
    beat_lines = [line for line in lines if line.startswith("[Beat ")]
    if len(beat_lines) != 8:
        errors.append("beat_count_invalid")
    expected = [f"[Beat {idx}]" for idx in range(1, 9)]
    if beat_lines != expected:
        errors.append("beat_order_invalid")
    for beat_line in beat_lines:
        beat_index = lines.index(beat_line)
        if beat_index + 1 >= len(lines):
            errors.append("beat_missing_sentence")
            continue
        beat_text = lines[beat_index + 1]
        if not _beat_has_sentence(beat_text):
            errors.append("beat_missing_sentence")
    sentences = []
    for beat_line in beat_lines:
        beat_index = lines.index(beat_line)
        if beat_index + 1 < len(lines):
            sentences.extend(_split_sentences(lines[beat_index + 1]))
    sentence_keys = [sentence.lower().strip() for sentence in sentences]
    if len(sentence_keys) != len(set(sentence_keys)):
        errors.append("duplicate_sentences")
    return len(errors) == 0, errors


def _find_repetition(beats: list[str]) -> set[int]:
    sentence_index: dict[str, set[int]] = {}
    phrase_index: dict[str, set[int]] = {}
    for idx, beat in enumerate(beats):
        beat_text = beat.split("\n", maxsplit=1)[-1]
        for sentence in _split_sentences(beat_text):
            key = sentence.lower().strip()
            sentence_index.setdefault(key, set()).add(idx)
        tokens = _tokenize(beat_text)
        for start in range(len(tokens) - 3):
            phrase = " ".join(tokens[start : start + 4])
            phrase_index.setdefault(phrase, set()).add(idx)
    repeated_indices: set[int] = set()
    for indices in sentence_index.values():
        if len(indices) > 1:
            repeated_indices.update(indices)
    for phrase, indices in phrase_index.items():
        if len(indices) > 1 and len(phrase.split()) >= 4:
            repeated_indices.update(indices)
    return repeated_indices


def _tiktok_beat_pool(topic: str) -> list[list[str]]:
    topic_lower = topic.lower()
    return [
        [
            "Stop, you’re not lazy—your phone is just way too convincing.",
            "Listen, it’s not you, it’s the tiny swipe that runs your whole day.",
            "Quick reality check: your phone isn’t chill, it’s in charge.",
        ],
        [
            "You open one app and suddenly it’s three hours later and dinner’s cold.",
            "One quick check turns into a marathon you never signed up for.",
            "You tap once and time folds like it owes you money.",
        ],
        [
            "The wild part is the tiny bedtime swipe hijacks your morning energy.",
            "That “just one more” before bed quietly steals tomorrow.",
            f"It’s the ritual, not the {topic_lower}, that flips your whole vibe.",
        ],
        [
            "Twist is, you don’t even like what you watched, you just kept moving.",
            "You’re not entertained, you’re just scrolling out of habit.",
            "You’re not having fun, you’re just stuck in the loop.",
        ],
        [
            "That one swipe turns into a loop and your brain calls it “relaxing.”",
            "Your brain calls it relaxing, but it’s really just autopilot.",
            "It feels chill, but it’s just a loop with good lighting.",
        ],
        [
            "Then you wake up tired, blame yourself, and repeat the exact same spiral.",
            "Next morning you’re foggy, annoyed, and right back on the same ride.",
            "You wake up drained, swear you’ll stop, and end up right there again.",
        ],
        [
            "Here’s the punchline: the app isn’t addictive, your autopilot is.",
            "Punchline is, it’s not the app, it’s your autopilot taking over.",
            "The realization: the scroll isn’t the villain, your autopilot is.",
        ],
        [
            "Anyway, I’m deleting it tonight, no speeches, just vibes.",
            "I’m done with it tonight—no big announcement, just peace.",
            "So yeah, I’m off it tonight, no drama, just quiet.",
        ],
    ]


def _build_tiktok_script(topic: str, hook: str) -> list[str]:
    beat_pool = _tiktok_beat_pool(topic)
    beat_lines = [random.choice(pool) for pool in beat_pool]
    beat_lines[0] = hook.rstrip(".!?") + "."
    beats = []
    for idx, line in enumerate(beat_lines, start=1):
        beats.append(_build_beat(f"[Beat {idx}]", line))
    return beats


def _repair_repetition(beats: list[str], topic: str, hook: str) -> list[str]:
    repeated = _find_repetition(beats)
    if not repeated:
        return beats
    pool = _tiktok_beat_pool(topic)
    for idx in sorted(repeated):
        if idx == 0:
            line = hook.rstrip(".!?") + "."
        else:
            line = random.choice(pool[idx])
        beats[idx] = _build_beat(f"[Beat {idx + 1}]", line)
    return beats


def _safe_fallback_script(topic: str) -> list[str]:
    lines = [
        "Okay, quick confession: my phone has me in a chokehold.",
        "I open one app and suddenly it’s an hour later and I’m still in bed.",
        "The sneaky part is the bedtime scroll that wrecks my morning energy.",
        "I’m not even entertained, I’m just stuck on autopilot.",
        "It feels relaxing, but it’s really just a loop dressed up as chill.",
        "Then I wake up tired, blame myself, and do it again like clockwork.",
        "Realization hit: it’s not the app, it’s my routine doing the damage.",
        "So I’m cutting it off tonight, no speech, just peace.",
    ]
    return [_build_beat(f"[Beat {idx}]", line) for idx, line in enumerate(lines, start=1)]


def build_script(idea: dict[str, Any], platform: str) -> str:
    hook = idea["hook"]
    topic = idea["topic"]
    attempts = 0
    beats: list[str] = []
    while attempts < 3:
        attempts += 1
        if platform == "tiktok":
            beats = _build_tiktok_script(topic, hook)
            beats = _repair_repetition(beats, topic, hook)
        else:
            beats = [
                _beat(hook, 10, 12),
                _beat(f"Escalation: {topic} flips your day fast.", 14, 16),
                _beat("New angle: it’s not your schedule, it’s the tiny ritual loop.", 18, 20),
                _beat("Contrast: you blame the big thing, but it’s a tiny trigger instead.", 20, 22),
                _beat("Fresh idea: change the first 30 seconds and the rest obeys.", 22, 24),
                _beat("Bigger twist: your ‘good habit’ is actually the trap door.", 24, 26),
                _beat("Final punch: break it once and the whole vibe resets.", 24, 26),
                _beat("Stop there. No recap. Keep scrolling.", 8, 12),
            ]
            beats = _unique_lines([beat for beat in beats if beat])
        script = "\n".join(beats)
        if platform == "tiktok":
            valid, errors = _validate_script(script)
            if valid:
                return script
            logger.warning("TikTok script validation failed, retrying: %s", errors)
            logger.info("Strict mode prompt applied: %s", STRICT_MODE_PROMPT)
            continue
        return script
    logger.error("TikTok script validation failed after retries, using fallback.")
    beats = _safe_fallback_script(topic)
    return "\n".join(beats)
