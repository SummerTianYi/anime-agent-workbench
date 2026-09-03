"""Task B unit tests: retrieval quality incl. held-out items beyond the golden set."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.memory_store import MemoryStore, retrieve_relevant, score_retrieval  # noqa: E402

# held-out items deliberately NOT in the gate's golden set: if the retriever
# were overfit to golden, these would expose it.
HELD_OUT = [
    {"query": "用户害怕什么", "stored": ["用户怕黑", "用户爱吃苹果"], "relevant": ["用户怕黑"]},
    {"query": "用户家住哪里", "stored": ["用户住在上海", "用户在写小说"], "relevant": ["用户住在上海"]},
    {"query": "用户用什么编程语言", "stored": ["用户常用Python", "用户每天跑步"], "relevant": ["用户常用Python"]},
    {"query": "用户的车是什么牌子", "stored": ["用户的车是比亚迪", "用户嗓音很好听"], "relevant": ["用户的车是比亚迪"]},
]


class GoldenRetrievalTests(unittest.TestCase):
    def test_score_retrieval_meets_threshold(self):
        import importlib.util

        spec = importlib.util.spec_from_file_location("g1_memory", REPO / "acceptance/gates/g1_memory.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        result = score_retrieval(module.GOLDEN)
        self.assertIsNotNone(result)
        self.assertGreaterEqual(result["precision"], 0.8)
        self.assertGreaterEqual(result["recall"], 0.8)


class HeldOutRetrievalTests(unittest.TestCase):
    def test_generalizes_beyond_golden(self):
        result = score_retrieval(HELD_OUT)
        self.assertGreaterEqual(result["precision"], 0.8, str(result["per_item"]))
        self.assertGreaterEqual(result["recall"], 0.8, str(result["per_item"]))


class RetrievalBehaviorTests(unittest.TestCase):
    def test_empty_stored_returns_empty(self):
        self.assertEqual(retrieve_relevant("任何问题", []), [])

    def test_no_lexical_signal_falls_back_deterministically(self):
        self.assertEqual(retrieve_relevant("完全无关的词", ["甲", "乙"]), ["甲"])


class ConsolidationTests(unittest.TestCase):
    def test_recall_limit_and_global_scope_coexist(self):
        store = MemoryStore()
        try:
            for i in range(15):
                store.add(f"会话事实{i}", session_id=1)
            store.add("全局事实", session_id=99, scope="global")
            visible = [f.fact for f in store.recall(session_id=1, limit=10)]
            self.assertLessEqual(len(visible), 10)
            self.assertIn("全局事实", visible)  # global rows survive the limit
        finally:
            store.close()


if __name__ == "__main__":
    unittest.main()
