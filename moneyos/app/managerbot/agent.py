from __future__ import annotations

import json
from pathlib import Path

from app.managerbot.memory import append_memory
from app.managerbot.policy import choose_task
from app.managerbot.router import ai_choose_task
from app.managerbot.state import SystemState, save_state
from app.managerbot.tasks import Task, write_task
from app.repairbot_v2.preflight import run_preflight
from app.repairbot_v2.verify import working_order
from app.repairbot_v2.agent import run_agent


def run_manager(root: Path, outputs: Path, mode: str = "once") -> dict[str, object]:
    tasks_dir = outputs / "tasks"
    memory_path = outputs / "memory.jsonl"
    state_path = outputs / "state.json"
    loop = True
    while loop:
        preflight = run_preflight(root, root / "outputs" / "repairbot_v2")
        ok, reasons = working_order(root, root / "outputs" / "repairbot_v2")
        state = {"ok": ok, "reasons": reasons, "preflight": preflight}
        task_kind = choose_task(state)
        if not task_kind:
            task_kind = ai_choose_task(state)
        task = Task(id=str(len(list(tasks_dir.glob("*.json"))) + 1), kind=task_kind, status="pending", acceptance=[])
        if task_kind == "REPAIR":
            result = run_agent(root, root / "outputs" / "repairbot_v2", {}, once=True)
            task.status = "done"
            task.result = result
        elif task_kind == "VERIFY":
            task.status = "done"
            task.result = {"ok": ok, "reasons": reasons}
        else:
            task.status = "skipped"
            task.result = {"note": "generation not wired"}
        write_task(tasks_dir / f"{task.id}.json", task)
        save_state(state_path, SystemState(status="ok" if ok else "error", last_reasons=reasons, last_task=task_kind))
        append_memory(memory_path, {"task": task_kind, "result": task.result})
        if mode == "once":
            loop = False
        if ok:
            loop = False
    return {"ok": ok, "reasons": reasons}
