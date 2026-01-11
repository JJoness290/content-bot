from __future__ import annotations

import argparse
import json
from pathlib import Path

from moneyos.repairbot_v2.agent import run_agent


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["once", "watch"], default="once")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    outputs = root / "outputs" / "repairbot_v2"
    intent_path = root / "moneyos_intent.yaml"
    intent = json.loads("{}")
    if intent_path.exists():
        import yaml

        intent = yaml.safe_load(intent_path.read_text(encoding="utf-8"))
    if args.mode == "once":
        run_agent(root, outputs, intent, once=True)
    else:
        run_agent(root, outputs, intent, once=False)


if __name__ == "__main__":
    main()
