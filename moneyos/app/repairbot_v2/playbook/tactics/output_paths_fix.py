from __future__ import annotations

from pathlib import Path
from typing import Any

from app.repairbot_v2.playbook.base import Tactic, TacticPlan


class OutputPathsFix(Tactic):
    id = "output_paths_fix"

    def applies(self, reason_codes: list[str], *args: Any, **kwargs: Any) -> bool:
        return "OUTPUT_PATHS_MISSING" in reason_codes

    def plan(self, **kwargs: Any) -> TacticPlan:
        return TacticPlan(id=self.id, details={})

    def apply(self, plan: TacticPlan, patcher: Any, snapshot: Any) -> dict[str, Any]:
        _ = (plan, patcher)
        outputs = snapshot.root / "outputs"
        outputs.mkdir(parents=True, exist_ok=True)
        return {"created": outputs.as_posix()}
