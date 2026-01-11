from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from moneyos.repairbot_v2.memory import append_memory, update_tactic_scores
from moneyos.repairbot_v2.planner import build_plan
from moneyos.repairbot_v2.preflight import run_preflight
from moneyos.repairbot_v2.snapshot import ensure_baseline, pre_attempt_snapshot, rollback_to_baseline
from moneyos.repairbot_v2.patcher import apply_patch
from moneyos.repairbot_v2.verify import working_order


def run_agent(root: Path, outputs: Path, intent: dict[str, Any], once: bool = False) -> dict[str, Any]:
    ensure_baseline(root, outputs)
    while True:
        preflight = run_preflight(root, outputs)
        ok, reasons = working_order(root, outputs)
        if ok:
            status = {"ok": True, "reasons": []}
            (outputs / "last_status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
            return status
        plan = build_plan(intent, preflight, outputs)
        pre_attempt_snapshot(root, outputs)
        apply_patch(root, outputs, plan)
        ok_after, reasons_after = working_order(root, outputs)
        append_memory(outputs / "memory.jsonl", {
            "plan": plan,
            "reasons": reasons_after if reasons_after else reasons,
        })
        update_tactic_scores(outputs / "tactic_scores.json", plan.get("tactics", []), ok_after)
        if ok_after:
            return {"ok": True, "reasons": []}
        rollback_to_baseline(root, outputs)
        if once:
            return {"ok": False, "reasons": reasons_after or reasons}
