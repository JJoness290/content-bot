from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core import content_autopilot

router = APIRouter(prefix="/api/autopilot")


@router.get("/status", response_class=JSONResponse)
async def status(request: Request):
    state = content_autopilot.autopilot_status()
    return {
        "enabled": state["enabled"],
        "interval_minutes": state["interval_minutes"],
        "last_tick": state["last_run_at"],
        "last_run_result": state["last_run_result"],
    }


@router.post("/enable", response_class=JSONResponse)
async def enable(request: Request):
    interval = content_autopilot.enable_autopilot()
    scheduler = request.app.state.scheduler
    content_autopilot.schedule_job(scheduler, interval)
    return {"enabled": True, "interval_minutes": interval}


@router.post("/disable", response_class=JSONResponse)
async def disable(request: Request):
    content_autopilot.disable_autopilot()
    scheduler = request.app.state.scheduler
    content_autopilot.remove_job(scheduler)
    return {"enabled": False}
