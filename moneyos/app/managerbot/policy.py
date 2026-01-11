from __future__ import annotations

from typing import Any


def choose_task(state: dict[str, Any]) -> str:
    reasons = state.get("reasons", [])
    if "autopilot_status_unavailable" in reasons or "route_import_error" in reasons:
        return "REPAIR"
    if reasons:
        return "REPAIR"
    return "GENERATE_TIKTOK"
