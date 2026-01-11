from __future__ import annotations

from pathlib import Path
from typing import Any

from moneyos.repairbot_v2.preflight import run_preflight


def collect_signals(root: Path, outputs: Path) -> dict[str, Any]:
    preflight = run_preflight(root, outputs)
    return {
        "preflight": preflight,
    }
