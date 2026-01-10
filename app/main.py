from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from moneyos.app.core import content_autopilot, runtime
from moneyos.app.routes import (
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

app.mount("/static", StaticFiles(directory="moneyos/app/static"), name="static")
app.mount("/output", StaticFiles(directory="moneyos/output"), name="output")

templates = Jinja2Templates(directory="moneyos/app/templates")
app.state.templates = templates
templates.env.globals["limited_mode"] = runtime.is_limited_mode
templates.env.globals["bootstrap_error"] = runtime.get_bootstrap_error
templates.env.globals["health_status"] = runtime.health_status
templates.env.globals["autopilot_status"] = content_autopilot.autopilot_status

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


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "MoneyOS running"}
