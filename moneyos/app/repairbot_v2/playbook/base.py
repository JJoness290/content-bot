from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class TacticPlan:
    id: str
    details: dict[str, Any]


class Tactic:
    id = "base"

    def applies(
        self,
        reason_codes: list[str],
        failure_bundle: dict[str, Any],
        intent: dict[str, Any],
        repo_map: dict[str, Any],
        memory: list[dict[str, Any]],
    ) -> bool:
        _ = (failure_bundle, intent, repo_map, memory)
        return bool(reason_codes)

    def plan(self, *args: Any, **kwargs: Any) -> TacticPlan:
        _ = (args, kwargs)
        return TacticPlan(id=self.id, details={})

    def apply(self, plan: TacticPlan, patcher: Any, snapshot: Any) -> dict[str, Any]:
        _ = (plan, patcher, snapshot)
        return {"applied": False}

    def verify(self, verify_runner: Any) -> tuple[bool, list[str]]:
        return verify_runner()
