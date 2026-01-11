from __future__ import annotations

import hashlib
import logging
import random
from typing import Any


PACE_WPS = {
    "fast": 2.7,
    "medium": 2.4,
    "slow": 2.0,
}

HOOK_PATTERNS = [
    "?",
    "did you know",
    "what if",
    "most people",
    "you won't believe",
    "here's why",
]

logger = logging.getLogger(__name__)


def _seeded_random(acl: dict[str, Any]) -> random.Random:
    seed_src = f"{acl.get('meta', {}).get('platform','')}-{acl.get('hook', {}).get('narration','')}"
    seed = int(hashlib.sha256(seed_src.encode("utf-8")).hexdigest(), 16)
    return random.Random(seed)


def estimate_duration(text: str, pacing: str) -> float:
    words = text.split()
    wps = PACE_WPS.get(pacing, 2.4)
    return max(1.0, len(words) / wps)


def extend_outro_text(text: str, target_seconds: float, pacing: str, rng: random.Random) -> str:
    additions = [
        "I’m swapping the scroll for a two-breath pause.",
        "One tiny reset and the rest of the day feels lighter.",
        "It’s a small switch, but it actually works.",
        "No big overhaul, just a calmer start.",
        "Give it one night and you’ll feel the difference.",
    ]
    extended = text
    idx = 0
    while estimate_duration(extended, pacing) < target_seconds and idx < len(additions):
        extended = f"{extended} {additions[idx]}"
        idx += 1
    return extended


def _contains_hook_language(text: str) -> bool:
    lowered = text.lower()
    return any(pattern in lowered for pattern in HOOK_PATTERNS)


def _regenerate_phase_text(phase_type: str, rng: random.Random) -> str:
    pools = {
        "explain": [
            "It’s the tiny habit that adds up faster than you think.",
            "Once you see the trigger, the rest of the loop makes sense.",
            "The pattern is simple: cue, scroll, repeat, and it drains your energy.",
        ],
        "reinforce": [
            "The fix is small and repeatable, not a big reset.",
            "Swap the first minute and the rest of the day follows.",
            "Keep it simple: change the cue, change the outcome.",
        ],
        "close": [
            "So I’m cutting it off tonight, no drama, just peace.",
            "I’m done with it tonight—quiet reset, no big speech.",
            "That’s it for me tonight, just a calm reset.",
        ],
    }
    options = pools.get(phase_type, [""])
    return rng.choice(options)


def plan_timeline(acl: dict[str, Any]) -> list[dict[str, Any]]:
    rng = _seeded_random(acl)
    target_duration = acl.get("meta", {}).get("target_duration", 60)
    phases = acl.get("phases", [])
    events: list[dict[str, Any]] = []
    current = 0.0

    hook_text = acl.get("hook", {}).get("narration", "").strip()
    beats = acl.get("beats", [])
    explain_beats = beats[: max(1, len(beats) // 2)]
    reinforce_beats = beats[len(explain_beats) :]
    outro_text = acl.get("outro", {}).get("narration", "").strip()

    phase_map = {
        "hook": (hook_text, "fast"),
        "explain": (" ".join(beat.get("narration", "").strip() for beat in explain_beats if beat), "medium"),
        "reinforce": (" ".join(beat.get("narration", "").strip() for beat in reinforce_beats if beat), "medium"),
        "close": (outro_text, "medium"),
    }

    for phase in phases:
        phase_type = phase.get("type")
        target_seconds = phase.get("target_seconds", 0)
        text, pacing = phase_map.get(phase_type, ("", "medium"))
        duration = estimate_duration(text, pacing)
        if phase_type != "hook" and _contains_hook_language(text):
            logger.info("[PHASE] %s rejected — hook language detected", phase_type)
            text = _regenerate_phase_text(phase_type, rng)
            duration = estimate_duration(text, pacing)
            logger.info("[PHASE] %s regenerated successfully", phase_type)
        locked = phase_type in {"hook", "explain"}
        if phase_type in {"reinforce", "close"} and duration < target_seconds:
            target_total = duration + (target_seconds - duration)
            text = extend_outro_text(text, target_total, pacing, rng)
            new_duration = estimate_duration(text, pacing)
            logger.info("[PHASE] %s extended (+%.0fs)", phase_type, new_duration - duration)
            duration = new_duration
        events.append(
            {
                "start": round(current, 2),
                "type": phase_type,
                "text": text,
                "duration": duration,
                "locked": locked,
            }
        )
        current += duration
        if locked:
            logger.info("[PHASE] %s completed (%.0fs) → locked", phase_type, duration)

    total_duration = sum(event["duration"] for event in events)
    remaining = max(0.0, target_duration - total_duration)
    if remaining > 0:
        reinforce_event = next((event for event in events if event["type"] == "reinforce"), None)
        if reinforce_event and not reinforce_event.get("locked") and remaining > 0:
            base_duration = reinforce_event["duration"]
            target_total = base_duration + remaining
            reinforce_text = extend_outro_text(reinforce_event["text"], target_total, "medium", rng)
            reinforce_event["text"] = reinforce_text
            reinforce_event["duration"] = estimate_duration(reinforce_text, "medium")
            logger.info("[PHASE] reinforce extended (+%.0fs)", reinforce_event["duration"] - base_duration)
            remaining = max(0.0, target_duration - sum(event["duration"] for event in events))
        close_event = next((event for event in events if event["type"] == "close"), None)
        if close_event and not close_event.get("locked") and remaining > 0:
            base_duration = close_event["duration"]
            target_total = base_duration + remaining
            close_text = extend_outro_text(close_event["text"], target_total, "medium", rng)
            close_event["text"] = close_text
            close_event["duration"] = estimate_duration(close_text, "medium")
            logger.info("[PHASE] close completed")

    for event in events:
        if not event.get("locked"):
            event["locked"] = True
            logger.info("[PHASE] %s completed (%.0fs) → locked", event["type"], event["duration"])

    return events
