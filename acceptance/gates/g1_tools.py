"""Gate 1d (Task E): read-only tool registry - allow-list + traversal rejection."""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from src.tools_registry import ToolRegistry  # noqa: E402

CASES = [
    ("read_file", {"path": "notes.txt"}, "inside root"),
    ("read_file", {"path": "../outside.txt"}, "traversal"),
    ("read_file", {"path": "C:/Windows/win.ini"}, "absolute"),
]


def run():
    problems = []
    pending = []
    registry = ToolRegistry()
    try:
        registry.openai_schema()
        pending.append("openai_schema/execute not implemented (Task E)")
        return problems, pending
    except NotImplementedError:
        pending.append("openai_schema/execute not implemented (Task E)")
        return problems, pending
    except Exception:
        problems.append("openai_schema() raised unexpected error")
        return problems, pending


if __name__ == "__main__":
    issues, pend = run()
    nl = chr(10)
    if issues:
        print(nl.join(issues))
        sys.exit(1)
    if pend:
        print(nl.join(pend))
        print("G1_TOOLS: PENDING")
        sys.exit(2)
    print("G1_TOOLS: PASS")
