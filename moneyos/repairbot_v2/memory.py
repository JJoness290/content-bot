from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


def append_memory(memory_path: Path, entry: dict[str, Any]) -> None:
    entry = {"timestamp": datetime.utcnow().isoformat(), **entry}
    memory_path.parent.mkdir(parents=True, exist_ok=True)
    with memory_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry) + "\n")


def read_recent(memory_path: Path, limit: int = 20) -> list[dict[str, Any]]:
    if not memory_path.exists():
        return []
    lines = memory_path.read_text(encoding="utf-8").splitlines()[-limit:]
    return [json.loads(line) for line in lines if line.strip()]


def update_tactic_scores(scores_path: Path, tactics: list[str], success: bool) -> None:
    scores: dict[str, dict[str, int]] = {}
    if scores_path.exists():
        scores = json.loads(scores_path.read_text(encoding="utf-8"))
    for tactic in tactics:
        scores.setdefault(tactic, {"success": 0, "failure": 0})
        if success:
            scores[tactic]["success"] += 1
        else:
            scores[tactic]["failure"] += 1
    scores_path.write_text(json.dumps(scores, indent=2), encoding="utf-8")
