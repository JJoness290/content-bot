from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter()


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _latest_diff(outputs: Path) -> str:
    diff_dir = outputs / "diffs"
    if not diff_dir.exists():
        return ""
    diffs = sorted(diff_dir.glob("*.patch"))
    return diffs[-1].name if diffs else ""


@router.get("/api/repairbot/status")
def repairbot_status() -> dict[str, Any]:
    root = Path(__file__).resolve().parents[2]
    return _read_json(root / "outputs" / "repairbot_v2" / "last_status.json")


@router.get("/api/repairbot/preflight")
def repairbot_preflight() -> dict[str, Any]:
    root = Path(__file__).resolve().parents[2]
    return _read_json(root / "outputs" / "repairbot_v2" / "preflight_latest.json")


@router.get("/api/repairbot/plan")
def repairbot_plan() -> dict[str, Any]:
    root = Path(__file__).resolve().parents[2]
    return _read_json(root / "outputs" / "repairbot_v2" / "plan_latest.json")


@router.get("/api/repairbot/preview")
def repairbot_preview() -> str:
    root = Path(__file__).resolve().parents[2]
    return _read_text(root / "outputs" / "repairbot_v2" / "preview_latest.md")


@router.get("/api/repairbot/memory")
def repairbot_memory() -> list[dict[str, Any]]:
    root = Path(__file__).resolve().parents[2]
    memory_path = root / "outputs" / "repairbot_v2" / "memory.jsonl"
    if not memory_path.exists():
        return []
    return [json.loads(line) for line in memory_path.read_text(encoding="utf-8").splitlines() if line.strip()]


@router.post("/api/repairbot/run-once")
def repairbot_run_once() -> dict[str, Any]:
    from app.repairbot_v2.agent import run_agent
    root = Path(__file__).resolve().parents[2]
    intent_path = root / "moneyos_intent.yaml"
    intent = {}
    if intent_path.exists():
        import yaml

        intent = yaml.safe_load(intent_path.read_text(encoding="utf-8"))
    outputs = root / "outputs" / "repairbot_v2"
    return run_agent(root, outputs, intent, once=True)


@router.get("/repairbot", response_class=HTMLResponse)
def repairbot_page(request: Request) -> HTMLResponse:
    root = Path(__file__).resolve().parents[2]
    outputs = root / "outputs" / "repairbot_v2"
    status = _read_json(outputs / "last_status.json")
    preflight = _read_text(outputs / "preflight_latest.md")
    plan = _read_text(outputs / "plan_latest.md")
    preview = _read_text(outputs / "preview_latest.md")
    failure_bundle = _read_text(outputs / "last_failure_bundle.json")
    latest_diff = _latest_diff(outputs)
    html = f"""
    <html>
      <head><title>RepairBot v2</title></head>
      <body style='font-family: sans-serif;'>
        <h1>RepairBot v2</h1>
        <h2>Status</h2>
        <pre>{json.dumps(status, indent=2)}</pre>
        <h2>Latest Diff</h2>
        <pre>{latest_diff}</pre>
        <h2>Preflight</h2>
        <pre>{preflight}</pre>
        <h2>Plan</h2>
        <pre>{plan}</pre>
        <h2>Preview</h2>
        <pre>{preview}</pre>
        <h2>Failure Bundle</h2>
        <pre>{failure_bundle}</pre>
        <form method='post' action='/api/repairbot/run-once'>
          <button type='submit'>Run Repair Iteration</button>
        </form>
      </body>
    </html>
    """
    return HTMLResponse(html)
@router.get("/api/repairbot/failure-bundle")
def repairbot_failure_bundle() -> dict[str, Any]:
    root = Path(__file__).resolve().parents[2]
    return _read_json(root / "outputs" / "repairbot_v2" / "last_failure_bundle.json")


@router.get("/api/repairbot/tactics")
def repairbot_tactics() -> list[str]:
    root = Path(__file__).resolve().parents[2]
    rules_path = root / "outputs" / "repairbot_v2" / "playbook_rules.json"
    if not rules_path.exists():
        return []
    rules = json.loads(rules_path.read_text(encoding="utf-8"))
    tactics = []
    for rule in rules:
        tactics.extend(rule.get("preferred_tactics", []))
    return sorted(set(tactics))
