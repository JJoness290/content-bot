from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from moneyos.app.core import safety, task_manager

router = APIRouter(prefix="/checklist")


@router.get("", response_class=HTMLResponse)
def checklist(request: Request):
    safe_info = safety.get_safe_mode_info()
    tasks = task_manager.list_tasks()
    return request.app.state.templates.TemplateResponse(
        "checklist.html",
        {
            "request": request,
            "mode": safety.get_mode(),
            "safe_mode": safe_info["safe_mode"],
            "safe_mode_reasons": safe_info["reasons"],
            "safe_mode_steps": safe_info["steps"],
            "tasks": tasks,
            "active_page": "Checklist",
        },
    )


@router.get("/{task_id}", response_class=HTMLResponse)
def task_detail(request: Request, task_id: int):
    safe_info = safety.get_safe_mode_info()
    task = task_manager.get_task(task_id)
    if not task:
        return request.app.state.templates.TemplateResponse(
            "task_detail.html",
            {
                "request": request,
                "mode": safety.get_mode(),
                "safe_mode": safe_info["safe_mode"],
                "safe_mode_reasons": safe_info["reasons"],
                "safe_mode_steps": safe_info["steps"],
                "task": None,
                "active_page": "Checklist",
            },
        )
    return request.app.state.templates.TemplateResponse(
        "task_detail.html",
        {
            "request": request,
            "mode": safety.get_mode(),
            "safe_mode": safe_info["safe_mode"],
            "safe_mode_reasons": safe_info["reasons"],
            "safe_mode_steps": safe_info["steps"],
            "task": task,
            "active_page": "Checklist",
        },
    )
