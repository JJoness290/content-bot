from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.core import learning, safety

router = APIRouter(prefix="/experiments")


@router.get("", response_class=HTMLResponse)
def experiments(request: Request):
    safe_info = safety.get_safe_mode_info()
    experiments = learning.list_experiments()
    return request.app.state.templates.TemplateResponse(
        "experiments.html",
        {
            "request": request,
            "mode": safety.get_mode(),
            "safe_mode": safe_info["safe_mode"],
            "safe_mode_reasons": safe_info["reasons"],
            "safe_mode_steps": safe_info["steps"],
            "experiments": experiments,
            "active_page": "Experiments",
        },
    )
