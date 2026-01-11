from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path


def _git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, check=False, capture_output=True, text=True)


def ensure_baseline(root: Path, outputs: Path) -> str:
    if not (root / ".git").exists():
        _git(["init"], root)
    _git(["add", "-A"], root)
    _git(["commit", "-m", "repairbot baseline", "--allow-empty"], root)
    commit = _git(["rev-parse", "HEAD"], root).stdout.strip()
    outputs.mkdir(parents=True, exist_ok=True)
    (outputs / "baseline_commit.txt").write_text(commit, encoding="utf-8")
    return commit


def pre_attempt_snapshot(root: Path, outputs: Path) -> str:
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    _git(["add", "-A"], root)
    _git(["commit", "-m", f"repairbot pre-attempt {timestamp}", "--allow-empty"], root)
    commit = _git(["rev-parse", "HEAD"], root).stdout.strip()
    snapshot_dir = outputs / "snapshots"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    archive_path = snapshot_dir / f"repo_{timestamp}.zip"
    _zip_repo(root, archive_path)
    return commit


def _zip_repo(root: Path, archive_path: Path) -> None:
    import zipfile

    excluded = {".git", "venv", "__pycache__", "outputs"}
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zipf:
        for path in root.rglob("*"):
            if any(part in excluded for part in path.parts):
                continue
            if path.is_dir():
                continue
            rel = path.relative_to(root).as_posix()
            zipf.write(path, rel)


def rollback_to_baseline(root: Path, outputs: Path) -> None:
    baseline = (outputs / "baseline_commit.txt").read_text(encoding="utf-8").strip()
    _git(["reset", "--hard", baseline], root)
    report = {
        "rollback": True,
        "baseline": baseline,
    }
    reports = outputs / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    report_path = reports / f"rollback_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.md"
    report_path.write_text("\n".join(["# Rollback", json.dumps(report, indent=2)]), encoding="utf-8")
