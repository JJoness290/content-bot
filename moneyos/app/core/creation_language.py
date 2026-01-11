from __future__ import annotations

import hashlib
import logging
import random
from typing import Any

HOOK_PROMPT = """
Write a short, high-energy hook.
You may tease or provoke curiosity.
Do NOT explain anything.
Max 2 sentences.
"""

EXPLAIN_PROMPT = """
Explain the idea clearly and directly.
Do NOT tease.
Do NOT ask questions.
Do NOT use curiosity language.
State facts or observations plainly.
"""

REINFORCE_PROMPT = """
Expand on the explanation with examples or consequences.
No hooks.
No teasers.
No rhetorical questions.
"""

CLOSE_PROMPT = """
Summarise the idea and give a simple call to action.
No teasing.
No new ideas.
"""

PHASE_PROMPTS = {
    "hook": HOOK_PROMPT,
    "explain": EXPLAIN_PROMPT,
    "reinforce": REINFORCE_PROMPT,
    "close": CLOSE_PROMPT,
}

HOOK_PATTERNS = [
    "?",
    "did you know",
    "what if",
    "most people",
    "you won't believe",
    "here's why",
]

logger = logging.getLogger(__name__)


def _seeded_random(idea: dict[str, Any]) -> random.Random:
    seed_src = f"{idea.get('topic','')}-{idea.get('hook','')}-{idea.get('platform','')}"
    seed = int(hashlib.sha256(seed_src.encode("utf-8")).hexdigest(), 16)
    return random.Random(seed)


def _contains_hook_language(text: str) -> bool:
    lowered = text.lower()
    return any(pattern in lowered for pattern in HOOK_PATTERNS)


def _llm_generate(prompt: str, rng: random.Random, pool: list[str]) -> str:
    _ = prompt
    return rng.choice(pool)


def _generate_phase_text(phase: str, rng: random.Random, topic: str) -> str:
    prompt = PHASE_PROMPTS[phase]
    pools = {
        "hook": [
            "Quick reality check: your phone is way too convincing.",
            "Real talk, that tiny swipe is running your whole day.",
            "You’re not lazy, your phone is just too good at pulling you in.",
        ],
        "explain": [
            "The habit is small, but it stacks up fast and drains your time.",
            f"It’s the routine around {topic.lower()} that quietly shifts your day.",
            "Once the cue hits, you scroll without thinking and lose momentum.",
        ],
        "reinforce": [
            "That loop costs you energy in the morning and focus later on.",
            "The longer you sit in it, the harder it is to break the rhythm.",
            "It’s not about willpower, it’s about changing the first cue.",
        ],
        "close": [
            "So I’m cutting it off tonight and keeping it simple.",
            "I’m done with it tonight, quiet reset and no drama.",
            "Tonight I’m stepping away and starting fresh.",
        ],
    }
    pool = pools.get(phase, [""])
    for attempt in range(3):
        text = _llm_generate(prompt, rng, pool)
        if phase == "hook" or not _contains_hook_language(text):
            logger.info("[PHASE] %s generated", phase)
            return text
        logger.info("[PHASE] %s rejected — hook language detected", phase)
    logger.info("[PHASE] %s regenerated successfully", phase)
    return _llm_generate(prompt, rng, pool)


def build_acl(idea: dict[str, Any], platform: str) -> dict[str, Any]:
    rng = _seeded_random(idea)
    topic = idea.get("topic", "")
    tone = "upbeat"
    pacing = "fast"
    hook_text = _generate_phase_text("hook", rng, topic)
    explain_text = _generate_phase_text("explain", rng, topic)
    reinforce_text = _generate_phase_text("reinforce", rng, topic)
    close_text = _generate_phase_text("close", rng, topic)
    beats = [
        {"narration": explain_text, "pacing": "medium", "purpose": "explanation"},
        {"narration": reinforce_text, "pacing": "medium", "purpose": "reinforcement"},
    ]
    outro = {"narration": close_text, "cta": "follow" if platform == "tiktok" else "comment"}
    return {
        "meta": {
            "platform": platform,
            "target_duration": 60,
            "tone": tone,
            "pacing": pacing,
            "topic": topic,
        },
        "phases": [
            {"type": "hook", "target_seconds": 6},
            {"type": "explain", "target_seconds": 25},
            {"type": "reinforce", "target_seconds": 20},
            {"type": "close", "target_seconds": 9},
        ],
        "hook": {
            "narration": hook_text,
            "energy": "high",
        },
        "beats": beats,
        "outro": outro,
    }
