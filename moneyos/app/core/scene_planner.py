from __future__ import annotations

import logging
from typing import Any


PACE_WPS = {
    "fast": 2.7,
    "medium": 2.4,
    "slow": 2.0,
}

logger = logging.getLogger(__name__)
def estimate_duration(text: str, pacing: str) -> float:
    words = text.split()
    wps = PACE_WPS.get(pacing, 2.4)
    return max(1.0, len(words) / wps)


def plan_timeline(acl: dict[str, Any]) -> list[dict[str, Any]]:
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
        text, pacing = phase_map.get(phase_type, ("", "medium"))
        duration = estimate_duration(text, pacing)
        locked = phase_type in {"hook", "explain"}
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

    for event in events:
        if not event.get("locked"):
            event["locked"] = True
            logger.info("[PHASE] %s completed (%.0fs) → locked", event["type"], event["duration"])

    return events
