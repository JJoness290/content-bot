from __future__ import annotations

import threading
from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class ProgressState:
    stage: str
    percent: int
    eta_seconds: int


_lock = threading.Lock()
_progress: dict[str, ProgressState] = {
    "tiktok": ProgressState(stage="idle", percent=0, eta_seconds=0),
    "youtube": ProgressState(stage="idle", percent=0, eta_seconds=0),
}


def update_progress(platform: str, stage: str, percent: int, eta_seconds: int) -> None:
    with _lock:
        _progress[platform] = ProgressState(stage=stage, percent=percent, eta_seconds=eta_seconds)


def get_progress(platform: str) -> dict[str, Any]:
    with _lock:
        state = _progress.get(platform, ProgressState(stage="idle", percent=0, eta_seconds=0))
        return asdict(state)
