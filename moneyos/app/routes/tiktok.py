import json

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from moneyos.app.core import safety
from moneyos.app.core.video_pipeline import (
    ScriptItem,
    ffmpeg_available,
    generate_script,
    generate_video_for_script,
)
from moneyos.app.core.video_queue import create_script_item, list_outputs_for_script, list_scripts

router = APIRouter(prefix="/tiktok")


@router.get("", response_class=HTMLResponse)
def tiktok(request: Request):
    safe_info = safety.get_safe_mode_info()
    scripts = list_scripts("tiktok")
    script_items = []
    for script in scripts:
        payload = json.loads(script["payload_json"])
        outputs = []
        for output in list_outputs_for_script(script["id"]):
            outputs.append({"row": output, "payload": json.loads(output["payload_json"])})
        script_items.append(
            {
                "row": script,
                "payload": payload,
                "outputs": outputs,
            }
        )
    return request.app.state.templates.TemplateResponse(
        "tiktok.html",
        {
            "request": request,
            "mode": safety.get_mode(),
            "safe_mode": safe_info["safe_mode"],
            "safe_mode_reasons": safe_info["reasons"],
            "safe_mode_steps": safe_info["steps"],
            "scripts": script_items,
            "active_page": "TikTok",
            "ffmpeg_ready": ffmpeg_available(),
            "output_path": "output/tiktok",
        },
    )


@router.post("/script")
def create_script(topic: str = Form(...)):
    script = generate_script(topic, "tiktok")
    create_script_item("tiktok", topic, script)
    return RedirectResponse(url="/tiktok", status_code=303)


@router.post("/{script_id}/generate-video")
def generate_video(script_id: int):
    scripts = list_scripts("tiktok")
    script_row = next((row for row in scripts if row["id"] == script_id), None)
    if not script_row:
        return RedirectResponse(url="/tiktok", status_code=303)
    payload = json.loads(script_row["payload_json"])
    generate_video_for_script(ScriptItem(id=script_id, platform="tiktok", payload=payload))
    return RedirectResponse(url="/tiktok", status_code=303)
