from __future__ import annotations

import logging
from typing import Any

from app.core.scene_planner import estimate_duration

logger = logging.getLogger(__name__)


def _default_beat_pool(topic: str) -> list[str]:
    topic_lower = topic.lower()
    return [
        "You open one app and suddenly time disappears.",
        f"It’s the tiny {topic_lower} habit that flips your whole vibe.",
        "You’re not even entertained, you’re just stuck on autopilot.",
        "The trigger is tiny, but the ripple is loud.",
        "Once you notice it, the loop feels obvious.",
    ]


def auto_repair(acl: dict[str, Any], target_duration: float) -> dict[str, Any]:
    topic = acl.get("topic", acl.get("meta", {}).get("topic", ""))
    beats = acl.get("beats", [])
    if not beats:
        beats = []
    if len(beats) < 3:
        pool = _default_beat_pool(topic)
        filler = [
            {"narration": pool[0], "pacing": "fast", "purpose": "reinforcement"},
            {"narration": pool[1], "pacing": "fast", "purpose": "reinforcement"},
            {"narration": pool[2], "pacing": "fast", "purpose": "reinforcement"},
        ]
        beats = (beats + filler)[:3]
        logger.info("Repair bot appended missing beats.")
    acl["beats"] = beats

    if not acl.get("hook") or not acl["hook"].get("narration"):
        acl["hook"] = {
            "narration": "Quick reality check: your phone is way too convincing.",
            "energy": "high",
        }
        logger.info("Repair bot restored missing hook.")

    if not acl.get("outro") or not acl["outro"].get("narration"):
        acl["outro"] = {
            "narration": "So yeah, I’m cutting it off tonight, no drama, just peace.",
            "cta": "follow",
        }
        logger.info("Repair bot restored missing outro.")

    hook_text = acl.get("hook", {}).get("narration", "").strip()
    beats_text = [beat.get("narration", "").strip() for beat in acl.get("beats", [])]
    outro_text = acl.get("outro", {}).get("narration", "").strip()
    total_estimate = estimate_duration(hook_text, "fast") + sum(
        estimate_duration(text, "medium") for text in beats_text if text
    ) + estimate_duration(outro_text, "medium")
    if total_estimate < target_duration:
        logger.info("Repair bot detected short duration (%.0fs).", total_estimate)

    return acl
