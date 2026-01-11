from __future__ import annotations

from typing import Any

from app.repairbot_v2.playbook.base import Tactic, TacticPlan


class ScriptExpand(Tactic):
    id = "script_expand"

    def applies(self, reason_codes: list[str], *args: Any, **kwargs: Any) -> bool:
        return "SCRIPT_TOO_SHORT" in reason_codes

    def plan(self, **kwargs: Any) -> TacticPlan:
        return TacticPlan(id=self.id, details={"min_words": 220})

    def apply(self, plan: TacticPlan, patcher: Any, snapshot: Any) -> dict[str, Any]:
        _ = (patcher, snapshot)
        return {"note": "expand scripted phases by content length"}
