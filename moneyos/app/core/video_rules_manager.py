from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable


@dataclass
class VisualPlan:
    visuals: int
    segment_duration: float
    total_duration: float


class VideoRulesManager:
    TIKTOK_MIN_SECONDS = 60.0
    TIKTOK_TARGET_SECONDS = 60.0
    TIKTOK_MAX_SECONDS = 65.0
    TIKTOK_MIN_VISUALS = 20
    TIKTOK_MAX_VISUALS = 40
    SEGMENT_MIN = 1.0
    SEGMENT_MAX = 3.0

    def ensure_word_count(self, text: str, min_words: int, max_words: int) -> str:
        words = text.split()
        filler = (
            "Here is the quick breakdown: keep it simple, keep it practical, "
            "and use the tip today so you actually see results this week."
        )
        while len(words) < min_words:
            text = f"{text} {filler}"
            words = text.split()
        if len(words) > max_words:
            text = " ".join(words[:max_words])
        return text

    def extend_for_duration(self, text: str, min_seconds: float) -> str:
        words = text.split()
        target_words = max(140, int(min_seconds * 2.4))
        return self.ensure_word_count(text, target_words, max(target_words + 10, 160))

    def plan_visuals(self, platform: str, voice_duration: float) -> VisualPlan:
        target_duration = voice_duration
        if platform == "tiktok":
            target_duration = max(self.TIKTOK_TARGET_SECONDS, voice_duration)
        visuals = math.ceil(target_duration / 2.0)
        if platform == "tiktok":
            visuals = max(self.TIKTOK_MIN_VISUALS, min(self.TIKTOK_MAX_VISUALS, visuals))
        segment_duration = max(self.SEGMENT_MIN, min(self.SEGMENT_MAX, target_duration / visuals))
        total_duration = segment_duration * visuals
        if total_duration < target_duration:
            visuals = math.ceil(target_duration / segment_duration)
            total_duration = segment_duration * visuals
        return VisualPlan(visuals=visuals, segment_duration=segment_duration, total_duration=total_duration)

    def validate_plan(self, platform: str, voice_duration: float, plan: VisualPlan) -> None:
        if platform == "tiktok" and voice_duration < self.TIKTOK_MIN_SECONDS:
            raise ValueError("TikTok video must be at least 60 seconds.")
        if plan.visuals < 2:
            raise ValueError("Video must contain multiple visuals.")
        if plan.total_duration < voice_duration:
            raise ValueError("Timeline must cover voice duration.")

    def enforce_plan(self, platform: str, voice_duration: float) -> VisualPlan:
        duration = voice_duration
        if platform == "tiktok":
            duration = max(self.TIKTOK_TARGET_SECONDS, voice_duration)
        plan = self.plan_visuals(platform, duration)
        if plan.total_duration < duration:
            plan = self.plan_visuals(platform, duration)
        return plan

    def color_sequence(self, count: int) -> Iterable[str]:
        palette = [
            "navy",
            "teal",
            "maroon",
            "olive",
            "purple",
            "steelblue",
            "darkgreen",
            "sienna",
            "slateblue",
            "darkred",
        ]
        for idx in range(count):
            yield palette[idx % len(palette)]
