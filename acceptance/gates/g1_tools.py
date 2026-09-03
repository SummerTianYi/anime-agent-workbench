"""Gate 1d (Task E): read-only tool registry - allow-list + traversal rejection.

Behavioral checks (hardened by Task E per tasks/E-readonly-tools/SPEC.md):
1. openai_schema() is well-formed OpenAI function-calling format
2. a file inside the registered root is readable
3. traversal ('..', '..\\') and absolute paths are rejected - including a file
   that actually exists outside the root (no leak)
4. unknown tools and non-dict arguments are rejected
The root is a throwaway temp dir; an outside file is planted to prove escape
attempts do not leak its content.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from src.tools_registry import ToolRegistry, ToolSpec  # noqa: E402

SCHEMA = {
    "type": "object",
    "properties": {"path": {"type": "string", "description": "relative path inside the tool root"}},
    "required": ["path"],
}

REJECT_CASES = [
    {"path": "../outside.txt"},
    {"path": "..\\outside.txt"},
    {"path": "a/../outside.txt"},
    {"path": "C:/Windows/win.ini"},
    {"path": "/etc/passwd"},
    {"path": "~/ssh-keys"},
    {"path": ""},
    {"path": None},
]


def run():
    problems = []
    pending = []
    try:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "notes.txt").write_text("inside-content", encoding="utf-8")
            outside = root.parent / "outside.txt"
            outside.write_text("SECRET-OUTSIDE", encoding="utf-8")
            try:
                registry = ToolRegistry()
                registry.register(ToolSpec(name="read_file", description="read a file", root=str(root), schema=SCHEMA))

                # 1) schema well-formed
                schema = registry.openai_schema()
                if not isinstance(schema, list) or not schema:
                    problems.append("openai_schema() must return a non-empty list")
                else:
                    for entry in schema:
                        fn = (entry or {}).get("function", {})
                        if entry.get("type") != "function":
                            problems.append("schema entry type must be 'function'")
                        for key in ("name", "description", "parameters"):
                            if key not in fn:
                                problems.append(f"schema function missing {key!r}")

                # 2) inside-root read works
                result = registry.execute("read_file", {"path": "notes.txt"})
                if not result.ok:
                    problems.append(f"inside-root read failed: {result.summary}")
                elif result.content != "inside-content":
                    problems.append("inside-root read returned wrong content")

                # 3) traversal / absolute rejection - outside file must not leak
                for arguments in REJECT_CASES:
                    result = registry.execute("read_file", arguments)
                    if result.ok:
                        problems.append(f"escape allowed: {arguments!r}")
                    elif "SECRET-OUTSIDE" in result.content:
                        problems.append(f"outside content leaked via {arguments!r}")

                # 4) unknown tool / malformed arguments
                if registry.execute("no_such_tool", {"path": "notes.txt"}).ok:
                    problems.append("unknown tool allowed")
                if registry.execute("read_file", "not-a-dict").ok:
                    problems.append("non-dict arguments allowed")

                # 5) symlink probe: a path that validates cleanly but resolves
                #    outside the root is caught only by root containment.
                #    Skipped where symlink creation is not permitted (Windows
                #    without developer mode) - not a failure.
                link = root / "link.txt"
                try:
                    link.symlink_to(outside)
                except OSError:
                    link = None
                if link is not None:
                    result = registry.execute("read_file", {"path": "link.txt"})
                    if result.ok and "SECRET-OUTSIDE" in result.content:
                        problems.append("symlink escape leaked outside content")
            finally:
                outside.unlink(missing_ok=True)
    except NotImplementedError:
        pending.append("openai_schema/execute not implemented (Task E)")
        return problems, pending
    except Exception as exc:  # gate must never crash on a broken impl
        problems.append(f"registry raised unexpected error: {type(exc).__name__}: {exc}")
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
