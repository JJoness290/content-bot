from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class Plan:
    goal: str
    hypothesis: str
    tactics: list[str]
    strategy_steps: list[str]
    files_to_modify: list[str]
    files_to_create: list[str]
    verification_expectations: list[str]
    risk_notes: list[str]


@dataclass
class PreflightReport:
    repo_map: str
    hook_filler_hits: list[dict[str, Any]]
