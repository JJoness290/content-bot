from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


def _rules_path(outputs_dir: Path) -> Path:
    return outputs_dir / "playbook_rules.json"


def load_rules(outputs_dir: Path) -> list[dict[str, Any]]:
    path = _rules_path(outputs_dir)
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def record_success(outputs_dir: Path, fingerprint: dict[str, Any], preferred_tactics: list[str]) -> None:
    rules = load_rules(outputs_dir)
    for rule in rules:
        if rule.get("fingerprint") == fingerprint:
            rule["success_count"] = rule.get("success_count", 0) + 1
            rule["last_success"] = datetime.utcnow().isoformat()
            rule["preferred_tactics"] = preferred_tactics
            break
    else:
        rules.append(
            {
                "fingerprint": fingerprint,
                "preferred_tactics": preferred_tactics,
                "success_count": 1,
                "failure_count": 0,
                "last_success": datetime.utcnow().isoformat(),
            }
        )
    _rules_path(outputs_dir).write_text(json.dumps(rules, indent=2), encoding="utf-8")


def record_failure(outputs_dir: Path, fingerprint: dict[str, Any]) -> None:
    rules = load_rules(outputs_dir)
    for rule in rules:
        if rule.get("fingerprint") == fingerprint:
            rule["failure_count"] = rule.get("failure_count", 0) + 1
            break
    _rules_path(outputs_dir).write_text(json.dumps(rules, indent=2), encoding="utf-8")
