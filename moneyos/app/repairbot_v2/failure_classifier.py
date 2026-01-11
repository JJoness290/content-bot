from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


REASON_CODES = {
    "DEP_MISSING_MODULE",
    "IMPORT_ROOT_MISMATCH",
    "SCRIPT_TOO_SHORT",
    "TTS_AUDIO_MISSING",
    "SRT_AS_SCRIPT_CONTAMINATION",
    "HOOK_FILLER_SPAM_DETECTED",
    "FFMPEG_MISSING",
    "VIDEO_RENDER_FAIL",
    "OUTPUT_PATHS_MISSING",
    "API_HEALTH_FAIL",
    "ROUTE_IMPORT_ERROR",
    "TIMEOUT_OR_DEADLOCK",
    "PERMISSION_ERROR",
}


def classify_failure(log_text: str, exception_text: str, verify_reasons: list[str]) -> list[str]:
    combined = "\n".join([log_text or "", exception_text or "", "\n".join(verify_reasons)])
    combined_lower = combined.lower()
    codes: list[str] = []

    if "modulenotfounderror" in combined_lower or "no module named" in combined_lower:
        codes.append("DEP_MISSING_MODULE")
    if "moneyos" in combined_lower and "no module named" in combined_lower:
        codes.append("IMPORT_ROOT_MISMATCH")
    if "spoken_script_too_short" in verify_reasons or "too short" in combined_lower:
        codes.append("SCRIPT_TOO_SHORT")
    if "audio_missing_or_small" in verify_reasons or "tts failed" in combined_lower:
        codes.append("TTS_AUDIO_MISSING")
    if "contains_srt" in " ".join(verify_reasons) or "-->" in combined or "00:00:" in combined:
        codes.append("SRT_AS_SCRIPT_CONTAMINATION")
    if "hook_spam_detected" in verify_reasons:
        codes.append("HOOK_FILLER_SPAM_DETECTED")
    if "ffmpeg" in combined_lower and "not available" in combined_lower:
        codes.append("FFMPEG_MISSING")
    if "ffmpeg" in combined_lower and "failed" in combined_lower:
        codes.append("VIDEO_RENDER_FAIL")
    if "output not found" in combined_lower:
        codes.append("OUTPUT_PATHS_MISSING")
    if "autopilot_status_unavailable" in verify_reasons:
        codes.append("API_HEALTH_FAIL")
    if "importerror" in combined_lower:
        codes.append("ROUTE_IMPORT_ERROR")
    if "timeout" in combined_lower or "deadlock" in combined_lower:
        codes.append("TIMEOUT_OR_DEADLOCK")
    if "permission" in combined_lower or "access denied" in combined_lower:
        codes.append("PERMISSION_ERROR")

    return sorted(set([code for code in codes if code in REASON_CODES]))


def write_failure_bundle(
    outputs: Path,
    reason_codes: list[str],
    log_excerpt: str,
    traceback: str,
    suspected_files: list[str],
) -> Path:
    bundle = {
        "reason_codes": reason_codes,
        "log_excerpt": log_excerpt,
        "traceback": traceback,
        "suspected_files": suspected_files,
        "timestamp": datetime.utcnow().isoformat(),
    }
    outputs.mkdir(parents=True, exist_ok=True)
    path = outputs / "last_failure_bundle.json"
    path.write_text(json.dumps(bundle, indent=2), encoding="utf-8")
    return path
