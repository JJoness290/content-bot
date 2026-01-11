from __future__ import annotations

from typing import Any

from app.repairbot_v2.playbook.base import Tactic, TacticPlan


class FfmpegFix(Tactic):
    id = "ffmpeg_fix"

    def applies(self, reason_codes: list[str], *args: Any, **kwargs: Any) -> bool:
        return "FFMPEG_MISSING" in reason_codes

    def plan(self, **kwargs: Any) -> TacticPlan:
        return TacticPlan(id=self.id, details={})

    def apply(self, plan: TacticPlan, patcher: Any, snapshot: Any) -> dict[str, Any]:
        _ = (plan, patcher, snapshot)
        return {"note": "ffmpeg required"}
