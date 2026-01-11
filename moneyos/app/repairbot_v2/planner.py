from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.repairbot_v2.llm_client import LLMRouter
from app.repairbot_v2.prompts import SYSTEM_PROMPTS


def build_plan(intent: dict[str, Any], preflight: dict[str, Any], outputs: Path) -> dict[str, Any]:
    router = LLMRouter()
    prompt = SYSTEM_PROMPTS["plan"] + "\n" + json.dumps({"intent": intent, "preflight": preflight})
    response = router.generate(prompt)
    try:
        plan = json.loads(response.content)
    except Exception:
        plan = {
            "goal": "repair system",
            "hypothesis": "preflight issues",
            "tactics": ["targeted fixes"],
            "strategy_steps": ["inspect", "patch", "verify"],
            "files_to_modify": [],
            "files_to_create": [],
            "verification_expectations": [],
            "risk_notes": [],
        }
    outputs.mkdir(parents=True, exist_ok=True)
    (outputs / "plan_latest.json").write_text(json.dumps(plan, indent=2), encoding="utf-8")
    (outputs / "plan_latest.md").write_text("# Plan\n\n" + json.dumps(plan, indent=2), encoding="utf-8")
    preview = [
        "# Preview",
        "", 
        "## Goal",
        plan.get("goal", ""),
        "", 
        "## Files",
        "- Modify: " + ", ".join(plan.get("files_to_modify", [])),
        "- Create: " + ", ".join(plan.get("files_to_create", [])),
        "", 
        "## Success",
        "- " + "\n- ".join(plan.get("verification_expectations", []) or ["Working order reached"]),
    ]
    (outputs / "preview_latest.md").write_text("\n".join(preview), encoding="utf-8")
    return plan
