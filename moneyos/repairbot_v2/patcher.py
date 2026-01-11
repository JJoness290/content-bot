from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any


def apply_patch(root: Path, outputs: Path, plan: dict[str, Any]) -> Path:
    _ = plan
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    diff_path = outputs / "diffs" / f"{timestamp}.patch"
    outputs.mkdir(parents=True, exist_ok=True)
    diff_path.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(["git", "diff"], cwd=root, capture_output=True, text=True, check=False)
    diff_path.write_text(result.stdout, encoding="utf-8")
    report_path = outputs / "reports" / f"{timestamp}.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("# Patch Report\n\nNo-op patcher for now.", encoding="utf-8")
    return diff_path
