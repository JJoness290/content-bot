import asyncio
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.responses import JSONResponse

from app.core import content_autopilot, runtime, video_autopilot
from app.core.code_repair_bot import get_code_repair_bot
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
    repairbot,
    manager,
    research,
    settings,
    tiktok,
    youtube,
)

app = FastAPI(title="MoneyOS")

APP_DIR = Path(__file__).resolve().parent

app.mount("/static", StaticFiles(directory=str(APP_DIR / "static")), name="static")
OUTPUT_DIR = APP_DIR.parent / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/output", StaticFiles(directory=OUTPUT_DIR), name="output")

templates = Jinja2Templates(directory=str(APP_DIR / "templates"))
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
app.include_router(repairbot.router)
app.include_router(manager.router)
app.include_router(tiktok.router)
app.include_router(youtube.router)


@app.middleware("http")
async def repair_bot_middleware(request: Request, call_next) -> Response:
    bot = get_code_repair_bot()
    try:
        response = await call_next(request)
    except Exception as exc:  # noqa: BLE001 - repair bot wrapper
        signature = bot.intercept_error(exc, context={"path": request.url.path, "method": request.method})
        bot.apply_fix(signature, str(exc), context={"path": request.url.path, "method": request.method})
        return JSONResponse(status_code=500, content={"detail": "RepairBot handled an internal error."})

    if response.status_code == 404 and request.url.path.startswith("/output"):
        output_path = OUTPUT_DIR / request.url.path.removeprefix("/output/").lstrip("/")
        signature = bot.intercept_error(
            FileNotFoundError(f"Missing output path: {output_path}"),
            context={"path": request.url.path, "fix": "ensure_output_path", "output_path": str(output_path)},
        )
        bot.apply_fix(
            signature,
            "output not found",
            context={"path": request.url.path, "fix": "ensure_output_path", "output_path": str(output_path)},
        )
    return response


@app.on_event("startup")
async def start_scheduler() -> None:
    init_video_queue_db()
    config = video_autopilot.init_video_autopilot_state()
    video_autopilot.schedule_job(scheduler, config["interval_minutes"])
    if not scheduler.running:
        scheduler.start()
    if not getattr(app.state, "autopilot_stop_event", None):
        app.state.autopilot_stop_event = asyncio.Event()
    if not getattr(app.state, "autopilot_task", None) or app.state.autopilot_task.done():
        app.state.autopilot_task = asyncio.create_task(
            content_autopilot.autopilot_loop(app.state.autopilot_stop_event)
        )


@app.on_event("shutdown")
async def stop_scheduler() -> None:
    stop_event = getattr(app.state, "autopilot_stop_event", None)
    if stop_event:
        stop_event.set()
    task = getattr(app.state, "autopilot_task", None)
    if task:
        task.cancel()
    if scheduler.running:
        scheduler.shutdown()
