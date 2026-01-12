from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


@dataclass
class SystemState:
    status: str
    last_reasons: list[str]
    last_task: str | None


def load_state(path: Path) -> SystemState:
    if not path.exists():
        return SystemState(status="unknown", last_reasons=[], last_task=None)
    data = json.loads(path.read_text(encoding="utf-8"))
    return SystemState(**data)


def save_state(path: Path, state: SystemState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(state), indent=2), encoding="utf-8")
