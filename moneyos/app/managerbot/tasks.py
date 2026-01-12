from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


@dataclass
class Task:
    id: str
    kind: str
    status: str
    acceptance: list[str]
    result: dict[str, Any] | None = None


def write_task(path: Path, task: Task) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(task), indent=2), encoding="utf-8")


def read_tasks(path: Path) -> list[Task]:
    if not path.exists():
        return []
    tasks = []
    for file in path.glob("*.json"):
        data = json.loads(file.read_text(encoding="utf-8"))
        tasks.append(Task(**data))
    return tasks
