from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


def append_memory(path: Path, entry: dict[str, Any]) -> None:
    entry = {"timestamp": datetime.utcnow().isoformat(), **entry}
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry) + "\n")
