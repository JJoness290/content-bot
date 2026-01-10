from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.core import db, safety

router = APIRouter(prefix="/metrics")


@router.get("", response_class=HTMLResponse)
def metrics(request: Request):
    safe_info = safety.get_safe_mode_info()
    with db.get_connection() as conn:
        rows = conn.execute("SELECT * FROM metrics_daily ORDER BY date DESC").fetchall()
    return request.app.state.templates.TemplateResponse(
        "metrics.html",
        {
            "request": request,
            "mode": safety.get_mode(),
            "safe_mode": safe_info["safe_mode"],
            "safe_mode_reasons": safe_info["reasons"],
            "safe_mode_steps": safe_info["steps"],
            "metrics": rows,
            "active_page": "Metrics",
        },
    )
