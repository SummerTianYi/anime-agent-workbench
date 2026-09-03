"""Task E unit tests: schema validity, allow-list, traversal rejection."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.tools_registry import ToolRegistry, ToolSpec  # noqa: E402

SCHEMA = {
    "type": "object",
    "properties": {"path": {"type": "string"}},
    "required": ["path"],
}


def make_registry(root: str) -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(ToolSpec(name="read_file", description="read a file", root=root, schema=SCHEMA))
    return registry


class SchemaTests(unittest.TestCase):
    def test_openai_schema_format(self):
        with tempfile.TemporaryDirectory() as tmp:
            schema = make_registry(tmp).openai_schema()
            self.assertEqual(len(schema), 1)
            entry = schema[0]
            self.assertEqual(entry["type"], "function")
            fn = entry["function"]
            self.assertEqual(fn["name"], "read_file")
            self.assertIn("parameters", fn)


class AllowListTests(unittest.TestCase):
    def test_inside_root_readable(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "notes.txt").write_text("hello", encoding="utf-8")
            result = make_registry(tmp).execute("read_file", {"path": "notes.txt"})
            self.assertTrue(result.ok)
            self.assertEqual(result.content, "hello")

    def test_subdirectory_inside_root_readable(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "sub").mkdir()
            Path(tmp, "sub", "a.txt").write_text("deep", encoding="utf-8")
            result = make_registry(tmp).execute("read_file", {"path": "sub/a.txt"})
            self.assertTrue(result.ok)
            self.assertEqual(result.content, "deep")


class TraversalRejectionTests(unittest.TestCase):
    def test_relative_escape_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            outside = Path(tmp).parent / "outside.txt"
            outside.write_text("SECRET", encoding="utf-8")
            try:
                for raw in ("../outside.txt", "..\\outside.txt", "a/../outside.txt"):
                    result = make_registry(tmp).execute("read_file", {"path": raw})
                    self.assertFalse(result.ok, raw)
                    self.assertNotIn("SECRET", result.content)
            finally:
                outside.unlink(missing_ok=True)

    def test_absolute_path_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            for raw in ("C:/Windows/win.ini", "/etc/passwd", "~/ssh-keys"):
                result = make_registry(tmp).execute("read_file", {"path": raw})
                self.assertFalse(result.ok, raw)

    def test_missing_and_empty_paths_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry = make_registry(tmp)
            for arguments in ({}, {"path": ""}, {"path": None}, {"path": 123}):
                self.assertFalse(registry.execute("read_file", arguments).ok, arguments)


class RegistryDisciplineTests(unittest.TestCase):
    def test_unknown_tool_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = make_registry(tmp).execute("no_such_tool", {"path": "a.txt"})
            self.assertFalse(result.ok)

    def test_non_dict_arguments_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = make_registry(tmp).execute("read_file", "not-a-dict")
            self.assertFalse(result.ok)


if __name__ == "__main__":
    unittest.main()
