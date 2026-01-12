from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


@router.get("/api/manager/state")
def manager_state() -> dict[str, Any]:
    root = Path(__file__).resolve().parents[2]
    return _read_json(root / "outputs" / "managerbot" / "state.json")


@router.get("/api/manager/tasks")
def manager_tasks() -> list[dict[str, Any]]:
    root = Path(__file__).resolve().parents[2]
    tasks_dir = root / "outputs" / "managerbot" / "tasks"
    if not tasks_dir.exists():
        return []
    return [json.loads(path.read_text(encoding="utf-8")) for path in tasks_dir.glob("*.json")]


@router.get("/api/manager/tasks/{task_id}")
def manager_task(task_id: str) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[2]
    task_path = root / "outputs" / "managerbot" / "tasks" / f"{task_id}.json"
    return _read_json(task_path)


@router.post("/api/manager/run-once")
def manager_run_once() -> dict[str, Any]:
    from app.managerbot.agent import run_manager

    root = Path(__file__).resolve().parents[2]
    outputs = root / "outputs" / "managerbot"
    return run_manager(root, outputs, mode="once")


@router.get("/manager", response_class=HTMLResponse)
def manager_page() -> HTMLResponse:
    root = Path(__file__).resolve().parents[2]
    outputs = root / "outputs" / "managerbot"
    state = _read_json(outputs / "state.json")
    tasks = manager_tasks()
    html = f"""
    <html>
      <head><title>ManagerBot</title></head>
      <body style='font-family: sans-serif;'>
        <h1>ManagerBot</h1>
        <h2>State</h2>
        <pre>{json.dumps(state, indent=2)}</pre>
        <h2>Tasks</h2>
        <pre>{json.dumps(tasks, indent=2)}</pre>
        <form method='post' action='/api/manager/run-once'>
          <button type='submit'>Run Manager Cycle</button>
        </form>
      </body>
    </html>
    """
    return HTMLResponse(html)
