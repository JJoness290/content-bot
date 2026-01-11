from __future__ import annotations

from typing import Any

from app.repairbot_v2.playbook.rules_store import load_rules
from app.repairbot_v2.playbook.tactics.api_health_fix import ApiHealthFix
from app.repairbot_v2.playbook.tactics.deps_install import DepsInstall
from app.repairbot_v2.playbook.tactics.ffmpeg_fix import FfmpegFix
from app.repairbot_v2.playbook.tactics.hook_filler_removal import HookFillerRemoval
from app.repairbot_v2.playbook.tactics.import_root_fix import ImportRootFix
from app.repairbot_v2.playbook.tactics.output_paths_fix import OutputPathsFix
from app.repairbot_v2.playbook.tactics.render_fix import RenderFix
from app.repairbot_v2.playbook.tactics.script_expand import ScriptExpand
from app.repairbot_v2.playbook.tactics.srt_contamination_fix import SrtContaminationFix
from app.repairbot_v2.playbook.tactics.tts_wiring_fix import TtsWiringFix

TACTICS = [
    DepsInstall(),
    ImportRootFix(),
    ScriptExpand(),
    TtsWiringFix(),
    SrtContaminationFix(),
    HookFillerRemoval(),
    FfmpegFix(),
    RenderFix(),
    OutputPathsFix(),
    ApiHealthFix(),
]


def choose_tactics(
    reason_codes: list[str],
    failure_bundle: dict[str, Any],
    intent: dict[str, Any],
    repo_map: dict[str, Any],
    memory: list[dict[str, Any]],
    outputs_dir: Any,
) -> list[Any]:
    rules = load_rules(outputs_dir)
    ordered = []
    if rules:
        for rule in rules:
            if set(rule.get("reason_codes", [])) <= set(reason_codes):
                preferred = rule.get("preferred_tactics", [])
                ordered.extend([tactic for tactic in TACTICS if tactic.id in preferred])
                break
    for tactic in TACTICS:
        if tactic in ordered:
            continue
        if tactic.applies(reason_codes, failure_bundle, intent, repo_map, memory):
            ordered.append(tactic)
    return ordered
