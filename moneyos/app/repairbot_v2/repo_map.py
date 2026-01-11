from __future__ import annotations

import ast
import json
from pathlib import Path


def build_repo_map(root: Path, output_dir: Path) -> Path:
    modules = []
    imports = {}
    functions = {}
    for path in root.rglob("*.py"):
        if ".git" in path.parts or "outputs" in path.parts:
            continue
        rel = path.relative_to(root).as_posix()
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        modules.append(rel)
        file_imports = []
        file_functions = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                file_imports.extend([alias.name for alias in node.names])
            if isinstance(node, ast.ImportFrom):
                if node.module:
                    file_imports.append(node.module)
            if isinstance(node, ast.FunctionDef):
                file_functions.append(node.name)
        imports[rel] = sorted(set(file_imports))
        functions[rel] = sorted(set(file_functions))

    payload = {
        "modules": sorted(modules),
        "imports": imports,
        "functions": functions,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "repo_map.json"
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return output_path
