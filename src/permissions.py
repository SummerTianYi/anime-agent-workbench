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


class PermissionEngine:
    """Evaluates action requests against an ordered rule list.

    Deny by default: no matching rule -> deny("default-deny").
    """

    def __init__(self, rules: list[PolicyRule] | None = None) -> None:
        self.rules = list(rules or [])

    def evaluate(self, request: ActionRequest) -> PolicyDecision:
        raise NotImplementedError("Task C: implement evaluate()")
