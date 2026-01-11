from __future__ import annotations

import hashlib
import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import requests
from app.core.video_rules_manager import VideoRulesManager

ROOT = Path(__file__).resolve().parents[2]
VISUALS_DIR = ROOT / "output" / "visuals"


@dataclass
class TrendSignals:
    hashtags: list[str]
    hooks: list[str]
    pacing_seconds: float


class VideoManagerBot:
    def __init__(self) -> None:
        self.rules = VideoRulesManager()

    def enforce_duration(self, seconds: float) -> float:
        return max(self.rules.TIKTOK_TARGET_SECONDS, seconds)

    def validate_platform_rules(self, platform: str, duration: float, visuals_count: int) -> None:
        plan = self.rules.plan_visuals(platform, duration)
        self.rules.validate_plan(platform, duration, plan)
        if visuals_count < self.rules.TIKTOK_MIN_VISUALS and platform == "tiktok":
            raise ValueError("Insufficient visuals for TikTok.")

    def _fetch_trending_hashtags(self) -> list[str]:
        url = "https://www.tiktok.com/trending"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                return []
            tags = re.findall(r"#([A-Za-z0-9_]+)", response.text)
            return list(dict.fromkeys(tags))[:10]
        except Exception:
            return []

    def _fallback_hashtags(self) -> list[str]:
        return [
            "moneytok",
            "sidehustle",
            "budgeting",
            "personalfinance",
            "moneymoves",
            "ai tools",
        ]

    def _trend_signals(self) -> TrendSignals:
        hashtags = self._fetch_trending_hashtags()
        if not hashtags:
            hashtags = self._fallback_hashtags()
        hooks = [
            "Quick money tip you can use tonight.",
            "This one habit saved me £200 last month.",
            "If I had to start over, I'd do this first.",
            "Try this before you check your bank app again.",
        ]
        return TrendSignals(hashtags=hashtags, hooks=hooks, pacing_seconds=3.5)

    def _visual_keywords(self, topic: str) -> Iterable[str]:
        base = [
            "city night",
            "home office",
            "laptop",
            "phone",
            "coffee shop",
            "shopping",
            "budget",
            "finance",
            "money",
            "calendar",
            "planner",
            "hand writing",
            "coins",
            "bills",
            "calculator",
        ]
        topic_words = re.findall(r"[a-zA-Z]+", topic.lower())
        for word in topic_words[:5]:
            base.append(word)
        random.shuffle(base)
        return base

    def generate_visuals(self, platform: str, topic: str, voice_duration: float) -> list[Path]:
        plan = self.rules.plan_visuals(platform, voice_duration)
        self.rules.validate_plan(platform, voice_duration, plan)
        visuals_needed = plan.visuals
        visuals_dir = VISUALS_DIR / platform
        visuals_dir.mkdir(parents=True, exist_ok=True)
        visuals: list[Path] = []
        used_hashes: set[str] = set()
        keywords = list(self._visual_keywords(topic))
        while len(visuals) < visuals_needed and keywords:
            keyword = keywords.pop()
            seed = random.randint(1000, 9999)
            url = f"https://source.unsplash.com/1080x1920/?{keyword},{seed}"
            try:
                response = requests.get(url, timeout=15)
                if response.status_code != 200:
                    continue
                digest = hashlib.md5(response.content).hexdigest()
                if digest in used_hashes:
                    continue
                used_hashes.add(digest)
                filename = visuals_dir / f"{platform}_{len(visuals)+1}.jpg"
                filename.write_bytes(response.content)
                visuals.append(filename)
            except Exception:
                continue

        if len(visuals) < visuals_needed:
            visuals.extend(self._fallback_visuals(visuals_dir, visuals_needed - len(visuals)))

        if len(visuals) < visuals_needed:
            raise RuntimeError("Insufficient visuals for rendering.")

        return visuals

    def refine_script(self, script_text: str) -> str:
        signals = self._trend_signals()
        hook = random.choice(signals.hooks)
        script_text = f"{hook} {script_text}"
        script_text = script_text.replace("do not", "don't").replace("cannot", "can't")
        script_text = script_text.replace("you are", "you're").replace("we are", "we're")
        script_text = script_text.replace("it is", "it's")
        script_text = script_text.replace("Here is", "Here's").replace("There is", "There's")
        script_text = script_text.replace(". ", ".\n")
        return self._ensure_upbeat(script_text)

    def _ensure_upbeat(self, script_text: str) -> str:
        lines = [line.strip() for line in script_text.splitlines() if line.strip()]
        if not lines:
            lines = ["Most people are broke because of THIS habit."]
        if len(lines[0].split()) > 12:
            lines[0] = "Most people are broke because of THIS habit."
        enforced = [self._shorten_sentence(line) for line in lines]
        if len(enforced) < 24:
            enforced.extend(self._upbeat_fillers(24 - len(enforced)))
        return "\n".join(enforced)

    def _shorten_sentence(self, line: str) -> str:
        line = line.replace("that is", "that's").replace("you will", "you'll")
        words = line.split()
        if len(words) <= 12:
            return line
        return " ".join(words[:12])

    def _upbeat_fillers(self, count: int) -> list[str]:
        pool = [
            "Nobody talks about this but it works.",
            "If you're doing this, stop today.",
            "Wait for it, this part is wild.",
            "Here's the trick most people miss.",
            "Try this tonight, seriously.",
            "This is why you're stuck right now.",
            "One tiny switch changes everything.",
            "Bet you didn't know this rule.",
            "Do this before you check your bank app.",
            "Save this, you'll need it later.",
        ]
        return [pool[i % len(pool)] for i in range(count)]

    def extend_script(self, script_text: str) -> str:
        additions = [
            "Okay, quick example.",
            "Picture this. You do it again.",
            "Then it gets worse. You know it.",
            "Wait for it. Here comes the twist.",
        ]
        return f"{script_text}\n" + "\n".join(additions)

    def _fallback_visuals(self, visuals_dir: Path, count: int) -> list[Path]:
        visuals: list[Path] = []
        for idx in range(count):
            filename = visuals_dir / f"fallback_{idx+1}.ppm"
            self._write_ppm_pattern(filename, 720, 1280, idx)
            visuals.append(filename)
        return visuals

    def _write_ppm_pattern(self, path: Path, width: int, height: int, seed: int) -> None:
        random.seed(seed)
        header = f"P6\n{width} {height}\n255\n".encode()
        pixels = bytearray()
        for y in range(height):
            for x in range(width):
                r = (x * 255) // width
                g = (y * 255) // height
                b = (r + g + (seed * 13)) % 255
                if (x + y + seed) % 23 == 0:
                    r = (r + 80) % 255
                    g = (g + 40) % 255
                    b = (b + 60) % 255
                pixels.extend([r, g, b])
        path.write_bytes(header + pixels)
