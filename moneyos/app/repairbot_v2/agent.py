from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.repairbot_v2.failure_classifier import classify_failure, write_failure_bundle
from app.repairbot_v2.memory import append_memory, update_tactic_scores, read_recent
from app.repairbot_v2.planner import build_plan
from app.repairbot_v2.preflight import run_preflight
from app.repairbot_v2.snapshot import ensure_baseline, pre_attempt_snapshot, rollback_to_baseline
from app.repairbot_v2.patcher import apply_patch
from app.repairbot_v2.verify import working_order
from app.repairbot_v2.playbook.registry import choose_tactics
from app.repairbot_v2.playbook.rules_store import record_success, record_failure


def run_agent(root: Path, outputs: Path, intent: dict[str, Any], once: bool = False) -> dict[str, Any]:
    ensure_baseline(root, outputs)
    while True:
        preflight = run_preflight(root, outputs)
        ok, reasons = working_order(root, outputs)
        if ok:
            status = {"ok": True, "reasons": []}
            (outputs / "last_status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
            return status
        failure_bundle = write_failure_bundle(
            outputs,
            classify_failure("", "", reasons),
            "",
            "",
            [],
        )
        failure_payload = json.loads(failure_bundle.read_text(encoding="utf-8"))
        memory = read_recent(outputs / "memory.jsonl")
        tactics = choose_tactics(
            failure_payload.get("reason_codes", []),
            failure_payload,
            intent,
            preflight,
            memory,
            outputs,
        )
        applied = False
        for tactic in tactics:
            pre_attempt_snapshot(root, outputs)
            plan = tactic.plan(failure_bundle=failure_payload, intent=intent, repo_map=preflight, memory=memory)
            tactic.apply(plan, patcher=apply_patch, snapshot=type("Snapshot", (), {"root": root}))
            ok_after, reasons_after = working_order(root, outputs)
            append_memory(outputs / "memory.jsonl", {
                "tactic": tactic.id,
                "plan": plan.details,
                "reasons": reasons_after if reasons_after else reasons,
            })
            update_tactic_scores(outputs / "tactic_scores.json", [tactic.id], ok_after)
            if ok_after:
                record_success(outputs, {"reason_codes": failure_payload.get("reason_codes", [])}, [tactic.id])
                return {"ok": True, "reasons": []}
            record_failure(outputs, {"reason_codes": failure_payload.get("reason_codes", [])})
            rollback_to_baseline(root, outputs)
            applied = True
            if once:
                return {"ok": False, "reasons": reasons_after or reasons}
        if not applied:
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
                record_success(outputs, {"reason_codes": failure_payload.get("reason_codes", [])}, plan.get("tactics", []))
                return {"ok": True, "reasons": []}
            record_failure(outputs, {"reason_codes": failure_payload.get("reason_codes", [])})
            rollback_to_baseline(root, outputs)
            if once:
                return {"ok": False, "reasons": reasons_after or reasons}
