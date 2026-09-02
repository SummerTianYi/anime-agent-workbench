"""Task E working file: read-only tool registry (allow-listed, traversal-safe).

Skeleton. Task E implements the registry per tasks/E-readonly-tools/SPEC.md;
gate g1_tools flips PENDING -> PASS. Keep stdlib-only.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ToolSpec:
    name: str
    description: str
    root: str
    schema: dict


@dataclass(frozen=True, slots=True)
class ToolResult:
    ok: bool
    summary: str
    content: str = ""


class ToolRegistry:
    """Read-only tools with a hard allow-list root per tool."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        self._tools[spec.name] = spec

    def openai_schema(self) -> list[dict]:
        raise NotImplementedError("Task E: implement openai_schema()")

    def execute(self, name: str, arguments: dict) -> ToolResult:
        raise NotImplementedError("Task E: execute() must enforce the allow-list and reject traversal")
