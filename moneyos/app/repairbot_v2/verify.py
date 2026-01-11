from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import urllib.request

HOOK_LINES = [
    "Nobody talks about this but it works.",
    "Wait for it, this part is wild.",
    "Here's the trick most people miss.",
    "Bet you didn't know this rule.",
    "One tiny switch changes everything.",
]


def _ping_status() -> bool:
    try:
        with urllib.request.urlopen("http://127.0.0.1:8000/api/autopilot/status", timeout=2) as resp:
            return resp.status == 200
    except Exception:
        return False


def _run_server_check(root: Path) -> bool:
    proc = subprocess.Popen(["python", "-m", "moneyos.start"], cwd=root)
    try:
        ok = _ping_status()
    finally:
        proc.terminate()
    return ok


def working_order(root: Path, outputs: Path) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    spoken_path = root / "outputs" / "latest_spoken_script.txt"
    audio_wav = root / "outputs" / "latest_audio.wav"
    audio_mp3 = root / "outputs" / "latest_audio.mp3"
    audio_path = audio_wav if audio_wav.exists() else audio_mp3
    captions_path = root / "outputs" / "latest_captions.srt"
    video_path = root / "outputs" / "latest_video.mp4"

    if not spoken_path.exists():
        reasons.append("spoken_script_missing")
    else:
        text = spoken_path.read_text(encoding="utf-8")
        if len(text) <= 300:
            reasons.append("spoken_script_too_short")
        if "00:00:" in text or "-->" in text:
            reasons.append("spoken_script_contains_srt")
        for line in HOOK_LINES:
            if text.count(line) > 1:
                reasons.append("hook_spam_detected")
                break

    if not audio_path.exists() or audio_path.stat().st_size < 50_000:
        reasons.append("audio_missing_or_small")
    if not captions_path.exists():
        reasons.append("captions_missing")
    if not video_path.exists():
        reasons.append("video_missing")

    if not _ping_status():
        if not _run_server_check(root):
            reasons.append("autopilot_status_unavailable")

    ok = not reasons
    status = {"ok": ok, "reasons": reasons}
    outputs.mkdir(parents=True, exist_ok=True)
    (outputs / "last_status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
    return ok, reasons
