from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from moneyos.app.core import audit, notifier, safety

router = APIRouter(prefix="/logs")


@router.get("", response_class=HTMLResponse)
def logs(request: Request):
    safe_info = safety.get_safe_mode_info()
    actions = audit.list_actions()
    notifications = notifier.list_notifications()
    return request.app.state.templates.TemplateResponse(
        "logs.html",
        {
            "request": request,
            "mode": safety.get_mode(),
            "safe_mode": safe_info["safe_mode"],
            "safe_mode_reasons": safe_info["reasons"],
            "safe_mode_steps": safe_info["steps"],
            "actions": actions,
            "notifications": notifications,
            "active_page": "Memory & Logs",
        },
    )
