from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Iterable


def install_packages(packages: Iterable[str], root: Path) -> None:
    packages = [pkg for pkg in packages if pkg]
    if not packages:
        return
    subprocess.run(["python", "-m", "pip", "install", "--upgrade", "pip"], cwd=root, check=False)
    subprocess.run(["python", "-m", "pip", "install", *packages], cwd=root, check=False)
    requirements = root / "requirements.txt"
    existing = requirements.read_text(encoding="utf-8").splitlines() if requirements.exists() else []
    for pkg in packages:
        if pkg not in existing:
            existing.append(pkg)
    requirements.write_text("\n".join(existing) + "\n", encoding="utf-8")
    subprocess.run(["python", "-m", "pip", "freeze"], cwd=root, check=False, capture_output=True, text=True)
    lock = root / "requirements.lock"
    lock.write_text(subprocess.run(["python", "-m", "pip", "freeze"], cwd=root, check=False, capture_output=True, text=True).stdout, encoding="utf-8")
