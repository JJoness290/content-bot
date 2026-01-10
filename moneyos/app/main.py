from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.core import content_autopilot, runtime
from app.core.video_queue import init_video_queue_db
from app.routes import (
    api_assets,
    api_autopilot,
    assets,
    checklist,
    experiments,
    logs,
    metrics,
    overview,
    research,
    settings,
    tiktok,
    youtube,
)

app = FastAPI(title="MoneyOS")

app.mount("/static", StaticFiles(directory="app/static"), name="static")

templates = Jinja2Templates(directory="app/templates")
app.state.templates = templates
templates.env.globals["limited_mode"] = runtime.is_limited_mode
templates.env.globals["bootstrap_error"] = runtime.get_bootstrap_error
templates.env.globals["health_status"] = runtime.health_status
templates.env.globals["autopilot_status"] = content_autopilot.autopilot_status

scheduler = BackgroundScheduler()
app.state.scheduler = scheduler

app.include_router(overview.router)
app.include_router(checklist.router)
app.include_router(research.router)
app.include_router(experiments.router)
app.include_router(metrics.router)
app.include_router(logs.router)
app.include_router(settings.router)
app.include_router(assets.router)
app.include_router(api_autopilot.router)
app.include_router(api_assets.router)
app.include_router(tiktok.router)
app.include_router(youtube.router)


@app.on_event("startup")
def start_scheduler() -> None:
    init_video_queue_db()
    if not scheduler.running:
        state = content_autopilot.get_autopilot_state()
        if state["enabled"]:
            content_autopilot.schedule_job(scheduler, state["interval_minutes"])
        scheduler.start()


@app.on_event("shutdown")
def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown()
