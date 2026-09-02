"""Gate 0b: secret scan. Zero tolerance on a public repo."""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCAN_DIRS = ["src", "acceptance", "tasks", "docs", "vendor"]
PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{16,}"),
    re.compile(r"AIza[0-9A-Za-z\-_]{20,}"),
    re.compile(r"[0-9a-f]{32}\.[A-Za-z0-9]{16}"),
    re.compile(r"(?i)(api_?key|token|secret)\s*[:=]\s*['\"][A-Za-z0-9+/=_\-]{16,}"),
    re.compile(r"(?i)Bearer\s+[A-Za-z0-9\-_\.]{20,}"),
]
SCAN_SUFFIXES = {".py", ".json", ".md", ".txt", ".cfg", ".toml"}


def run():
    problems = []
    for rel_dir in SCAN_DIRS:
        base = REPO / rel_dir
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix not in SCAN_SUFFIXES:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            for i, line in enumerate(text.splitlines()):
                for pat in PATTERNS:
                    if pat.search(line):
                        problems.append(f"{path.relative_to(REPO).as_posix()}:{i+1}: secret-like pattern")
    return problems


if __name__ == "__main__":
    issues = run()
    print("\n".join(issues) if issues else "G0_SECRETS: PASS")
    sys.exit(1 if issues else 0)
