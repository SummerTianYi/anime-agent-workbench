"""Task B retrieval tests: layer-by-layer ranking + evaluation-metric checks.

Companion to tests/test_workbench.py (roundtrip lives there). Coverage map
mirrors the five-layer model in src/memory_ranker.py plus the store-level
integration (recall_relevant / format_memory_prompt).
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from src import memory_ranker as mr  # noqa: E402


class NormalizeTests(unittest.TestCase):
    """L1: NFKC fold + lowercase + whitespace/punctuation stripping."""

    def test_fullwidth_folds_to_halfwidth(self):
        # ＮＦＫＣ 会把全角字母数字折成半角，这是「7月12日」类事实里
        # 全角/半角混写不影响打分的前提
        self.assertEqual(mr.normalize("ＡＢＣ１２３"), "abc123")

    def test_lowercases_latin(self):
        self.assertEqual(mr.normalize("PyTorch"), "pytorch")

    def test_strips_whitespace_and_punctuation(self):
        self.assertEqual(mr.normalize(" 你 好，世 界!  "), "你好世界")
        self.assertEqual(mr.normalize("a,b.c;:!?\"'()[]{}"), "abc")

    def test_keeps_cjk_characters(self):
        self.assertEqual(mr.normalize("用户喜欢蓝色"), "用户喜欢蓝色")

    def test_empty_string(self):
        self.assertEqual(mr.normalize(""), "")


class BigramSimilarityTests(unittest.TestCase):
    """L2: character-bigram multiset cosine. Boundary matrix required by spec."""

    def test_empty_vs_anything_is_zero(self):
        self.assertEqual(mr.bigram_similarity("", "用户喜欢蓝色"), 0.0)
        self.assertEqual(mr.bigram_similarity("用户喜欢蓝色", ""), 0.0)
        self.assertEqual(mr.bigram_similarity("", ""), 0.0)

    def test_identical_is_one(self):
        self.assertEqual(mr.bigram_similarity("用户喜欢蓝色", "用户喜欢蓝色"), 1.0)

    def test_disjoint_is_zero(self):
        self.assertEqual(mr.bigram_similarity("蓝色天空", "黑白棋子"), 0.0)

    def test_partial_overlap_between_zero_and_one(self):
        score = mr.bigram_similarity("用户喜欢的颜色", "用户最喜欢的颜色是蓝色")
        self.assertGreater(score, 0.0)
        self.assertLess(score, 1.0)

    def test_single_char_degrades_both_sides_to_unigram(self):
        # 任一侧短于 2 字时无 bigram，约定双侧一起退化为 unigram 多重集：
        # 同字为 1.0，异字为 0.0，单字 vs 长串仍有非零重叠
        self.assertEqual(mr.bigram_similarity("猫", "猫"), 1.0)
        self.assertEqual(mr.bigram_similarity("猫", "狗"), 0.0)
        single_vs_long = mr.bigram_similarity("猫", "用户养了一只猫")
        self.assertGreater(single_vs_long, 0.0)
        self.assertLess(single_vs_long, 1.0)

    def test_symmetric(self):
        a = mr.bigram_similarity("用户在哪座城市", "用户在杭州工作")
        b = mr.bigram_similarity("用户在杭州工作", "用户在哪座城市")
        self.assertAlmostEqual(a, b, places=12)

    def test_normalizes_inputs(self):
        # 全角/标点差异不应影响相似度（内部先走 L1 归一化）
        self.assertEqual(
            mr.bigram_similarity("用户，喜欢蓝色！", "用户喜欢蓝色"),
            1.0,
        )


if __name__ == "__main__":
    unittest.main()
