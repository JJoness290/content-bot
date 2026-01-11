from __future__ import annotations

import hashlib
import logging
import random
from typing import Any

from app.core.scene_planner import estimate_duration, extend_outro_text

logger = logging.getLogger(__name__)


def _seeded_random(acl: dict[str, Any]) -> random.Random:
    seed_src = f"{acl.get('meta', {}).get('platform','')}-{acl.get('hook', {}).get('narration','')}"
    seed = int(hashlib.sha256(seed_src.encode("utf-8")).hexdigest(), 16)
    return random.Random(seed)


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
    rng = _seeded_random(acl)
    topic = acl.get("topic", acl.get("meta", {}).get("topic", ""))
    beats = acl.get("beats", [])
    if not beats:
        beats = []
    if len(beats) < 3:
        pool = _default_beat_pool(topic)
        while len(beats) < 3:
            beats.append(
                {
                    "narration": pool[len(beats) % len(pool)],
                    "pacing": "fast",
                    "purpose": "reinforcement",
                }
            )
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
    outro = acl.get("outro", {})
    outro_text = outro.get("narration", "").strip()
    outro_pacing = "medium"
    total_estimate = estimate_duration(hook_text, "fast") + sum(
        estimate_duration(text, "medium") for text in beats_text if text
    ) + estimate_duration(outro_text, outro_pacing)
    if total_estimate < target_duration:
        remaining = target_duration - total_estimate
        outro["narration"] = extend_outro_text(outro_text, remaining, outro_pacing, rng)
        acl["outro"] = outro
        logger.info("Repair bot extended outro to hit duration.")

    return acl
