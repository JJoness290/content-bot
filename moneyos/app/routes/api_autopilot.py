from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core import video_autopilot

router = APIRouter(prefix="/api/autopilot")


@router.get("/status", response_class=JSONResponse)
async def status(request: Request):
    state = video_autopilot.autopilot_status()
    return {
        "enabled": state["enabled"],
        "interval_minutes": state["interval_minutes"],
        "last_tick": state["last_run_at"],
        "last_run_result": state["last_run_result"],
        "last_action": state["last_action"],
        "last_error": state["last_error"],
        "platforms": state["platforms"],
    }


@router.post("/enable", response_class=JSONResponse)
async def enable(request: Request):
    config = video_autopilot.enable_autopilot()
    interval = config["interval_minutes"]
    scheduler = request.app.state.scheduler
    video_autopilot.schedule_job(scheduler, interval)
    return {"enabled": True, "interval_minutes": interval}


@router.post("/disable", response_class=JSONResponse)
async def disable(request: Request):
    video_autopilot.disable_autopilot()
    scheduler = request.app.state.scheduler
    video_autopilot.remove_job(scheduler)
    return {"enabled": False}
