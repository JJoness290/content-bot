import os
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
BOOTSTRAP_ERROR_LOG = ROOT / "logs" / "bootstrap_error.log"


def is_limited_mode() -> bool:
    return os.environ.get("MONEYOS_LIMITED_MODE") == "1"


def _redact(text: str) -> str:
    patterns = [
        r"(?i)(token|key|secret|password)\s*[:=]\s*\S+",
        r"(?i)authorization\s*[:=]\s*\S+",
    ]
    redacted = text
    for pattern in patterns:
        redacted = re.sub(pattern, "[redacted]", redacted)
    return redacted


def get_bootstrap_error() -> str | None:
    if not BOOTSTRAP_ERROR_LOG.exists():
        return None
    content = BOOTSTRAP_ERROR_LOG.read_text(encoding="utf-8")
    return _redact(content)


def health_status() -> str:
    return "Limited Mode" if is_limited_mode() else "Ready"
