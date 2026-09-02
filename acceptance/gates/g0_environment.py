"""Gate 0a: environment sanity. Fails on banned imports, absolute paths, oversize files."""
from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BANNED_IMPORTS = {"torch", "numpy", "sounddevice", "sherpa_onnx", "fastapi", "uvicorn", "pydantic", "requests", "httpx", "whisper", "soundfile", "pandas"}
SCAN_DIRS = ["src", "acceptance", "tasks"]


def _py_files():
    for rel in SCAN_DIRS:
        base = REPO / rel
        if not base.is_dir():
            continue
        yield from base.rglob("*.py")


def run():
    problems = []
    for path in _py_files():
        rel = path.relative_to(REPO).as_posix()
        text = path.read_text(encoding="utf-8", errors="replace")
        if text.startswith("###VENDORED###"):
            continue
        try:
            tree = ast.parse(text)
        except SyntaxError as exc:
            problems.append(f"{rel}: syntax error: {exc}")
            continue
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = [node.module.split(".")[0]]
            for name in names:
                if name in BANNED_IMPORTS:
                    problems.append(f"{rel}: banned import '{name}' (stdlib-only rule)")
        if len(text.splitlines()) > 800:
            problems.append(f"{rel}: file exceeds 800 lines")
        for needle in ("C:\\\\", "D:\\\\", "/Users/", "C:/Users"):
            if needle in text and "acceptance" not in rel:
                problems.append(f"{rel}: hard-coded absolute path {needle!r}")
    return problems


if __name__ == "__main__":
    issues = run()
    print("\n".join(issues) if issues else "G0_ENVIRONMENT: PASS")
    sys.exit(1 if issues else 0)
