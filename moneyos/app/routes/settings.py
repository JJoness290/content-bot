from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from moneyos.app.core import content_autopilot, safety

router = APIRouter(prefix="/settings")


@router.get("", response_class=HTMLResponse)
def settings(request: Request):
    safe_info = safety.get_safe_mode_info()
    return request.app.state.templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "mode": safety.get_mode(),
            "safe_mode": safe_info["safe_mode"],
            "safe_mode_reasons": safe_info["reasons"],
            "safe_mode_steps": safe_info["steps"],
            "autopilot": content_autopilot.SETTINGS,
            "active_page": "Settings",
        },
    )
