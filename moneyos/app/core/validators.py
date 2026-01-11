from __future__ import annotations

from typing import Any


def validate_acl(acl: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(acl, dict):
        return ["acl_not_dict"]
    meta = acl.get("meta", {})
    if not isinstance(meta, dict):
        errors.append("meta_missing")
    hook = acl.get("hook", {})
    if not isinstance(hook, dict) or not hook.get("narration"):
        errors.append("hook_missing")
    beats = acl.get("beats", [])
    if not isinstance(beats, list):
        errors.append("beats_missing")
    else:
        for beat in beats:
            narration = beat.get("narration") if isinstance(beat, dict) else None
            if not narration:
                errors.append("beat_empty")
                break
    outro = acl.get("outro", {})
    if not isinstance(outro, dict) or not outro.get("narration"):
        errors.append("outro_missing")
    return errors
