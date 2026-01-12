from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable
import logging
import random


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
        fillers = [
            "Quick side note: this is the part everyone skips but it changes everything.",
            "Keep it casual, keep it real, and make the small change today.",
            "No big reset, just tweak the first minute and the rest follows.",
            "If this feels too simple, that’s the point—simple works.",
        ]
        filler_idx = 0
        while len(words) < min_words:
            text = f"{text} {fillers[filler_idx % len(fillers)]}"
            filler_idx += 1
            words = text.split()
        if len(words) > max_words:
            text = " ".join(words[:max_words])
        return text

    def extend_for_duration(self, text: str, min_seconds: float) -> str:
        words = text.split()
        target_words = max(140, int(min_seconds * 2.4))
        additions = [
            "Give yourself a two-breath pause before the next swipe.",
            "Say it out loud once, it actually breaks the spell.",
            "Put the phone down face down for one minute, it’s wild how fast it helps.",
            "Swap the last scroll for a quick stretch and you’ll feel the difference.",
            "The tiny reset is the whole trick, not some big overhaul.",
            "It’s not about willpower, it’s about changing the first cue.",
        ]
        random.shuffle(additions)
        idx = 0
        while len(words) < target_words and idx < len(additions):
            text = f"{text} {additions[idx]}"
            idx += 1
            words = text.split()
        return self.ensure_word_count(text, target_words, max(target_words + 10, 180))

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

    def validate_plan(self, platform: str, voice_duration: float, plan: VisualPlan) -> bool:
        logger = logging.getLogger(__name__)
        ok = True
        if platform == "tiktok" and voice_duration < self.TIKTOK_MIN_SECONDS:
            logger.warning("TikTok voice duration too short: %.2fs", voice_duration)
            ok = False
        if plan.visuals < 2:
            logger.warning("Video visuals count too low: %s", plan.visuals)
            ok = False
        if plan.total_duration < voice_duration:
            logger.warning(
                "Plan duration too short: %.2fs < voice %.2fs",
                plan.total_duration,
                voice_duration,
            )
            ok = False
        return ok

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
