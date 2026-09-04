# main-repo-target: services/agent-core/agent_core/permissions.py (new module)
"""Task C working file: the tool/action permission layer (deny by default).

Skeleton. Task C implements PermissionEngine.evaluate per
tasks/C-permission-layer/SPEC.md; gate g1_permissions flips PENDING -> PASS.
Keep stdlib-only.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ActionRequest:
    tool: str
    arguments: dict
    origin: str  # "user" | "agent" | "schedule"
    session_id: int


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    allowed: bool
    rule_id: str
    reason: str = ""


@dataclass(frozen=True, slots=True)
class PolicyRule:
    rule_id: str
    match_tool: str  # exact name or "*"
    match_origin: str  # exact origin or "*"
    decision: bool
    note: str = ""
    constraints: tuple = field(default=())


def _path_escape(value: str) -> bool:
    """True if the string smells like a path that leaves its sandbox.

    Absolute (drive letter, leading slash, ~) or any '..' path segment.
    Backslashes are normalized so Windows-style escapes are caught too.
    """
    v = value.replace("\\", "/")
    if v.startswith("/") or v.startswith("~"):
        return True
    if len(v) >= 2 and v[1] == ":":
        return True
    return ".." in v.split("/")


def _iter_strings(arguments: dict):
    for value in arguments.values():
        if isinstance(value, str):
            yield value
        elif isinstance(value, dict):
            yield from _iter_strings(value)
        elif isinstance(value, (list, tuple)):
            for item in value:
                if isinstance(item, str):
                    yield item


class PermissionEngine:
    """Evaluates action requests against an ordered rule list.

    First matching rule wins (rules are ordered); a rule hit returns its
    rule_id so every decision is attributable. Two hard denials sit above
    the rule list and cannot be allow-listed away:

    - malformed-request: arguments is not a dict
    - path-safety: any string argument looks absolute or traverses ('..')

    Deny by default: no matching rule -> deny("default-deny").
    """

    def __init__(self, rules: list[PolicyRule] | None = None) -> None:
        self.rules = list(rules or [])

    def evaluate(self, request: ActionRequest) -> PolicyDecision:
        if not isinstance(request.arguments, dict):
            return PolicyDecision(False, "malformed-request", "arguments must be a dict")
        for value in _iter_strings(request.arguments):
            if _path_escape(value):
                return PolicyDecision(
                    False, "path-safety", "absolute path or '..' traversal in arguments"
                )
        for rule in self.rules:
            tool_ok = rule.match_tool == "*" or rule.match_tool == request.tool
            origin_ok = rule.match_origin == "*" or rule.match_origin == request.origin
            if tool_ok and origin_ok:
                for constraint in rule.constraints:
                    if constraint == "no_absolute_path" or constraint == "no_traversal":
                        for value in _iter_strings(request.arguments):
                            if _path_escape(value):
                                return PolicyDecision(
                                    False,
                                    f"constraint:{rule.rule_id}",
                                    f"violated constraint {constraint}",
                                )
                return PolicyDecision(
                    rule.decision, rule.rule_id, rule.note or ("allowed" if rule.decision else "denied by rule")
                )
        return PolicyDecision(False, "default-deny", "no matching rule")
