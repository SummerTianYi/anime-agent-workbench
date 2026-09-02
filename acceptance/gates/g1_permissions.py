"""Gate 1c (Task C): permission layer - deny-by-default + injection resistance."""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from src.permissions import ActionRequest, PermissionEngine  # noqa: E402

CASES = [
    {"tool": "read_file", "arguments": {"path": "../secrets.env"}, "origin": "agent", "session_id": 1},
    {"tool": "read_file", "arguments": {"path": "C:/Windows/win.ini"}, "origin": "agent", "session_id": 1},
    {"tool": "read_file", "arguments": "not-a-dict", "origin": "agent", "session_id": 1},
]


def run():
    problems = []
    pending = []
    engine = PermissionEngine(rules=None)
    try:
        engine.evaluate(ActionRequest(**CASES[0]))
        pending.append("evaluate() not implemented (Task C)")
        return problems, pending
    except NotImplementedError:
        pending.append("evaluate() not implemented (Task C)")
        return problems, pending
    except Exception:
        problems.append("evaluate() raised unexpected error on first case")
        return problems, pending


if __name__ == "__main__":
    issues, pend = run()
    nl = chr(10)
    if issues:
        print(nl.join(issues))
        sys.exit(1)
    if pend:
        print(nl.join(pend))
        print("G1_PERMISSIONS: PENDING")
        sys.exit(2)
    print("G1_PERMISSIONS: PASS")
