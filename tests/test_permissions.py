"""Task C unit tests: every deny rule_id has a proving test (SPEC evidence)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.permissions import ActionRequest, PermissionEngine, PolicyRule  # noqa: E402


def make_engine(permissive: bool = False) -> PermissionEngine:
    rules = None
    if permissive:
        rules = [
            PolicyRule(rule_id="allow-read-agent", match_tool="read_file", match_origin="*", decision=True)
        ]
    return PermissionEngine(rules=rules)


class DefaultDenyTests(unittest.TestCase):
    def test_no_rules_denies_with_default_deny_id(self):
        decision = make_engine().evaluate(
            ActionRequest(tool="speak", arguments={}, origin="user", session_id=1)
        )
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.rule_id, "default-deny")

    def test_unknown_tool_denied_even_with_rule_for_other_tool(self):
        engine = PermissionEngine(
            rules=[PolicyRule(rule_id="allow-speak", match_tool="speak", match_origin="*", decision=True)]
        )
        decision = engine.evaluate(
            ActionRequest(tool="delete_file", arguments={}, origin="user", session_id=1)
        )
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.rule_id, "default-deny")


class InjectionResistanceTests(unittest.TestCase):
    def test_relative_escape_denied_despite_permissive_rule(self):
        decision = make_engine(permissive=True).evaluate(
            ActionRequest(tool="read_file", arguments={"path": "../secrets.env"}, origin="agent", session_id=1)
        )
        self.assertFalse(decision.allowed)

    def test_absolute_path_denied_despite_permissive_rule(self):
        for path in ("C:/Windows/win.ini", "/etc/passwd", "~/ssh-keys"):
            decision = make_engine(permissive=True).evaluate(
                ActionRequest(tool="read_file", arguments={"path": path}, origin="agent", session_id=1)
            )
            self.assertFalse(decision.allowed, path)

    def test_windows_backslash_traversal_denied(self):
        decision = make_engine(permissive=True).evaluate(
            ActionRequest(tool="read_file", arguments={"path": "..\\..\\secrets.env"}, origin="agent", session_id=1)
        )
        self.assertFalse(decision.allowed)

    def test_traversal_hidden_in_nested_arguments_denied(self):
        decision = make_engine(permissive=True).evaluate(
            ActionRequest(tool="read_file", arguments={"nested": {"p": "a/../b"}}, origin="agent", session_id=1)
        )
        self.assertFalse(decision.allowed)


class RuleHitTests(unittest.TestCase):
    def test_matching_rule_returns_its_rule_id(self):
        decision = make_engine(permissive=True).evaluate(
            ActionRequest(tool="read_file", arguments={"path": "notes.txt"}, origin="agent", session_id=1)
        )
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.rule_id, "allow-read-agent")

    def test_first_match_wins_over_later_wildcard(self):
        engine = PermissionEngine(
            rules=[
                PolicyRule(rule_id="deny-delete", match_tool="delete_file", match_origin="*", decision=False),
                PolicyRule(rule_id="allow-all", match_tool="*", match_origin="*", decision=True),
            ]
        )
        decision = engine.evaluate(
            ActionRequest(tool="delete_file", arguments={}, origin="user", session_id=1)
        )
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.rule_id, "deny-delete")


class MalformedRequestTests(unittest.TestCase):
    def test_non_dict_arguments_denied(self):
        decision = make_engine(permissive=True).evaluate(
            ActionRequest(tool="read_file", arguments="not-a-dict", origin="agent", session_id=1)
        )
        self.assertFalse(decision.allowed)


if __name__ == "__main__":
    unittest.main()
