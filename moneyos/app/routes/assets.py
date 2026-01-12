from datetime import datetime

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from app.core import audit, content_autopilot, safety
from app.core.db import get_connection

router = APIRouter(prefix="/assets")


@router.get("", response_class=HTMLResponse)
def assets(request: Request):
    safe_info = safety.get_safe_mode_info()
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM assets ORDER BY created_at DESC").fetchall()
    return request.app.state.templates.TemplateResponse(
        "assets.html",
        {
            "request": request,
            "mode": safety.get_mode(),
            "safe_mode": safe_info["safe_mode"],
            "safe_mode_reasons": safe_info["reasons"],
            "safe_mode_steps": safe_info["steps"],
            "assets": rows,
            "active_page": "Assets",
        },
    )


@router.get("/{asset_id}", response_class=HTMLResponse)
def asset_detail(request: Request, asset_id: int):
    safe_info = safety.get_safe_mode_info()
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM assets WHERE id = ?", (asset_id,)).fetchone()
    return request.app.state.templates.TemplateResponse(
        "asset_detail.html",
        {
            "request": request,
            "mode": safety.get_mode(),
            "safe_mode": safe_info["safe_mode"],
            "safe_mode_reasons": safe_info["reasons"],
            "safe_mode_steps": safe_info["steps"],
            "asset": row,
            "active_page": "Assets",
        },
    )


@router.post("/{asset_id}/publish")
def asset_publish(request: Request, asset_id: int, medium_url: str = Form("")):
    with get_connection() as conn:
        conn.execute(
            "UPDATE assets SET status = ?, updated_at = ? WHERE id = ?",
            ("PUBLISHED", datetime.utcnow().isoformat(), asset_id),
        )
        task_row = conn.execute(
            "SELECT id FROM tasks WHERE title = ? AND status != ? ORDER BY created_at DESC LIMIT 1",
            ("Publish blog post on Medium", "DONE"),
        ).fetchone()
        if task_row:
            conn.execute(
                "UPDATE tasks SET status = ?, updated_at = ? WHERE id = ?",
                ("DONE", datetime.utcnow().isoformat(), task_row["id"]),
            )
        conn.commit()

    audit.log_action(
        name="asset_publish",
        action_type="content",
        metadata={"asset_id": asset_id, "medium_url": medium_url},
        decision="PUBLISHED",
        reason="Marked as published by human.",
    )
    return RedirectResponse(url=f"/assets/{asset_id}", status_code=303)


@router.post("", response_class=JSONResponse)
def create_asset(request: Request):
    asset_info = content_autopilot.create_blank_asset()
    generated = content_autopilot.generate_content_for_asset(asset_info["id"])
    return {
        "id": asset_info["uuid"],
        "type": "blog",
        "title": generated["title"],
        "status": "draft",
        "content": generated["content_md"],
        "created_at": datetime.utcnow().isoformat(),
    }


@router.post("/generate")
def generate_asset(
    request: Request,
    platform: str = Form("medium"),
    topic: str = Form(...),
    tone: str = Form("friendly"),
    length: str = Form("medium"),
    audience: str = Form("UK"),
    draft_only: bool = Form(False),
):
    payload = content_autopilot.generate_custom_asset(
        topic=topic,
        tone=tone,
        length=length,
        audience=audience,
        platform=platform,
        draft_only=draft_only,
    )
    asset = content_autopilot.create_asset_from_payload(payload)
    return RedirectResponse(url=f"/assets/{asset['id']}", status_code=303)
