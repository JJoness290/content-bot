from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config" / "settings.yaml"
DB_PATH = ROOT / "data" / "moneyos.db"

SAFE_MODE_LABEL = "Safe Mode"
OPERATIONAL_LABEL = "Operational Mode"


def get_safe_mode_info() -> dict[str, list[str] | bool]:
    reasons: list[str] = []
    steps: list[str] = []
    if not CONFIG_PATH.exists():
        reasons.append("Config file missing: config/settings.yaml")
        steps.append("Restore config/settings.yaml or recreate it from source control.")
    if not DB_PATH.exists():
        reasons.append("Database missing: data/moneyos.db")
        steps.append("Run python start.py to initialize the database.")
    return {"safe_mode": bool(reasons), "reasons": reasons, "steps": steps}


def get_mode() -> str:
    info = get_safe_mode_info()
    return SAFE_MODE_LABEL if info["safe_mode"] else OPERATIONAL_LABEL
