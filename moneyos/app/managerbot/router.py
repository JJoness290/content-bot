from __future__ import annotations

import json
from typing import Any

from app.repairbot_v2.llm_client import LLMRouter


def ai_choose_task(state: dict[str, Any]) -> str:
    router = LLMRouter()
    prompt = "Choose next task based on state: " + json.dumps(state)
    response = router.generate(prompt)
    text = response.content.lower()
    if "repair" in text:
        return "REPAIR"
    if "verify" in text:
        return "VERIFY"
    return "GENERATE_TIKTOK"
