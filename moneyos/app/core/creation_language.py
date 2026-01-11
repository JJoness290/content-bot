from __future__ import annotations

import hashlib
import random
from typing import Any


def _seeded_random(idea: dict[str, Any]) -> random.Random:
    seed_src = f"{idea.get('topic','')}-{idea.get('hook','')}-{idea.get('platform','')}"
    seed = int(hashlib.sha256(seed_src.encode("utf-8")).hexdigest(), 16)
    return random.Random(seed)


def build_acl(idea: dict[str, Any], platform: str) -> dict[str, Any]:
    rng = _seeded_random(idea)
    topic = idea.get("topic", "")
    hook = idea.get("hook", "")
    tone = "upbeat"
    pacing = "fast"
    beat_pool = [
        "You open your phone for one tiny thing and suddenly time just disappears.",
        "It feels relaxing, but it’s really just a loop with good lighting.",
        "That little habit is loud enough to mess with the rest of your day.",
        "You’re not even enjoying it, you’re just stuck on autopilot.",
        f"It’s the routine around {topic.lower()} that quietly runs the show.",
        "The funny part is how small the trigger is compared to the damage.",
        "Once you spot the trigger, the whole loop looks obvious.",
        "You don’t need a big reset, just a tiny switch at the start.",
    ]
    outro_pool = [
        "So yeah, I’m cutting it off tonight, no drama, just peace.",
        "I’m done with it tonight—no big announcement, just quiet.",
        "Anyway, I’m out tonight, no speech, just vibes.",
    ]
    beats = []
    for idx in range(5):
        narration = beat_pool[idx % len(beat_pool)]
        beats.append(
            {
                "narration": narration,
                "pacing": rng.choice(["fast", "medium", "fast"]),
                "purpose": rng.choice(["explanation", "reinforcement", "climax"]),
            }
        )
    outro = {
        "narration": rng.choice(outro_pool),
        "cta": "follow" if platform == "tiktok" else "comment",
    }
    return {
        "meta": {
            "platform": platform,
            "target_duration": 60,
            "tone": tone,
            "pacing": pacing,
            "topic": topic,
        },
        "hook": {
            "narration": hook or "Quick reality check: your phone is way too convincing.",
            "energy": "high",
        },
        "beats": beats,
        "outro": outro,
    }
