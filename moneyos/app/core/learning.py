import json
import random
from datetime import datetime
from typing import Any

from app.core.db import get_connection


def list_experiments() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM experiments ORDER BY started_at DESC").fetchall()
        return [dict(row) for row in rows]


def record_experiment(name: str, hypothesis: str, variants: list[str]) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO experiments (name, hypothesis, variants_json, status, started_at, ended_at, outcome_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                hypothesis,
                json.dumps(variants),
                "PLANNED",
                datetime.utcnow().isoformat(),
                None,
                json.dumps({}),
            ),
        )
        conn.commit()
        return int(cur.lastrowid)


def record_outcome(experiment_id: int, variant: str, success: bool) -> None:
    with get_connection() as conn:
        row = conn.execute("SELECT outcome_json FROM experiments WHERE id = ?", (experiment_id,)).fetchone()
        outcomes = json.loads(row["outcome_json"]) if row else {}
        variant_stats = outcomes.get(variant, {"success": 0, "failure": 0})
        if success:
            variant_stats["success"] += 1
        else:
            variant_stats["failure"] += 1
        outcomes[variant] = variant_stats
        conn.execute(
            "UPDATE experiments SET outcome_json = ? WHERE id = ?",
            (json.dumps(outcomes), experiment_id),
        )
        conn.commit()


def pick_variant(variants: list[str], outcomes: dict[str, dict[str, int]] | None = None) -> str:
    outcomes = outcomes or {}
    scores = {}
    for variant in variants:
        stats = outcomes.get(variant, {"success": 0, "failure": 0})
        alpha = 1 + stats["success"]
        beta = 1 + stats["failure"]
        scores[variant] = random.betavariate(alpha, beta)
    return max(scores, key=scores.get)
