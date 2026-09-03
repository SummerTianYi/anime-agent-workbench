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
from src.memory_store import MemoryStore, format_memory_prompt  # noqa: E402

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


class ScoreRetrievalTests(unittest.TestCase):
    """评测口径：top-1 检索 + 宏平均查准/查全（与 g1_memory 同口径）。"""

    def test_golden_set_reaches_threshold(self):
        result = mr.score_retrieval(GOLDEN)
        self.assertIsInstance(result, dict)
        self.assertIsInstance(result["precision"], float)
        self.assertIsInstance(result["recall"], float)
        self.assertGreaterEqual(result["precision"], 0.8)
        self.assertGreaterEqual(result["recall"], 0.8)

    def test_holdout_set_reaches_threshold(self):
        # 留出集不达标即视为过拟合；不许改数据迁就实现
        result = mr.score_retrieval(HOLDOUT_GOLDEN)
        self.assertGreaterEqual(result["precision"], 0.8)
        self.assertGreaterEqual(result["recall"], 0.8)

    def test_perfect_small_set_scores_one(self):
        golden = [
            {"query": "用户养的宠物", "stored": ["用户养了一只猫"], "relevant": ["用户养了一只猫"]},
            {"query": "用户的职业", "stored": ["用户是后端工程师"], "relevant": ["用户是后端工程师"]},
        ]
        result = mr.score_retrieval(golden)
        self.assertAlmostEqual(result["precision"], 1.0)
        self.assertAlmostEqual(result["recall"], 1.0)

    def test_empty_relevant_counts_zero_per_convention(self):
        # 口径约定：relevant 为空时该条 recall 记 0.0（评测集不应出现，
        # 但口径必须确定性）
        golden = [{"query": "用户的宠物", "stored": ["用户养了一只猫"], "relevant": []}]
        result = mr.score_retrieval(golden)
        self.assertEqual(result["recall"], 0.0)


class RecallRelevantTests(unittest.TestCase):
    """存储层集成：检索必须继承 recall() 的 scope 语义（session+global）。"""

    def setUp(self):
        self.store = MemoryStore()
        self.addCleanup(self.store.close)
        self.store.add("用户最喜欢的颜色是蓝色", session_id=1)
        self.store.add("用户在杭州工作", session_id=1)
        self.store.add("全局事实：用户希望被称呼为老板", session_id=999, scope="global")
        self.store.add("用户养了一只猫", session_id=2)

    def test_ranks_by_query_relevance(self):
        facts = self.store.recall_relevant(session_id=1, query="用户喜欢什么颜色")
        self.assertEqual(facts[0].fact, "用户最喜欢的颜色是蓝色")

    def test_limit_caps_result(self):
        facts = self.store.recall_relevant(session_id=1, query="用户喜欢什么颜色", limit=2)
        self.assertEqual(len(facts), 2)

    def test_global_facts_visible(self):
        facts = self.store.recall_relevant(session_id=1, query="怎么称呼用户")
        self.assertEqual(facts[0].fact, "全局事实：用户希望被称呼为老板")

    def test_session_isolation(self):
        # 跨会话零泄漏是 SPEC 硬指标：session 1 无论怎么查都拿不到
        # session 2 的行，即使查询与那条事实高度相关
        facts = self.store.recall_relevant(session_id=1, query="用户养的宠物")
        self.assertNotIn("用户养了一只猫", [f.fact for f in facts])

    def test_empty_query_returns_recent_first(self):
        # 空查询无检索意图，退化为新近优先（与 recall() 默认序一致），
        # 但 scope 过滤仍生效
        facts = self.store.recall_relevant(session_id=1, query="", limit=2)
        self.assertEqual(len(facts), 2)
        self.assertNotIn("用户养了一只猫", [f.fact for f in facts])

    def test_returns_memory_fact_objects(self):
        from src.memory_store import MemoryFact

        facts = self.store.recall_relevant(session_id=1, query="用户的职业")
        self.assertTrue(all(isinstance(f, MemoryFact) for f in facts))


class FormatMemoryPromptTests(unittest.TestCase):
    """prompt 片段格式化：直接作 extra_system 拼接的中文文本。"""

    def _fact(self, text: str, fact_id: int = 1) -> object:
        from src.memory_store import MemoryFact

        return MemoryFact(
            fact_id=fact_id, session_id=1, scope="session", fact=text, source_request_id=""
        )

    def test_empty_list_returns_empty_string(self):
        self.assertEqual(format_memory_prompt([]), "")

    def test_single_fact(self):
        prompt = format_memory_prompt([self._fact("用户最喜欢的颜色是蓝色")])
        self.assertIn("【已知记忆】", prompt)
        self.assertIn("用户最喜欢的颜色是蓝色", prompt)
        # 面向 LLM 的字符串用中文全角标点，与 BASE_SYSTEM_PROMPT 文风一致
        self.assertNotIn(",", prompt)
        self.assertNotIn(":", prompt)

    def test_multiple_facts_keep_order(self):
        prompt = format_memory_prompt(
            [self._fact("用户最喜欢的颜色是蓝色", 2), self._fact("用户在杭州工作", 1)]
        )
        self.assertLess(prompt.index("用户最喜欢的颜色是蓝色"), prompt.index("用户在杭州工作"))

    def test_no_internal_metadata_leaks(self):
        # fact_id / session_id / scope / source_request_id 是存储内部元数据，
        # 泄进 prompt 只会浪费上下文并可能误导模型
        prompt = format_memory_prompt([self._fact("用户在杭州工作", 42)])
        self.assertNotIn("42", prompt)
        self.assertNotIn("session", prompt)
        self.assertNotIn("scope", prompt)


class RecallRelevantDuplicateTextTests(unittest.TestCase):
    """审查发现 H1：重复 fact 文本下按文本反查会把多行归并成同一行。

    facts 表无 UNIQUE 约束，同一文本合法地存在多行（典型场景：同一句
    事实先被归为 global、后又在某会话里重复沉淀）。把 session 行标成
    global 属身份伪造级缺陷，在「跨会话零泄漏」是硬指标的系统里不可接受。
    """

    def setUp(self):
        self.store = MemoryStore()
        self.addCleanup(self.store.close)
        # 审查者给出的反例形状：先 global 后 session，文本完全相同
        self.global_row_id = self.store.add("用户养了一只猫", session_id=999, scope="global")
        self.session_row_id = self.store.add("用户养了一只猫", session_id=1)

    def test_duplicate_text_returns_both_row_identities(self):
        facts = self.store.recall_relevant(session_id=1, query="用户养的宠物", limit=2)
        self.assertEqual(len(facts), 2)
        # 只断言 fact 文本发现不了归并：两行文本本来就相同。
        # 必须断言行身份（fact_id / scope）。
        self.assertEqual(
            {f.fact_id for f in facts},
            {self.global_row_id, self.session_row_id},
        )
        self.assertEqual({f.scope for f in facts}, {"global", "session"})

    def test_duplicate_text_does_not_return_same_object_twice(self):
        facts = self.store.recall_relevant(session_id=1, query="用户养的宠物", limit=2)
        self.assertIsNot(facts[0], facts[1])
        self.assertNotEqual(facts[0].fact_id, facts[1].fact_id)

    def test_session_row_not_relabeled_as_global(self):
        # 本会话自己的行必须能以 session 身份被取回，不能被误标为
        # 999/global——下游若按 fact_id/scope 做删除或全局化提升会操错行
        facts = self.store.recall_relevant(session_id=1, query="用户养的宠物", limit=2)
        session_rows = [f for f in facts if f.fact_id == self.session_row_id]
        self.assertEqual(len(session_rows), 1)
        self.assertEqual(session_rows[0].scope, "session")
        self.assertEqual(session_rows[0].session_id, 1)

    def test_duplicate_text_limit_one_still_returns_a_real_row(self):
        facts = self.store.recall_relevant(session_id=1, query="用户养的宠物", limit=1)
        self.assertEqual(len(facts), 1)
        self.assertIn(facts[0].fact_id, {self.global_row_id, self.session_row_id})


if __name__ == "__main__":
    unittest.main()
