import json

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.core import safety
from app.core.video_pipeline import (
    ScriptItem,
    ffmpeg_available,
    generate_script,
    generate_video_for_script,
)
from app.core.video_queue import create_script_item, list_outputs_for_script, list_scripts

router = APIRouter(prefix="/youtube")


@router.get("", response_class=HTMLResponse)
def youtube(request: Request):
    safe_info = safety.get_safe_mode_info()
    scripts = list_scripts("youtube")
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
        "youtube.html",
        {
            "request": request,
            "mode": safety.get_mode(),
            "safe_mode": safe_info["safe_mode"],
            "safe_mode_reasons": safe_info["reasons"],
            "safe_mode_steps": safe_info["steps"],
            "scripts": script_items,
            "active_page": "YouTube",
            "ffmpeg_ready": ffmpeg_available(),
            "output_path": "output/youtube",
        },
    )


@router.post("/script")
def create_script(topic: str = Form(...)):
    script = generate_script(topic, "youtube")
    create_script_item("youtube", topic, script)
    return RedirectResponse(url="/youtube", status_code=303)


@router.post("/{script_id}/generate-video")
def generate_video(script_id: int):
    scripts = list_scripts("youtube")
    script_row = next((row for row in scripts if row["id"] == script_id), None)
    if not script_row:
        return RedirectResponse(url="/youtube", status_code=303)
    payload = json.loads(script_row["payload_json"])
    generate_video_for_script(ScriptItem(id=script_id, platform="youtube", payload=payload))
    return RedirectResponse(url="/youtube", status_code=303)
