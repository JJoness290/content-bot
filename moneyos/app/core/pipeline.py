from __future__ import annotations

import logging
from typing import Any

from app.core.creation_language import build_acl
from app.core.repair_bot import auto_repair
from app.core.scene_planner import plan_timeline
from app.core.script_interpreter import render_spoken_script
from app.core.validators import validate_acl

logger = logging.getLogger(__name__)


def generate_render_package(idea: dict[str, Any], platform: str) -> dict[str, Any]:
    acl = build_acl(idea, platform)
    errors = validate_acl(acl)
    repairs = 0
    target_duration = acl.get("meta", {}).get("target_duration", 60)
    while errors and repairs < 3:
        acl = auto_repair(acl, target_duration)
        errors = validate_acl(acl)
        repairs += 1
        logger.info("ACL repair attempt %s complete: %s", repairs, errors)
    if errors:
        logger.warning("ACL validation still failing, continuing with repairs: %s", errors)

    timeline = plan_timeline(acl)
    script = render_spoken_script(acl)
    return {
        "acl": acl,
        "timeline": timeline,
        "script": script,
    }
