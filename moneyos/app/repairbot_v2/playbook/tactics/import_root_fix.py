from __future__ import annotations

from pathlib import Path
from typing import Any

from app.repairbot_v2.playbook.base import Tactic, TacticPlan


class ImportRootFix(Tactic):
    id = "import_root_fix"

    def applies(self, reason_codes: list[str], *args: Any, **kwargs: Any) -> bool:
        return "IMPORT_ROOT_MISMATCH" in reason_codes or "ROUTE_IMPORT_ERROR" in reason_codes

    def plan(self, **kwargs: Any) -> TacticPlan:
        return TacticPlan(id=self.id, details={})

    def apply(self, plan: TacticPlan, patcher: Any, snapshot: Any) -> dict[str, Any]:
        _ = (plan, patcher)
        root: Path = snapshot.root
        for path in root.rglob("*.py"):
            if ".git" in path.parts or "outputs" in path.parts:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            updated = text.replace("from moneyos.", "from app.").replace("import moneyos.", "import app.")
            if updated != text:
                path.write_text(updated, encoding="utf-8")
        return {"updated": True}
