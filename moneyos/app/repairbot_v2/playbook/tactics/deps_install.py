from __future__ import annotations

import re
from typing import Any

from app.repairbot_v2.playbook.base import Tactic, TacticPlan
from app.repairbot_v2.deps import install_packages


class DepsInstall(Tactic):
    id = "deps_install"

    def applies(self, reason_codes: list[str], *args: Any, **kwargs: Any) -> bool:
        return "DEP_MISSING_MODULE" in reason_codes

    def plan(self, failure_bundle: dict[str, Any], **kwargs: Any) -> TacticPlan:
        text = (failure_bundle.get("traceback") or "") + "\n" + (failure_bundle.get("log_excerpt") or "")
        match = re.search(r"No module named '([^']+)'", text)
        module = match.group(1) if match else ""
        return TacticPlan(id=self.id, details={"module": module})

    def apply(self, plan: TacticPlan, patcher: Any, snapshot: Any) -> dict[str, Any]:
        _ = (patcher, snapshot)
        module = plan.details.get("module")
        install_packages([module], snapshot.root)
        return {"installed": module}
