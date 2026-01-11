from __future__ import annotations

import argparse
from pathlib import Path

from app.managerbot.agent import run_manager


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["once", "watch"], default="once")
    parser.add_argument("--until-green", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    outputs = root / "outputs" / "managerbot"
    if args.mode == "once":
        run_manager(root, outputs, mode="once")
    else:
        run_manager(root, outputs, mode="watch")


if __name__ == "__main__":
    main()
