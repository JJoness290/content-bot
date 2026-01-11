from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import logging

logger = logging.getLogger(__name__)


@dataclass
class VoiceCandidate:
    name: str
    engine: str
    tags: list[str]
    score: int = 0


class VoiceManager:
    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.candidates = self._discover_candidates()

    def _discover_candidates(self) -> list[VoiceCandidate]:
        candidates = [
            VoiceCandidate(
                name="en-US-JennyNeural",
                engine="edge_tts",
                tags=["energetic", "expressive", "casual"],
            ),
            VoiceCandidate(
                name="en-US-GuyNeural",
                engine="edge_tts",
                tags=["conversational", "informal", "fast"],
            ),
            VoiceCandidate(
                name="en-GB-SoniaNeural",
                engine="edge_tts",
                tags=["expressive", "casual"],
            ),
        ]
        return candidates

    def score_voice(self, voice: VoiceCandidate) -> int:
        score = 0
        tag_bonus = {"energetic": 3, "expressive": 2, "casual": 2, "informal": 2, "fast": 1}
        for tag in voice.tags:
            score += tag_bonus.get(tag, 0)
        voice.score = score
        return score

    def select_voice(self) -> VoiceCandidate:
        for voice in self.candidates:
            self.score_voice(voice)
        ranked = sorted(self.candidates, key=lambda v: v.score, reverse=True)
        best = ranked[0]
        if best.score < 7:
            raise RuntimeError("no_viable_voice")
        return best

    async def _edge_tts_save(self, text: str, output_path: Path, voice: str, rate: str) -> None:
        import edge_tts

        communicate = edge_tts.Communicate(text, voice=voice, rate=rate)
        await communicate.save(str(output_path))

    def synthesize(self, text: str, voice: VoiceCandidate, rate: str = "+10%") -> Path:
        output_path = self.output_dir / f"voice_{voice.name}.mp3"
        if voice.engine == "edge_tts":
            asyncio.run(self._edge_tts_save(text, output_path, voice.name, rate))
            return output_path
        raise RuntimeError("unsupported_voice_engine")

    def test_and_select(self, text: str) -> VoiceCandidate:
        errors: list[str] = []
        for candidate in self.candidates:
            self.score_voice(candidate)
            if candidate.score < 7:
                continue
            try:
                self.synthesize(text, candidate)
                return candidate
            except Exception as exc:
                errors.append(str(exc))
        raise RuntimeError("no_viable_voice")

    def validate_voice(self, voice: VoiceCandidate) -> bool:
        return voice.score >= 7
