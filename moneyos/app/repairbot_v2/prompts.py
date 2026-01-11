from __future__ import annotations

SYSTEM_PROMPTS = {
    "preflight": """
You are a repair bot. Summarize repo health risks and weak points.
Return concise JSON only.
""".strip(),
    "diagnosis": """
Diagnose the probable root causes. Return JSON only.
""".strip(),
    "plan": """
Generate a structured repair plan as JSON. Use keys: goal, hypothesis, tactics,
strategy_steps, files_to_modify, files_to_create, verification_expectations, risk_notes.
""".strip(),
    "patch": """
Propose a patch outline as JSON. Keep it short.
""".strip(),
    "verification": """
Interpret verify results and return JSON summary.
""".strip(),
    "idea": """
Generate a brief idea list in JSON.
""".strip(),
}
