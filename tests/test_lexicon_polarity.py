"""Task B retrieval tests: concept-lexicon semantics and polarity handling.

Split out of tests/test_memory_retrieval.py by N4 (that file had grown to 798
lines against the 800-line ceiling). This is a pure move: no assertion, no test
name and no test count changed.

Coverage: lexicon membership and masked-scan semantics
(LexiconSemanticsTests), and the polarity / negation-scope behaviour of
preference_bonus (PolarityTests).
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from src import memory_ranker as mr  # noqa: E402


class LexiconSemanticsTests(unittest.TestCase):
    """审查发现 M1/M4：单字 head 误判与嵌套子串重复计数。

    M1：head 词里的单字（「色」「市」）做子串命中，把「超市/角色/脸色」
    误判为稳定属性提问，于是 L5 对正对题的近期事实扣分——与
    transient_penalty 自己 docstring「问『最近干嘛』时这些事实恰恰对题」
    的设计口径直接相反。golden 的 8 个查询全部含双字 head，去掉单字不影响。

    M4：「颜色」同时命中 head「颜色」与 head「色」、「生日」同时命中
    「生日」与「日」，完全相同的证据强度只因该类 head 存在嵌套关系就被抬高
    33%，跨类不可比。修法是最长优先贪心掩码：长词命中后其覆盖的字符位置
    标为已用，落在已用位置内的短词不再计数。
    """

    def test_recent_state_query_does_not_demote_on_topic_fact(self):
        # M1 端到端：查询问近期状态时，带时态标记的对题事实不得被降权到
        # 稳定属性事实之下（修复前实测 0.2716 < 0.4025，排序完全反了）
        query = "用户最近去超市买了什么"
        self.assertGreater(
            mr.score(query, "用户最近在超市买了咖啡豆"),
            mr.score(query, "用户喜欢逛超市"),
        )

    def test_anime_flavored_recent_query_not_misgated(self):
        # 动漫语境同源：「角色」里的单字「色」曾让本查询被当成颜色类提问
        query = "用户最近在追哪个角色"
        self.assertEqual(mr.transient_penalty(query, "用户最近在追芙莉莲"), 0.0)
        self.assertEqual(mr.preference_bonus(query, "用户喜欢芙莉莲这个角色"), 0.0)

    def test_nested_head_not_double_counted(self):
        self.assertEqual(mr._concept_hits(mr.normalize("颜色"), mr.CONCEPT_LEXICON["颜色"]), 1)
        self.assertEqual(mr._concept_hits(mr.normalize("生日"), mr.CONCEPT_LEXICON["生日"]), 1)

    def test_single_char_head_no_longer_cross_matches(self):
        self.assertEqual(mr._concept_hits(mr.normalize("超市"), mr.CONCEPT_LEXICON["城市"]), 0)
        self.assertEqual(mr._concept_hits(mr.normalize("角色"), mr.CONCEPT_LEXICON["颜色"]), 0)

    def test_self_bridge_strength_comparable_across_classes(self):
        # M4 的直接可测口径：同样的「查询 == 事实」自匹配，每个类的桥接
        # 强度必须相等（修复前颜色/城市/生日三类被抬高到 0.667，其余 0.500）。
        # 两处更新，都是 RC-3a/RC-3b 的直接后果：
        #   1. 自匹配文本必须同时含 head 与 member。只含 head 的「用户的{head}」
        #      现在双侧都 head-only，恒为 0.0，len(values)==1 会变成空转断言。
        #   2. member 必须取「不落到别的类里」的那一个。RC-3b 的 noisy-OR 让
        #      跨类证据真的累加了，于是 member[0] 的偶然歧义会显形：过敏类的
        #      「花粉」含颜色类单字 member「粉」，自匹配文本因此命中两个类、
        #      拿到 0.8333 而不是 0.6667。这个歧义本身是已记录的局限（N1，见
        #      test_retrieval_structure.py），本测口径要隔离它，否则「跨类可比」
        #      这条 M4 性质会被一个无关的字面巧合掩盖。
        values = {}
        for concept in mr.CONCEPT_LEXICON.values():
            member = next(
                (
                    word
                    for word in concept.member
                    if all(
                        other is concept
                        or mr._concept_hits(mr.normalize(word), other) == 0
                        for other in mr.CONCEPT_LEXICON.values()
                    )
                ),
                None,
            )
            self.assertIsNotNone(member, f"{concept.name} 的 member 全部与其他类歧义")
            text = f"用户的{concept.head[0]}是{member}"
            value = round(mr.concept_bridge(text, text), 12)
            self.assertGreater(value, 0.0, f"{concept.name} 的自匹配被 RC-3a 误伤")
            values[concept.name] = value
        self.assertEqual(len(set(values.values())), 1, f"跨类自匹配强度不可比：{values}")

    def test_masked_hits_counts_largest_non_overlapping_subset(self):
        self.assertEqual(mr._masked_hits(mr.normalize("用户住在杭州市"), ("城市", "市", "杭州")), 2)
        self.assertEqual(mr._masked_hits(mr.normalize("颜色"), ("颜色", "色")), 1)
        self.assertEqual(mr._masked_hits("", ("颜色",)), 0)


class PolarityTests(unittest.TestCase):
    """审查发现 M2：PREFERENCE_MARKERS 混入否定谓词且不辨极性。

    实测：查询「用户的爱好」下 score("用户讨厌运动")=0.3921 >
    score("用户周末徒步")=0.3421——问「爱好」却把否定该活动的事实排在真实
    爱好之前，注入 extra_system 即语义反转，LLM 会据此以为用户喜欢运动。

    修法是把肯定/否定谓词分开建模并对查询定极性：匹配加分、相反扣分。
    不能只把否定词删掉了事——那样「用户有什么忌口」这类查询就没人接了。
    """

    def test_negative_predicate_does_not_outrank_real_hobby(self):
        self.assertLess(
            mr.score("用户的爱好", "用户讨厌运动"),
            mr.score("用户的爱好", "用户周末徒步"),
        )

    def test_negative_query_prefers_negative_fact(self):
        self.assertGreater(
            mr.score("用户有什么忌口", "用户不吃香菜"),
            mr.score("用户有什么忌口", "用户喜欢吃香菜"),
        )

    def test_query_polarity_is_three_valued(self):
        self.assertEqual(mr._query_polarity("用户的爱好"), 1)
        self.assertEqual(mr._query_polarity("用户有什么忌口"), -1)
        self.assertEqual(mr._query_polarity("用户周末一般干嘛"), 0)

    def test_opposed_polarity_is_penalized_not_just_unrewarded(self):
        self.assertLess(mr.preference_bonus("用户的爱好", "用户讨厌运动"), 0.0)
        self.assertGreater(mr.preference_bonus("用户有什么忌口", "用户不吃香菜"), 0.0)
        self.assertLess(mr.preference_bonus("用户有什么忌口", "用户喜欢吃香菜"), 0.0)

    def test_polarity_scan_is_joint_so_negation_is_not_cancelled(self):
        # 「不喜欢」含子串「喜欢」；两组分开扫描会让肯定词抵消否定词并翻转极性
        self.assertEqual(mr._polarity_hits(mr.normalize("用户不喜欢吃香菜")), (0, 1))
        self.assertEqual(mr._polarity_hits(mr.normalize("用户最喜欢也最热爱徒步")), (2, 0))
        self.assertEqual(mr._polarity_hits(mr.normalize("用户是后端工程师")), (0, 0))

    def test_polarity_bonus_range_is_signed_and_saturated(self):
        for query in ("用户的爱好", "用户有什么忌口", "用户周末一般干嘛"):
            for fact in ("用户最喜欢也最热爱徒步", "用户讨厌也不吃香菜", "用户在杭州工作"):
                with self.subTest(query=query, fact=fact):
                    self.assertGreaterEqual(mr.preference_bonus(query, fact), -1.0)
                    self.assertLessEqual(mr.preference_bonus(query, fact), 1.0)


if __name__ == "__main__":
    unittest.main()
