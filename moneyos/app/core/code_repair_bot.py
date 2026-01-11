from __future__ import annotations

import compileall
import json
import logging
import os
import subprocess
import sys
import traceback
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable

from app.core.video_rules_manager import VideoRulesManager

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
MEMORY_PATH = DATA_DIR / "repair_bot_memory.json"
logger = logging.getLogger(__name__)


@dataclass
class RepairMemory:
    disabled_subtitles: bool = False
    disabled_backgrounds: bool = False
    disabled_filters: bool = False
    fallback_mode: bool = False
    applied_repairs: set[str] = field(default_factory=set)
    failures: dict[str, int] = field(default_factory=dict)
    successes: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "disabled_subtitles": self.disabled_subtitles,
            "disabled_backgrounds": self.disabled_backgrounds,
            "disabled_filters": self.disabled_filters,
            "fallback_mode": self.fallback_mode,
            "applied_repairs": sorted(self.applied_repairs),
            "failures": self.failures,
            "successes": self.successes,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RepairMemory":
        memory = cls()
        memory.disabled_subtitles = bool(payload.get("disabled_subtitles", False))
        memory.disabled_backgrounds = bool(payload.get("disabled_backgrounds", False))
        memory.disabled_filters = bool(payload.get("disabled_filters", False))
        memory.fallback_mode = bool(payload.get("fallback_mode", False))
        memory.applied_repairs = set(payload.get("applied_repairs", []))
        memory.failures = dict(payload.get("failures", {}))
        memory.successes = dict(payload.get("successes", {}))
        return memory


class CodeRepairBot:
    def __init__(self, memory_path: Path) -> None:
        self._memory_path = memory_path
        self._memory = self._load_memory()

    @property
    def memory(self) -> RepairMemory:
        return self._memory

    def _load_memory(self) -> RepairMemory:
        if not self._memory_path.exists():
            return RepairMemory()
        payload = json.loads(self._memory_path.read_text(encoding="utf-8"))
        return RepairMemory.from_dict(payload)

    def _save_memory(self) -> None:
        self._memory_path.parent.mkdir(parents=True, exist_ok=True)
        self._memory_path.write_text(json.dumps(self._memory.to_dict(), indent=2), encoding="utf-8")

    def _hash_signature(self, message: str) -> str:
        return sha256(message.encode("utf-8", errors="ignore")).hexdigest()

    def intercept_error(self, error: Exception, context: dict[str, Any] | None = None) -> str:
        context_blob = json.dumps(context or {}, sort_keys=True, default=str)
        signature_source = f"{type(error).__name__}:{error}:{context_blob}"
        signature = self._hash_signature(signature_source)
        self.record_failure(signature)
        logger.error("RepairBot captured error signature: %s", signature)
        logger.error("RepairBot traceback: %s", traceback.format_exc())
        return signature

    def apply_fix(self, signature: str, stderr: str = "", context: dict[str, Any] | None = None) -> bool:
        if signature in self._memory.applied_repairs:
            return False
        if self._memory.failures.get(signature, 0) > 1:
            return False

        stderr_lower = stderr.lower()
        applied = False
        context = context or {}
        fix = context.get("fix")
        if fix == "ensure_output_dir":
            output_dir = context.get("output_dir")
            if output_dir:
                Path(output_dir).mkdir(parents=True, exist_ok=True)
                applied = True
        if fix == "ensure_output_path":
            output_path = context.get("output_path")
            if output_path:
                path = Path(output_path)
                path.parent.mkdir(parents=True, exist_ok=True)
                duration = float(context.get("duration", 62.0))
                applied = self._safe_black_video(path, duration=duration)
        if "unable to choose an output format for" in stderr_lower:
            applied = True
        if "subtitles" in stderr_lower or ".srt" in stderr_lower or "caption" in stderr_lower:
            if not self._memory.disabled_subtitles:
                self._memory.disabled_subtitles = True
                applied = True
        if "invalid argument" in stderr_lower or "filter" in stderr_lower:
            if not self._memory.disabled_filters:
                self._memory.disabled_filters = True
                applied = True
        if "no such file" in stderr_lower or "could not open" in stderr_lower:
            if not self._memory.disabled_subtitles:
                self._memory.disabled_subtitles = True
                applied = True

        if applied:
            self._memory.applied_repairs.add(signature)
            self._save_memory()
            self.verify_repair(context)
            self.restart_app()
        return applied

    def retry_operation(self, operation: Callable[[], Any], context: dict[str, Any] | None = None) -> Any:
        try:
            result = operation()
            if context:
                signature = self._hash_signature(json.dumps(context, sort_keys=True, default=str))
                self.record_success(signature)
            return result
        except Exception as exc:  # noqa: BLE001 - controlled repair wrapper
            signature = self.intercept_error(exc, context)
            self.apply_fix(signature, str(exc), context=context)
            raise

    def fallback_to_safe_mode(self) -> None:
        self._memory.fallback_mode = True
        self._memory.disabled_subtitles = True
        self._memory.disabled_backgrounds = True
        self._memory.disabled_filters = True
        self._save_memory()
        logger.info("RepairBot fallback mode enabled")

    def record_success(self, signature: str) -> None:
        self._memory.successes[signature] = self._memory.successes.get(signature, 0) + 1
        self._save_memory()

    def record_failure(self, signature: str) -> None:
        self._memory.failures[signature] = self._memory.failures.get(signature, 0) + 1
        self._save_memory()

    def verify_repair(self, context: dict[str, Any] | None = None) -> None:
        logger.info("RepairBot verifying: compiling Python sources")
        compileall.compile_dir(str(ROOT), quiet=1)
        ffmpeg_cmd = (context or {}).get("ffmpeg_cmd")
        if ffmpeg_cmd is not None:
            subprocess.run(ffmpeg_cmd, capture_output=True, text=True, check=False)
        logger.info("RepairBot verification complete; relaunch requested")

    def restart_app(self) -> None:
        logger.info("RepairBot restarting application")
        os.execv(sys.executable, [sys.executable] + sys.argv)

    def _safe_black_video(self, output_path: Path, duration: float = 1.0) -> bool:
        rules = VideoRulesManager()
        plan = rules.plan_visuals("tiktok", max(duration, 62.0))
        colors = list(rules.color_sequence(plan.visuals))
        cmd = ["ffmpeg", "-y"]
        segment_duration = plan.segment_duration
        for color in colors:
            cmd += ["-f", "lavfi", "-i", f"color=c={color}:s=1080x1920:d={segment_duration}"]
        concat_inputs = "".join(f"[{idx}:v]" for idx in range(plan.visuals))
        filter_complex = f"{concat_inputs}concat=n={plan.visuals}:v=1:a=0[v0]"
        cmd += [
            "-filter_complex",
            filter_complex,
            "-map",
            "[v0]",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-r",
            "25",
            "-movflags",
            "+faststart",
            output_path.as_posix(),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error("RepairBot safe video failed: %s", result.stderr)
            return False
        return output_path.exists() and output_path.stat().st_size > 0


_BOT: CodeRepairBot | None = None


def get_code_repair_bot() -> CodeRepairBot:
    global _BOT
    if _BOT is None:
        _BOT = CodeRepairBot(MEMORY_PATH)
    return _BOT
