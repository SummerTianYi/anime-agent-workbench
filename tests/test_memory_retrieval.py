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

# GOLDEN 直接 import 冻结闸门而非复制，避免两份数据静默失同步；
# acceptance.gates 无 __init__.py，靠命名空间包机制导入（test_workbench 同法）
from acceptance.gates.g1_memory import GOLDEN  # noqa: E402

# 留出验证集：与 golden 同覆盖 8 个语义类，但表层用词刻意错开
# （城市用成都/常驻、职业用设计师、宠物用乌龟/动物、过敏用海鲜……）。
# 反过拟合约束：不许为迁就实现修改本集，不达标即回炉改设计。
HOLDOUT_GOLDEN: list[dict[str, list[str] | str]] = [
    {"query": "用户喜欢什么颜色", "stored": ["用户最喜欢蓝色", "用户常驻上海"], "relevant": ["用户最喜欢蓝色"]},
    {"query": "用户住在哪个城市", "stored": ["用户常驻上海", "用户不喜欢吃香菜"], "relevant": ["用户常驻上海"]},
    {"query": "用户的昵称是什么", "stored": ["用户让大家叫他阿豪", "用户讨厌加班"], "relevant": ["用户让大家叫他阿豪"]},
    {"query": "用户是什么时候出生的", "stored": ["用户的生日在3月8日", "用户住在北京"], "relevant": ["用户的生日在3月8日"]},
    {"query": "用户养了什么动物", "stored": ["用户养了一只乌龟", "用户对海鲜过敏"], "relevant": ["用户养了一只乌龟"]},
    {"query": "用户吃不了什么", "stored": ["用户对海鲜过敏", "用户是一名厨师"], "relevant": ["用户对海鲜过敏"]},
    {"query": "用户做什么工作", "stored": ["用户是平面设计师", "用户早上喜欢去游泳"], "relevant": ["用户是平面设计师"]},
    {"query": "用户有什么兴趣", "stored": ["用户热爱摄影", "用户这周一直在追剧"], "relevant": ["用户热爱摄影"]},
    {"query": "用户常驻哪座城市", "stored": ["用户在成都生活", "用户特别喜欢蓝色"], "relevant": ["用户在成都生活"]},
    {"query": "用户做什么职业", "stored": ["用户是中学教师", "用户刚换了新手机"], "relevant": ["用户是中学教师"]},
    {"query": "用户平时喜欢做什么", "stored": ["用户空下来喜欢唱歌", "用户今天在开会"], "relevant": ["用户空下来喜欢唱歌"]},
    {"query": "用户平时怎么称呼", "stored": ["用户希望被称呼为老师", "用户喜欢红色"], "relevant": ["用户希望被称呼为老师"]},
]


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


class ConceptBridgeTests(unittest.TestCase):
    """L3: lexicon bridging for queries with no literal overlap."""

    def test_same_class_hits_positive(self):
        # 「用户的职业」与「用户是后端工程师」零字面重叠，全靠词典桥接
        self.assertGreater(mr.concept_bridge("用户的职业", "用户是后端工程师"), 0.0)
        self.assertGreater(mr.concept_bridge("用户的爱好", "用户周末喜欢徒步"), 0.0)
        self.assertGreater(mr.concept_bridge("用户养的宠物", "用户养了一只猫"), 0.0)

    def test_head_only_hit_still_bridges(self):
        # 查询命中 head、事实只命中 member（甚至反之）都必须能桥接
        self.assertGreater(mr.concept_bridge("用户在哪座城市", "用户在杭州工作"), 0.0)

    def test_unrelated_is_zero(self):
        self.assertEqual(mr.concept_bridge("用户的职业", "用户最喜欢的颜色是蓝色"), 0.0)
        self.assertEqual(mr.concept_bridge("用户的生日", "用户养了一只猫"), 0.0)
        self.assertEqual(mr.concept_bridge("今天天气怎么样", "用户在杭州工作"), 0.0)

    def test_one_sided_hit_is_zero(self):
        # 只有一侧命中不构成桥：查询问宠物、事实只谈颜色时得 0，
        # 否则任何含「用户」的事实都会因单边命中拿到噪声分
        self.assertEqual(mr.concept_bridge("用户养的宠物", "用户最喜欢的颜色是蓝色"), 0.0)

    def test_more_shared_hits_score_higher(self):
        # 双方在同一类里命中的词越多，桥接信号越强（单调性）
        weak = mr.concept_bridge("用户在哪座城市", "用户在杭州")
        strong = mr.concept_bridge("用户在哪座城市", "用户住在杭州市")
        self.assertGreater(strong, weak)

    def test_range_zero_to_one(self):
        score = mr.concept_bridge("用户的爱好", "用户周末喜欢徒步登山")
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)

    def test_lexicon_covers_eight_classes(self):
        self.assertEqual(len(mr.CONCEPT_LEXICON), 8)

    def test_lexicon_generality_against_golden(self):
        # 反过拟合硬约束（机器可验证）：每个语义类至少 3 个 member
        # 从未出现在 golden 集任何位置（query/stored/relevant 全算）。
        # 这保证词典不是「golden 答案换皮」，而是通用概念知识。
        corpus = mr.normalize(
            "".join(
                str(item["query"]) + "".join(item["stored"]) + "".join(item["relevant"])
                for item in GOLDEN
            )
        )
        for concept in mr.CONCEPT_LEXICON.values():
            unseen = [w for w in concept.member if mr.normalize(w) not in corpus]
            self.assertGreaterEqual(
                len(unseen),
                3,
                f"concept class {concept.name!r} has fewer than 3 members unseen in golden: {unseen}",
            )


if __name__ == "__main__":
    unittest.main()
