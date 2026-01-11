from __future__ import annotations

import hashlib
import random
from typing import Any


PACE_WPS = {
    "fast": 2.7,
    "medium": 2.4,
    "slow": 2.0,
}


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


def plan_timeline(acl: dict[str, Any]) -> list[dict[str, Any]]:
    rng = _seeded_random(acl)
    target_duration = acl.get("meta", {}).get("target_duration", 60)
    events: list[dict[str, Any]] = []
    current = 0.0

    hook_text = acl.get("hook", {}).get("narration", "").strip()
    hook_duration = estimate_duration(hook_text, "fast")
    events.append({"start": round(current, 2), "type": "hook", "text": hook_text, "duration": hook_duration})
    current += hook_duration

    beats = acl.get("beats", [])
    for beat in beats:
        narration = beat.get("narration", "").strip()
        pacing = beat.get("pacing", "medium")
        duration = estimate_duration(narration, pacing)
        events.append({"start": round(current, 2), "type": "beat", "text": narration, "duration": duration})
        current += duration

    outro = acl.get("outro", {})
    outro_text = outro.get("narration", "").strip()
    outro_pacing = "medium"
    outro_duration = estimate_duration(outro_text, outro_pacing)
    if current + outro_duration < target_duration:
        remaining = target_duration - current
        outro_text = extend_outro_text(outro_text, remaining, outro_pacing, rng)
        outro_duration = estimate_duration(outro_text, outro_pacing)
        outro["narration"] = outro_text
    events.append({"start": round(current, 2), "type": "outro", "text": outro_text, "duration": outro_duration})
    return events
