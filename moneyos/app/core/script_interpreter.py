from __future__ import annotations

from typing import Any


def render_spoken_script(acl: dict[str, Any]) -> str:
    spoken_script = acl.get("spoken_script")
    if isinstance(spoken_script, str) and spoken_script.strip():
        return spoken_script.strip()
    parts: list[str] = []
    hook = acl.get("hook", {}).get("narration", "").strip()
    if hook:
        parts.append(hook)
    for beat in acl.get("beats", []):
        narration = beat.get("narration", "").strip()
        if narration:
            parts.append(narration)
    outro = acl.get("outro", {}).get("narration", "").strip()
    if outro:
        parts.append(outro)
    return " ".join(parts)
