from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from moneyos.app.core import db, safety

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
@router.get("/overview", response_class=HTMLResponse)
def overview(request: Request):
    safe_info = safety.get_safe_mode_info()
    with db.get_connection() as conn:
        metrics = conn.execute(
            "SELECT * FROM metrics_daily ORDER BY date DESC LIMIT 3"
        ).fetchall()
        tasks = conn.execute(
            "SELECT * FROM tasks ORDER BY created_at DESC LIMIT 3"
        ).fetchall()
        experiments = conn.execute(
            "SELECT * FROM experiments ORDER BY started_at DESC LIMIT 3"
        ).fetchall()
    return request.app.state.templates.TemplateResponse(
        "overview.html",
        {
            "request": request,
            "mode": safety.get_mode(),
            "safe_mode": safe_info["safe_mode"],
            "safe_mode_reasons": safe_info["reasons"],
            "safe_mode_steps": safe_info["steps"],
            "metrics": metrics,
            "tasks": tasks,
            "experiments": experiments,
            "active_page": "Overview",
        },
    )
