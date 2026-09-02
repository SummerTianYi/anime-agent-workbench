"""Workbench self-tests (stdlib unittest)."""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from acceptance.evals.providers import MockProvider  # noqa: E402
from acceptance.gates.g1_contract import parse_contract  # noqa: E402


class MockProviderTests(unittest.TestCase):
    def test_missing_fact_triggers_marker(self):
        from src.prompt_persona.system_prompt import ACTIVE_SYSTEM_PROMPT, REQUIRED_IDENTITY_FACTS

        provider = MockProvider(required_facts=REQUIRED_IDENTITY_FACTS)
        messages = [
            {"role": "system", "content": "空提示词"},
                {"role": "user", "content": "你是谁"},
        ]
        result = provider.complete(messages)
        self.assertIn("PROMPT_MISSING", result.text)


class ParseContractTests(unittest.TestCase):
    def test_plain_and_fenced_json_parse(self):
        good = '{"reply": "hi", "emotion": "neutral", "emotion_intensity": 0.3, "gesture": "none", "memory_candidate": null}'
        self.assertIsNotNone(parse_contract(good))
        fenced = "```json" + chr(10) + good + chr(10) + "```"
        self.assertIsNotNone(parse_contract(fenced))
        self.assertIsNone(parse_contract("not json"))


class MemoryRoundtripTests(unittest.TestCase):
    def test_roundtrip_isolation_persistence(self):
        from src.memory_store import MemoryStore

        store = MemoryStore()
        store.add("用户最喜欢的颜色是蓝色", session_id=1)
        store.add("全局事实", session_id=99, scope="global")
        visible = [f.fact for f in store.recall(session_id=1)]
        self.assertIn("用户最喜欢的颜色是蓝色", visible)
        self.assertIn("全局事实", visible)
        other = [f.fact for f in store.recall(session_id=2)]
        self.assertNotIn("用户最喜欢的颜色是蓝色", other)
        store.close()
        store2 = MemoryStore(store.path)
        persisted = [f.fact for f in store2.recall(session_id=1)]
        self.assertIn("用户最喜欢的颜色是蓝色", persisted)
        store2.close()
