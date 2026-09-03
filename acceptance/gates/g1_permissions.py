"""Gate 1c (Task C): permission layer - deny-by-default + injection resistance.

Behavioral checks (hardened by Task C per tasks/C-permission-layer/SPEC.md):
1. empty rule set denies everything with rule_id "default-deny" (proof of
   default-deny, not just an exception)
2. relative-path escape and absolute-path arguments are rejected even when a
   permissive rule would allow the tool (injection resistance cannot be
   allow-listed away)
3. a matching rule returns its own rule_id; first match wins
4. malformed (non-dict) arguments are rejected
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from src.permissions import ActionRequest, PermissionEngine, PolicyRule  # noqa: E402

INJECTION_CASES = [
    {"tool": "read_file", "arguments": {"path": "../secrets.env"}, "origin": "agent", "session_id": 1},
    {"tool": "read_file", "arguments": {"path": "C:/Windows/win.ini"}, "origin": "agent", "session_id": 1},
    {"tool": "read_file", "arguments": {"path": "..\\..\\secrets.env"}, "origin": "agent", "session_id": 1},
    {"tool": "read_file", "arguments": "/etc/passwd", "origin": "agent", "session_id": 1},
    {"tool": "read_file", "arguments": {"path": "~/ssh-keys"}, "origin": "agent", "session_id": 1},
    {"tool": "read_file", "arguments": {"nested": {"p": "a/../b"}}, "origin": "agent", "session_id": 1},
]


def _request(case: dict) -> ActionRequest:
    return ActionRequest(**case)


def run():
    problems = []
    pending = []
    try:
        # 1) default-deny proof: no rules -> every request denied as default-deny
        engine = PermissionEngine(rules=None)
        for tool in ("read_file", "speak", "unknown_tool"):
            decision = engine.evaluate(ActionRequest(tool=tool, arguments={}, origin="user", session_id=1))
            if decision.allowed:
                problems.append(f"default-deny violated: {tool} allowed with no rules")
            elif decision.rule_id != "default-deny":
                problems.append(f"default-deny expects rule_id 'default-deny', got {decision.rule_id!r}")
        # 2) injection resistance: escapes/absolute paths denied even WITH a permissive rule
        permissive = PermissionEngine(
            rules=[PolicyRule(rule_id="allow-read-agent", match_tool="read_file", match_origin="*", decision=True)]
        )
        for case in INJECTION_CASES:
            decision = permissive.evaluate(_request(case))
            if decision.allowed:
                problems.append(f"injection allowed despite rule: {case['arguments']!r}")
        # 3) rule hit must return the rule's own rule_id
        decision = permissive.evaluate(
            ActionRequest(tool="read_file", arguments={"path": "notes.txt"}, origin="agent", session_id=1)
        )
        if not decision.allowed:
            problems.append(f"rule hit unexpectedly denied: {decision.reason}")
        elif decision.rule_id != "allow-read-agent":
            problems.append(f"rule hit must return rule_id, got {decision.rule_id!r}")
        # 3b) specific rule beats later wildcard (first match wins, attributable)
        ordered = PermissionEngine(
            rules=[
                PolicyRule(rule_id="deny-delete", match_tool="delete_file", match_origin="*", decision=False),
                PolicyRule(rule_id="allow-all", match_tool="*", match_origin="*", decision=True),
            ]
        )
        decision = ordered.evaluate(
            ActionRequest(tool="delete_file", arguments={}, origin="user", session_id=1)
        )
        if decision.allowed or decision.rule_id != "deny-delete":
            problems.append("first-match-wins violated for specific deny rule")
        # 4) malformed arguments rejected
        decision = permissive.evaluate(
            ActionRequest(tool="read_file", arguments="not-a-dict", origin="agent", session_id=1)
        )
        if decision.allowed:
            problems.append("malformed (non-dict) arguments allowed")
    except NotImplementedError:
        pending.append("evaluate() not implemented (Task C)")
        return problems, pending
    except Exception as exc:  # gate must never crash on a broken impl
        problems.append(f"evaluate() raised unexpected error: {type(exc).__name__}: {exc}")
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
