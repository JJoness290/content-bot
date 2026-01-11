from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def keyword_search(root: Path, query_terms: list[str], limit: int = 20) -> list[dict[str, Any]]:
    matches = []
    for path in root.rglob("*.py"):
        if ".git" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        score = sum(text.lower().count(term.lower()) for term in query_terms)
        if score:
            matches.append({"file": path.relative_to(root).as_posix(), "score": score})
    matches.sort(key=lambda item: item["score"], reverse=True)
    return matches[:limit]


def write_index(output_dir: Path, items: list[dict[str, Any]]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "retrieval_index.json").write_text(json.dumps(items, indent=2), encoding="utf-8")
