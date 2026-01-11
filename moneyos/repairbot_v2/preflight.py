from __future__ import annotations

import json
from pathlib import Path

from moneyos.repairbot_v2.repo_map import build_repo_map

HOOK_LINES = [
    "Nobody talks about this but it works.",
    "Wait for it, this part is wild.",
    "Here's the trick most people miss.",
    "Bet you didn't know this rule.",
    "One tiny switch changes everything.",
]

SRT_MARKERS = ["00:00:", "-->"]


def run_preflight(root: Path, outputs: Path) -> dict[str, object]:
    repo_index = outputs / "repo_index"
    repo_map_path = build_repo_map(root, repo_index)
    text_hits = []
    for line in HOOK_LINES:
        matches = list(root.rglob("*.py"))
        for path in matches:
            if ".git" in path.parts:
                continue
            if line in path.read_text(encoding="utf-8", errors="ignore"):
                text_hits.append({"file": path.relative_to(root).as_posix(), "line": line})
    srt_hits = []
    for path in root.rglob("*.py"):
        if ".git" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if any(marker in text for marker in SRT_MARKERS):
            srt_hits.append(path.relative_to(root).as_posix())
    report = {
        "repo_map": repo_map_path.as_posix(),
        "hook_filler_hits": text_hits,
        "srt_marker_files": srt_hits,
    }
    outputs.mkdir(parents=True, exist_ok=True)
    (outputs / "preflight_latest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (outputs / "preflight_latest.md").write_text(
        "# Preflight\n\n" + json.dumps(report, indent=2),
        encoding="utf-8",
    )
    return report
