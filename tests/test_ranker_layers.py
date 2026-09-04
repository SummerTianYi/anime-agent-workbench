"""Task B retrieval tests: the five scoring layers, composition and rank().

Split out of tests/test_memory_retrieval.py by N4 (that file had grown to 798
lines against the 800-line ceiling). This is a pure move: no assertion, no test
name and no test count changed.

Coverage map mirrors the five-layer model in src/memory_ranker.py:
normalize (L1) / bigram_similarity (L2) / concept_bridge (L3) /
preference_bonus (L4) / transient_penalty (L5), plus score composition, rank()
and the profile precompute cache. Corpus-level checks (score_retrieval) and the
MemoryStore integration live in tests/test_memory_retrieval.py; lexicon
semantics and polarity live in tests/test_lexicon_polarity.py.
"""
from __future__ import annotations

import sys
import time
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from src import memory_ranker as mr  # noqa: E402

# GOLDEN 直接 import 冻结闸门而非复制，避免两份数据静默失同步；
# acceptance.gates 无 __init__.py，靠命名空间包机制导入（test_workbench 同法）
from acceptance.gates.g1_memory import GOLDEN  # noqa: E402


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

    def test_proportional_multisets_score_one(self):
        # 审查发现 M3 的契约锁定：余弦对成比例的 n-gram 多重集恒为 1.0，
        # 而归一化后的字符串并不相等。处置选「改契约」而不是「改实现」
        # （长度阻尼会把 L2 从内容探测器变成长度探测器，系统性惩罚「查询
        # 短、事实长」这一常态形态），所以这里锁定的是真实性质
        self.assertNotEqual(mr.normalize("哈哈"), mr.normalize("哈哈哈哈"))
        self.assertEqual(mr.bigram_similarity("哈哈", "哈哈哈哈"), 1.0)
        self.assertEqual(mr.bigram_similarity("aaa", "aaaaaa"), 1.0)
        self.assertEqual(mr.bigram_similarity("猫", "猫猫猫猫"), 1.0)
        # 不成比例就不为 1.0（插字改变了分布）
        self.assertLess(mr.bigram_similarity("蓝色", "蓝蓝蓝蓝色色"), 1.0)


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
        strong = mr.concept_bridge("用户在哪座城市", "用户在北京和上海都住过")
        # M1 去掉单字 head「市」后，「杭州市」只贡献 member「杭州」一个命中，
        # 不能再用它做强侧样例；改用命中两个 member 的事实验证单调性
        self.assertGreater(strong, weak)

    def test_range_zero_to_one(self):
        score = mr.concept_bridge("用户的爱好", "用户周末喜欢徒步登山")
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)

    def test_lexicon_covers_at_least_eight_classes(self):
        # 审查发现 L5：写死 assertEqual(…, 8) 会把「新增一个语义类」变成
        # 测试失败，而词典扩充恰恰是预期的演进方向；断言下限才能既锁住
        # 「八个类一个都不能少」又不阻止生长
        self.assertGreaterEqual(len(mr.CONCEPT_LEXICON), 8)

    def test_concept_bridge_is_symmetric(self):
        # 审查发现 L5：原来只测了单向桥接。concept_bridge 对两侧用同一本
        # 词典、同一个 sqrt(qh*fh) 与同一组参与均值的双侧命中类，所以它必须
        # 对称；不对称就意味着某一侧走了不同的命中口径，会直接影响
        # recall_relevant 与 score_retrieval 的可重复性
        pairs = [
            ("用户在哪座城市", "用户在杭州工作"),
            ("用户的职业", "用户是后端工程师"),
            ("用户养的宠物", "用户养了一只猫"),
            ("用户的生日", "用户的生日是7月12日"),
            ("用户的职业", "用户最喜欢的颜色是蓝色"),
        ]
        for left, right in pairs:
            self.assertEqual(mr.concept_bridge(left, right), mr.concept_bridge(right, left))
        self.assertGreater(mr.concept_bridge(pairs[0][0], pairs[0][1]), 0.0)

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


class PreferenceBonusTests(unittest.TestCase):
    """L4: preference assertions strengthen stable-attribute evidence only."""

    def test_marker_in_fact_scores_under_stable_query(self):
        # 「用户的爱好」是稳定属性提问（含 head 词「爱好」），
        # 「喜欢」类调词是偏好的显式断言，应加分
        self.assertGreater(mr.preference_bonus("用户的爱好", "用户周末喜欢徒步"), 0.0)
        self.assertGreater(mr.preference_bonus("怎么称呼用户", "用户希望被称呼为老板"), 0.0)

    def test_no_effect_for_non_stable_query(self):
        # 查询不含任何 head 词（问的是行为而非属性）时，L4 必须静默：
        # 否则闲聊查询也会被带偏好词的事实抢位
        self.assertEqual(mr.preference_bonus("用户周末一般干嘛", "用户周末喜欢徒步"), 0.0)

    def test_marker_free_fact_scores_zero(self):
        self.assertEqual(mr.preference_bonus("用户的爱好", "用户是后端工程师"), 0.0)

    def test_saturates_at_one(self):
        score = mr.preference_bonus("用户的爱好", "用户最喜欢也最热爱徒步")
        self.assertGreater(score, 0.0)
        self.assertLessEqual(score, 1.0)


class TransientPenaltyTests(unittest.TestCase):
    """L5: tense markers demote short-term states under stable queries only."""

    def test_marker_in_fact_penalized_under_stable_query(self):
        # golden 把「用户最近在健身」排除在「用户的爱好」正确答案外：
        # 稳定属性提问下，带时态标记的短期状态应被降权
        self.assertGreater(mr.transient_penalty("用户的爱好", "用户最近在健身"), 0.0)
        self.assertGreater(mr.transient_penalty("用户的职业", "用户今天在公司加班"), 0.0)

    def test_no_effect_for_non_stable_query(self):
        # 非稳定属性提问（不含 head 词）时不扣分：问「最近干嘛」时
        # 带「最近」的事实恰恰是对题的，不该被惩罚
        self.assertEqual(mr.transient_penalty("用户周末一般干嘛", "用户最近在健身"), 0.0)

    def test_marker_free_fact_scores_zero(self):
        self.assertEqual(mr.transient_penalty("用户的爱好", "用户周末喜欢徒步"), 0.0)

    def test_saturates_at_one(self):
        score = mr.transient_penalty("用户的爱好", "用户最近今天一直在健身")
        self.assertGreater(score, 0.0)
        self.assertLessEqual(score, 1.0)

    def test_stable_gate_keys_on_head_words(self):
        # 门控判定暴露为私有函数以便直接测：head 词命中即稳定属性提问
        self.assertTrue(mr._is_stable_attribute_query("用户的爱好"))
        self.assertTrue(mr._is_stable_attribute_query("用户在哪座城市"))
        self.assertFalse(mr._is_stable_attribute_query("用户周末一般干嘛"))
        self.assertFalse(mr._is_stable_attribute_query(""))
        # 审查发现 M1：单字 head（色/市）做子串命中，会让「超市/角色/脸色/
        # 色号」被误判成稳定属性提问，L5 随即反噬对题的近期事实
        self.assertFalse(mr._is_stable_attribute_query("用户最近去超市买了什么"))
        self.assertFalse(mr._is_stable_attribute_query("用户最近在追哪个角色"))
        self.assertFalse(mr._is_stable_attribute_query("用户今天脸色怎么样"))
        self.assertFalse(mr._is_stable_attribute_query("用户喜欢什么色号"))


class ScoreCompositionTests(unittest.TestCase):
    """合成层：四层信号按全局权重线性叠加。"""

    def test_matches_layer_formula(self):
        query, fact = "用户的爱好", "用户周末喜欢徒步"
        expected = (
            mr.W_BIGRAM * mr.bigram_similarity(query, fact)
            + mr.W_CONCEPT * mr.concept_bridge(query, fact)
            + mr.W_PREFERENCE * mr.preference_bonus(query, fact)
            - mr.W_TRANSIENT * mr.transient_penalty(query, fact)
        )
        self.assertAlmostEqual(mr.score(query, fact), expected, places=12)

    def test_transient_marker_lowers_score_under_stable_query(self):
        plain = mr.score("用户的爱好", "用户周末喜欢徒步")
        transient = mr.score("用户的爱好", "用户最近喜欢徒步")
        self.assertGreater(plain, transient)

    def test_preference_assertion_raises_score_under_stable_query(self):
        with_marker = mr.score("用户的爱好", "用户喜欢徒步")
        without = mr.score("用户的爱好", "用户周末徒步")
        self.assertGreater(with_marker, without)


class RankTests(unittest.TestCase):
    """排序层：降序 + 同分按原序（稳定排序）+ 全量返回。"""

    def test_descending_by_score(self):
        ranked = mr.rank("用户养的宠物", ["用户最喜欢的颜色是蓝色", "用户养了一只猫"])
        self.assertEqual(ranked[0][0], "用户养了一只猫")
        self.assertGreaterEqual(ranked[0][1], ranked[1][1])

    def test_stable_tie_keeps_input_order(self):
        # 两条同分事实必须按入参原序返回，保证结果可复现可测试
        ranked = mr.rank("无关提问", ["事实甲", "事实乙", "事实丙"])
        self.assertEqual([text for text, _ in ranked], ["事实甲", "事实乙", "事实丙"])
        self.assertEqual(len({s for _, s in ranked}), 1)

    def test_returns_full_list_with_scores(self):
        candidates = ["用户是后端工程师", "用户最近在健身", "用户周末喜欢徒步"]
        ranked = mr.rank("用户的爱好", candidates)
        self.assertEqual(len(ranked), 3)
        self.assertEqual({text for text, _ in ranked}, set(candidates))
        for _, value in ranked:
            self.assertIsInstance(value, float)

    def test_empty_candidates(self):
        self.assertEqual(mr.rank("用户的爱好", []), [])

    def test_golden_hard_pair_prefers_stable_hobby(self):
        # golden 最难对：稳定爱好断言必须压过带时态标记的短期健身
        ranked = mr.rank("用户的爱好", ["用户是后端工程师", "用户最近在健身", "用户周末喜欢徒步"])
        self.assertEqual(ranked[0][0], "用户周末喜欢徒步")


class RankPrecomputeTests(unittest.TestCase):
    """审查发现 M6：每个 candidate 重复归一化 query 并重建 Counter。

    score() 内 4 个层函数各自独立调 normalize(query)，bigram_similarity 每次
    重建 query 的 Counter。本机复现 500 candidates：短 query 下 rank() 从
    150.9 ms 降到 15.2 ms；query 拉到 100000 字符时旧实现要 72.70 s（已接近
    run_all.py 的 120 s 硬超时，candidate 再涨一个量级就撞穿），截断后一律
    15.8 ms。这里用 normalize 调用计数作主锁，计时只作数量级参考，避免在慢
    机器上 flaky。
    """

    QUERY = "用户喜欢什么颜色"
    CANDIDATES = ["用户最喜欢的颜色是蓝色", "用户在杭州工作", "用户养了一只猫", "用户讨厌蓝色"]

    def test_precomputed_path_matches_layer_formula_exactly(self):
        context = mr._query_context(self.QUERY)
        for fact in self.CANDIDATES:
            expected = (
                mr.W_BIGRAM * mr.bigram_similarity(self.QUERY, fact)
                + mr.W_CONCEPT * mr.concept_bridge(self.QUERY, fact)
                + mr.W_PREFERENCE * mr.preference_bonus(self.QUERY, fact)
                - mr.W_TRANSIENT * mr.transient_penalty(self.QUERY, fact)
            )
            # 容差 0：预计算路径与逐次计算路径必须逐位相同
            self.assertEqual(mr._score_with_context(context, fact), mr.score(self.QUERY, fact))
            self.assertEqual(mr.score(self.QUERY, fact), expected)

    def test_query_normalized_once_per_rank_call(self):
        seen: list[str] = []
        real = mr.normalize
        with mock.patch.object(mr, "normalize", lambda text: (seen.append(text), real(text))[1]):
            mr.rank(self.QUERY, self.CANDIDATES * 10)
        self.assertEqual(seen.count(self.QUERY), 1)
        # 锁数量级：旧实现是 8 次/candidate，现在每条 candidate 只归一化一次
        self.assertLessEqual(len(seen), 2 + len(self.CANDIDATES) * 10)

    def test_overlong_query_is_truncated_at_module_cap(self):
        padded = self.QUERY + "无关填充" * 400
        capped = padded[: mr._MAX_QUERY_CHARS]
        self.assertEqual(mr.score(padded, self.CANDIDATES[0]), mr.score(capped, self.CANDIDATES[0]))
        self.assertEqual(mr.rank(padded, self.CANDIDATES), mr.rank(capped, self.CANDIDATES))

    def test_rank_scale_is_bounded(self):
        # 锁数量级而不是绝对毫秒数：阈值刻意宽松（实测应在几十毫秒级），
        # 慢机器上不 flaky；它的目的是让 8 倍重复归一化回潮时直接爆阈值
        query = self.QUERY * 250
        candidates = [f"{fact}{index}" for index, fact in enumerate(self.CANDIDATES * 50)]
        started = time.perf_counter()
        mr.rank(query, candidates)
        self.assertLess(time.perf_counter() - started, 5.0)


if __name__ == "__main__":
    unittest.main()
