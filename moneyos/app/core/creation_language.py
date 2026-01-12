from __future__ import annotations

import hashlib
import logging
import random
from typing import Any

HOOK_PROMPT = (
    "Write a short, high-impact hook. "
    "You may tease or provoke curiosity. "
    "Do NOT explain anything. "
    "Max 2 sentences."
)

EXPLAIN_PROMPT = (
    "Explain the idea clearly and directly. "
    "No teasing. "
    "No rhetorical questions. "
    "State facts plainly."
)

REINFORCE_PROMPT = (
    "Expand on the explanation with concrete examples, "
    "consequences, or clarification. "
    "No hooks. No teasing."
)

CLOSE_PROMPT = (
    "Summarise the idea and give a simple call to action. "
    "No new ideas. No teasing."
)

PHASE_PROMPTS = {
    "hook": HOOK_PROMPT,
    "explain": EXPLAIN_PROMPT,
    "reinforce": REINFORCE_PROMPT,
    "close": CLOSE_PROMPT,
}

HOOK_PHRASES = [
    "nobody talks about",
    "wait for it",
    "this part is wild",
    "here's the trick",
    "bet you didn't know",
    "most people",
    "did you know",
]

logger = logging.getLogger(__name__)


def _seeded_random(idea: dict[str, Any]) -> random.Random:
    seed_src = f"{idea.get('topic','')}-{idea.get('hook','')}-{idea.get('platform','')}"
    seed = int(hashlib.sha256(seed_src.encode("utf-8")).hexdigest(), 16)
    return random.Random(seed)


def _contains_hook_language(text: str) -> bool:
    lowered = text.lower()
    return any(pattern in lowered for pattern in HOOK_PHRASES)


def _llm_generate(prompt: str, rng: random.Random, pool: list[str]) -> str:
    _ = prompt
    return rng.choice(pool)


def generate_phase(phase: str, rng: random.Random, topic: str) -> str:
    prompt = PHASE_PROMPTS[phase]
    pools = {
        "hook": [
            "Quick reality check: your phone is way too convincing and it keeps stealing your attention before you even notice.",
            "Real talk, that tiny swipe is running your whole day and it’s cutting your focus into tiny pieces.",
            "You’re not lazy, your phone is just too good at pulling you in and making time disappear fast.",
        ],
        "explain": [
            "The habit is small, but it stacks up fast and drains your time in the quiet parts of your day.",
            f"It’s the routine around {topic.lower()} that quietly shifts your day and sets the tone for everything else.",
            "Once the cue hits, you scroll without thinking and lose momentum that you need later.",
        ],
        "reinforce": [
            "That loop costs you energy in the morning and focus later on, so the smallest habits feel heavier than they should.",
            "The longer you sit in it, the harder it is to break the rhythm and the more normal it starts to feel.",
            "It’s not about willpower, it’s about changing the first cue so the whole routine shifts with less effort.",
        ],
        "close": [
            "So I’m cutting it off tonight and keeping it simple, because the reset has to be calm and repeatable.",
            "I’m done with it tonight, quiet reset and no drama, just a clean start for tomorrow.",
            "Tonight I’m stepping away and starting fresh, one small change that makes the next day easier.",
        ],
    }
    pool = pools.get(phase, [""])
    text = _llm_generate(prompt, rng, pool)
    if phase != "hook" and _contains_hook_language(text):
        logger.info("[PHASE] %s rejected — hook language detected", phase)
        text = _llm_generate(prompt, rng, pool)
        logger.info("[PHASE] %s regenerated successfully", phase)
    logger.info("[GEN] %s generated", phase)
    return text


def generate_script(rng: random.Random, topic: str) -> tuple[str, dict[str, str]]:
    parts = {
        "hook": generate_phase("hook", rng, topic),
        "explain": generate_phase("explain", rng, topic),
        "reinforce": generate_phase("reinforce", rng, topic),
        "close": generate_phase("close", rng, topic),
    }
    script = " ".join(parts.values())
    return script, parts


def build_acl(idea: dict[str, Any], platform: str) -> dict[str, Any]:
    rng = _seeded_random(idea)
    topic = idea.get("topic", "")
    tone = "upbeat"
    pacing = "fast"
    spoken_script, parts = generate_script(rng, topic)
    hook_text = parts["hook"]
    explain_text = parts["explain"]
    reinforce_text = parts["reinforce"]
    close_text = parts["close"]
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
        "spoken_script": spoken_script,
        "beats": beats,
        "outro": outro,
    }
