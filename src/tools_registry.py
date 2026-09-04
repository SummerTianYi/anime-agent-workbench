# main-repo-target: services/agent-core/agent_core/tools_registry.py (new module)
"""Task E working file: read-only tool registry (allow-listed, traversal-safe).

Skeleton. Task E implements the registry per tasks/E-readonly-tools/SPEC.md;
gate g1_tools flips PENDING -> PASS. Keep stdlib-only.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

MAX_CONTENT_CHARS = 64_000  # read-only tools must not dump unbounded files


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


def _validate_rel_path(raw) -> str | None:
    """Normalized relative path, or None if the path tries to escape.

    Rejects absolute paths (leading '/', drive letters anywhere via ':', '~'),
    any '..' segment, and empty input. Backslashes are normalized to '/' so
    Windows-style escapes are caught.
    """
    if not isinstance(raw, str):
        return None
    v = raw.replace("\\", "/").strip()
    if not v or v.startswith("/") or v.startswith("~") or ":" in v:
        return None
    parts = [p for p in v.split("/") if p not in ("", ".")]
    if any(p == ".." for p in parts):
        return None
    return "/".join(parts)


class ToolRegistry:
    """Read-only tools with a hard allow-list root per tool.

    The root is fixed at registration time; the model can only supply a
    relative path argument, and every execution re-checks it: absolute or
    traversing paths are rejected before any filesystem access, and the
    resolved target must stay under the resolved root (symlink-safe).
    """

    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        self._tools[spec.name] = spec

    def openai_schema(self) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": spec.name,
                    "description": spec.description,
                    "parameters": spec.schema,
                },
            }
            for spec in self._tools.values()
        ]

    def execute(self, name: str, arguments: dict) -> ToolResult:
        spec = self._tools.get(name)
        if spec is None:
            return ToolResult(False, f"unknown tool: {name}")
        if not isinstance(arguments, dict):
            return ToolResult(False, "malformed-arguments: must be a dict")
        rel = _validate_rel_path(arguments.get("path"))
        if rel is None:
            return ToolResult(False, "invalid-path: absolute or traversing path rejected")
        root = Path(spec.root).resolve()
        target = (root / rel).resolve()
        if target != root and root not in target.parents:
            return ToolResult(False, "invalid-path: resolved outside allow-list root")
        try:
            content = target.read_text(encoding="utf-8")
        except OSError as exc:
            return ToolResult(False, f"read-failed: {exc}")
        if len(content) > MAX_CONTENT_CHARS:
            content = content[:MAX_CONTENT_CHARS]
            return ToolResult(True, f"read {rel} (truncated at {MAX_CONTENT_CHARS} chars)", content)
        return ToolResult(True, f"read {rel}", content)
