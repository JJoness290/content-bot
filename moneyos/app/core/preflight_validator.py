from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import shutil

from app.core.code_repair_bot import get_code_repair_bot
from app.core.video_manager_bot import VideoManagerBot
from app.core.video_rules_manager import VideoRulesManager


@dataclass
class PreflightResult:
    ok: bool
    message: str


class PreflightValidator:
    def __init__(self) -> None:
        self.rules = VideoRulesManager()
        self.manager = VideoManagerBot()
        self.bot = get_code_repair_bot()

    def validate(self, output_path: Path, platform: str) -> PreflightResult:
        if output_path.suffix != ".mp4":
            return PreflightResult(False, "output_path_invalid")
        if output_path.stem.isdigit():
            return PreflightResult(False, "output_filename_numeric")
        if platform not in {"tiktok", "youtube"}:
            return PreflightResult(False, "platform_invalid")
        if shutil.which("ffmpeg") is None:
            return PreflightResult(False, "ffmpeg_missing")
        return PreflightResult(True, "ok")

    def validate_or_repair(self, output_path: Path, platform: str) -> PreflightResult:
        result = self.validate(output_path, platform)
        if result.ok:
            return result
        signature = self.bot.intercept_error(RuntimeError(result.message), context={"phase": "preflight"})
        self.bot.apply_fix(
            signature,
            result.message,
            context={"fix": "ensure_output_path", "output_path": str(output_path), "duration": 62.0, "restart": False},
        )
        return self.validate(output_path, platform)
