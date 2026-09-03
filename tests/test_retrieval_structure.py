"""Structural repairs to L3/L4 driven by the v2 layered attribution, not by v2 pairs.

本文件里的每一条断言都来自 `report_retrieval.py diagnose` 打出的四层加权贡献，而
不是来自「v2 第几对失败就把那条的数据抄进测试」。三条修复的原则性依据分别是：

RC-3a 双侧只命中 head 不构成桥（L3）
    diagnose 实测：v2 #15 query「用户在哪个城市工作」下，干扰项「用户喜欢在城市的
    公园里散步」与正确答案「用户在武汉的一家设计院上班」的 L3 加权贡献**完全相同**
    （都是 +0.2750）。原因是 `_concept_hits` 把 head 与 member 同等计数：干扰项靠
    重复问题里的「城市」拿到 fh=1，答案靠给出实例「武汉」也拿到 fh=1。
    原则性依据不需要 v2：head 词**命名槽位**，member 词**填充槽位**。一侧只说「城市」
    是在问/提及这个槽位，它没有给出任何值，因此不构成「桥」的一岸。这与
    concept_bridge 已有的「单边命中不计分」是同一条原则的延伸——原实现已经承认
    「桥需要两岸」，却没承认「岸必须是值而不是槽位名」。
    规则写成**对称**形式（双侧都只命中 head 才排除），而不是「查询侧 head-only 则
    要求事实侧有 member」：后者会让 concept_bridge 失去它已文档化并有测试钉住的
    对称性（test_memory_retrieval.py 的 test_concept_bridge_is_symmetric），而对称性
    是 recall_relevant 与 score_retrieval 可重复性的前提。

RC-3b 多个类的独立证据必须能累加（L3）
    diagnose 实测：v2 #24 干扰项「用户是老师」命中 1 个类（称呼），答案「…橘猫…
    叫团子」命中 2 个类（称呼 + 宠物），两者 L3 加权贡献仍然**完全相同**（+0.2750）。
    原因是 `_concept_profile` 对参与类取**算术均值**：mean([0.5]) == mean([0.5,0.5])。
    这与 concept_bridge docstring 自己声称的「几何均值让单个弱命中不超过 head 级
    命中」直接矛盾——均值让「一个类的弱命中」与「两个类的强命中」完全等价，跨类
    的独立证据被归一化抹平了。
    改用 noisy-OR：`1 - Π(1 - c_i)`。它是把 [0,1) 内独立证据合成一个 [0,1) 置信度
    的标准做法，满足三条必需性质：① 单类时退化为原值（改动是保守的，只影响多类
    情形）；② 对证据个数单调递增；③ 值域仍在 [0,1)，不破坏「concept_bridge 返回
    [0.0,1.0]」这条已文档化契约，也不需要重新调 W_CONCEPT。

RC-5 查询侧的偏好谓词本身就决定了取向（L4）
    diagnose 实测：v2 #7 与 #23 的 query（「用户喜欢喝什么饮品」「用户喜欢吃什么」）
    都含「喜欢」，但 `_query_polarity` 返回 0，因为 `_stable_from_normalized` 只认
    head 词而「喜欢」是爱好类的 **member**。polarity=0 → `_preference_profile` 直接
    返回 0 → 「用户不喝酒」「用户不喜欢香菜」这类否定事实**完全不受惩罚**，靠 L2
    的长度优势（#23 干扰 7 字 vs 答案 27 字）抢到 top-1。
    原则性依据也不需要 v2：问句的极性决定答案该有的极性。「喜欢 X 吗」问的是正向
    偏好，「讨厌 X 吗」问的是负向约束，这与事实侧用 POSITIVE_MARKERS /
    NEGATIVE_MARKERS 判极性是同一条语言学事实。原实现已经在事实侧承认它，也在
    查询侧承认了**负向**（QUERY_NEGATIVE_MARKERS），唯独漏了查询侧的正向——这是
    一个不对称的缺口，补上它是把已有的对称性补全，不是新增语义。

刻意**不**做的事（范围限制，有测试钉住）
    - 不放宽 L5 的 stable 门控。L5（时态降权）的门控仍只认 head 词。理由：问「最近
      喜欢吃什么」时，「用户最近喜欢吃辣」恰恰对题，放宽会让 L5 误伤；而 RC-5 要
      解决的是 L4 的极性静默，两者门控语义不同，不该共用一个开关。
    - 不修 L4 的「对象盲」。L4 只看事实里有没有极性词，不看它支配的对象是否是被问
      的槽位（#15 的「喜欢在城市的公园里散步」因此拿到 +0.0500）。修它需要让 L4
      以 L3 的类重叠为条件，而那会连带静默 #7/#23（query 问的槽位与否定事实所属类
      不重叠），与 RC-5 直接冲突。RC-3a 落地后 L4 的对象盲在三个集上不再决定任何
      一对的胜负，所以本轮把它作为已知局限如实记录，而不是硬修。
"""
from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path
from types import MappingProxyType
from unittest import mock

TESTS = Path(__file__).resolve().parent
REPO = TESTS.parent
for _path in (str(REPO), str(TESTS)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from src import memory_ranker as mr  # noqa: E402

# 探针词典：只含一个类，head 与 member 都是不会出现在任何评测集里的合成词。
# 用它测「机制」而不是测「某个真实词在不在词典里」，这样词典按通用规则扩充后
# 这些测试仍然成立——它们的红/绿只由打分语义决定，与词表内容无关。
_PROBE = MappingProxyType({
    "探针": mr.ConceptClass(name="探针", head=("探针头",), member=("探针值",)),
})
_OTHER = MappingProxyType({
    "甲类": mr.ConceptClass(name="甲类", head=("甲头",), member=("甲值",)),
    "乙类": mr.ConceptClass(name="乙类", head=("乙头",), member=("乙值",)),
})


class HeadOnlyBridgeExclusionTests(unittest.TestCase):
    """RC-3a: naming a slot is not the same as filling it."""

    def test_both_sides_head_only_does_not_bridge(self):
        """红因（当前实现）：双侧都只命中 head 时仍返回 0.5，与给出实例同分。"""
        probe = MappingProxyType({
            "槽位": mr.ConceptClass(name="槽位", head=("槽位名",), member=("槽位值",)),
        })
        with mock.patch.object(mr, "CONCEPT_LEXICON", probe):
            both_head = mr.concept_bridge("用户的槽位名", "用户提到槽位名")
            with_member = mr.concept_bridge("用户的槽位名", "用户的槽位值是甲")
        self.assertEqual(
            both_head, 0.0,
            f"双侧都只重复槽位名却拿到桥接分 {both_head}：head 命名槽位、member 填充"
            f"槽位，只命名不填充的一侧不构成桥的一岸",
        )
        self.assertGreater(
            with_member, both_head,
            f"给出实例的一侧（{with_member}）没有压过只重复槽位名的一侧（{both_head}）"
            f"——两者同分意味着 L3 完全无法区分「提及槽位」与「填充槽位」",
        )

    def test_exclusion_is_symmetric(self):
        """纯护栏：排除规则必须对称，否则 concept_bridge 的对称性契约被破坏。

        这条在修复前后都必须绿（它只比相等关系，不比大小），所以把它放在红集
        之外：若将来有人把排除写成单侧的（例如「查询侧 head-only 就判 0」），
        forward != backward，这条立刻红。
        """
        probe = MappingProxyType({
            "槽位": mr.ConceptClass(name="槽位", head=("槽位名",), member=("槽位值",)),
        })
        with mock.patch.object(mr, "CONCEPT_LEXICON", probe):
            forward = mr.concept_bridge("用户的槽位名", "用户提到槽位名")
            backward = mr.concept_bridge("用户提到槽位名", "用户的槽位名")
            mixed = mr.concept_bridge("用户的槽位名", "用户的槽位值是甲")
            mixed_rev = mr.concept_bridge("用户的槽位值是甲", "用户的槽位名")
        self.assertEqual(forward, backward)
        self.assertEqual(mixed, mixed_rev, "一侧 head-only、另一侧含 member 时必须对称")

    def test_head_plus_member_on_one_side_still_bridges(self):
        """护栏：排除只针对「双侧都 head-only」，一侧含 member 就必须照常桥接。

        这条防的是把规则写过头——若误写成「任一侧 head-only 就排除」，那么
        「用户的生日」对「用户的生日是7月12日」这种最常见的真实形态会被判 0，
        既有测试 test_concept_bridge_is_symmetric 也会一起红。
        """
        self.assertGreater(mr.concept_bridge("用户的生日", "用户的生日是7月12日"), 0.0)
        self.assertGreater(mr.concept_bridge("用户在哪座城市", "用户在天津住过"), 0.0)

    def test_member_only_still_bridges_both_ways(self):
        """护栏：双侧都只命中 member（没有 head）也必须桥接——那是在比较两个值。"""
        probe = MappingProxyType({
            "槽位": mr.ConceptClass(name="槽位", head=("槽位名",), member=("槽位值",)),
        })
        with mock.patch.object(mr, "CONCEPT_LEXICON", probe):
            self.assertGreater(mr.concept_bridge("我的槽位值", "他的槽位值"), 0.0)


class MultiClassEvidenceTests(unittest.TestCase):
    """RC-3b: independent evidence from two classes must outweigh one."""

    def test_two_classes_outrank_one(self):
        """红因（当前实现）：算术均值让 mean([0.5]) == mean([0.5, 0.5])。"""
        with mock.patch.object(mr, "CONCEPT_LEXICON", _OTHER):
            one = mr.concept_bridge("甲头和乙头", "这里是甲值")
            two = mr.concept_bridge("甲头和乙头", "这里是甲值和乙值")
        self.assertGreater(
            two, one,
            f"两个类的独立实例证据（{two}）没有压过一个类（{one}）：均值归一化把"
            f"跨类证据抹平了，与 docstring 声称的「单个弱命中不超过 head 级命中」矛盾",
        )

    def test_single_class_value_is_unchanged_by_the_combination_rule(self):
        """护栏：noisy-OR 在单类时退化为原值，所以这次改动是保守的。

        这条把「改动只影响多类情形」钉成事实：若将来有人换成求和或加权平均，
        单类值会变，这条测试立刻红。
        """
        with mock.patch.object(mr, "CONCEPT_LEXICON", _OTHER):
            single = mr.concept_bridge("甲头", "这里是甲值")
        qh = fh = 1
        strength = math.sqrt(qh * fh)
        self.assertAlmostEqual(single, strength / (strength + 1.0), places=12)

    def test_combination_stays_within_unit_interval(self):
        """护栏：值域必须仍在 [0,1)，否则 W_CONCEPT 的量纲就变了、需要重新调参。"""
        many = MappingProxyType({
            f"类{i}": mr.ConceptClass(name=f"类{i}", head=(f"头{i}",), member=(f"值{i}",))
            for i in range(8)
        })
        query = "".join(f"头{i}" for i in range(8))
        fact = "".join(f"值{i}" for i in range(8))
        with mock.patch.object(mr, "CONCEPT_LEXICON", many):
            combined = mr.concept_bridge(query, fact)
        self.assertLess(combined, 1.0, f"八个类全命中也不许达到 1.0，实测 {combined}")
        self.assertGreater(combined, 0.99, f"八个独立 0.5 证据合成后应接近 1，实测 {combined}")

    def test_more_evidence_is_monotone(self):
        """单调性：证据类数递增时桥接分严格递增（noisy-OR 的性质）。"""
        many = MappingProxyType({
            f"类{i}": mr.ConceptClass(name=f"类{i}", head=(f"头{i}",), member=(f"值{i}",))
            for i in range(4)
        })
        with mock.patch.object(mr, "CONCEPT_LEXICON", many):
            values = [
                mr.concept_bridge("头0头1头2头3", "".join(f"值{i}" for i in range(count + 1)))
                for count in range(4)
            ]
        self.assertEqual(values, sorted(values), f"非单调：{values}")
        self.assertEqual(len(set(values)), 4, f"存在相等的相邻档：{values}")


class QuerySidePolarityTests(unittest.TestCase):
    """RC-5: the polarity of the question decides the polarity of the answer."""

    def test_positive_predicate_without_head_word_gives_positive_polarity(self):
        """红因（当前实现）：query 含「喜欢」但无 head 词 → polarity=0 → L4 静默。

        用探针词典而不是真词典：这样「喜欢」只是 POSITIVE_MARKERS 的一员，不是任何
        类的 member/head，测试只考核「查询侧正向谓词被识别」这个机制本身，词典按
        通用规则扩充后仍然成立。
        """
        with mock.patch.object(mr, "CONCEPT_LEXICON", _PROBE):
            for query in ("用户喜欢探针味的东西", "用户热爱探针味的东西", "用户偏好探针味"):
                self.assertEqual(
                    mr._query_polarity(query), 1,
                    f"{query!r} 明明在问正向偏好，极性却是 0，L4 会对它完全静默",
                )

    def test_negative_query_polarity_still_takes_precedence(self):
        """护栏：负向判定优先于正向——「不喜欢」里含「喜欢」，必须判 -1。

        这条在修复前就是绿的（QUERY_NEGATIVE_MARKERS 先判），写下来是防止补正向
        检测时把优先级顺序写反。
        """
        with mock.patch.object(mr, "CONCEPT_LEXICON", _PROBE):
            self.assertEqual(mr._query_polarity("用户不喜欢探针味"), -1)
            self.assertEqual(mr._query_polarity("用户讨厌探针味的东西"), -1)

    def test_neutral_query_stays_silent(self):
        """护栏：无极性词、无 head 词的闲聊查询必须保持 polarity=0。

        这是 _query_polarity docstring 明确承诺的行为（「行为式提问不含 head 词，
        L4 对它们保持静默，否则闲聊查询也会被带偏好词的事实抢位」）。补正向检测
        不许把它破坏。
        """
        with mock.patch.object(mr, "CONCEPT_LEXICON", _PROBE):
            self.assertEqual(mr._query_polarity("今天天气怎么样"), 0)
            self.assertEqual(mr._query_polarity("用户周末一般干嘛"), 0)
            self.assertEqual(mr.preference_bonus("今天天气怎么样", "用户不喜欢探针味"), 0.0)

    def test_negative_fact_is_penalised_under_a_positive_query(self):
        """红因（当前实现）：polarity=0 → 否定事实既不加分也不减分。"""
        with mock.patch.object(mr, "CONCEPT_LEXICON", _PROBE):
            bonus = mr.preference_bonus("用户喜欢探针味的东西", "用户不喜欢探针味")
        self.assertLess(
            bonus, 0.0,
            f"正向提问下否定事实应被减分，实测 {bonus}：L4 静默意味着注入 extra_system"
            f"的可能是语义反转的记忆",
        )

    def test_positive_fact_is_rewarded_under_a_positive_query(self):
        """对称的一半：正向提问下正向事实应加分。"""
        with mock.patch.object(mr, "CONCEPT_LEXICON", _PROBE):
            self.assertGreater(mr.preference_bonus("用户喜欢探针味的东西", "用户喜欢探针味"), 0.0)

    def test_tense_gate_is_not_widened_by_the_polarity_fix(self):
        """范围限制：L5 的 stable 门控仍只认 head 词，不许跟着 L4 一起放宽。

        理由见模块 docstring：问「最近喜欢吃什么」时「用户最近喜欢吃辣」恰恰对题，
        放宽 L5 会误伤它。RC-5 修的是 L4 的极性静默，两层门控语义不同。
        """
        with mock.patch.object(mr, "CONCEPT_LEXICON", _PROBE):
            self.assertFalse(mr._is_stable_attribute_query("用户喜欢探针味的东西"))
            self.assertEqual(mr.transient_penalty("用户喜欢探针味的东西", "用户最近喜欢探针味"), 0.0)
            # head 词在场时 L5 照常生效（护栏：不许把 L5 一起关掉）
            self.assertTrue(mr._is_stable_attribute_query("用户的探针头"))
            self.assertGreater(mr.transient_penalty("用户的探针头", "用户最近改了探针值"), 0.0)


class BehaviouralRegressionTests(unittest.TestCase):
    """End-to-end: the two mechanisms must change an actual ranking decision.

    样例全部现场构造，不复用任何评测集里的对——用评测集数据写单测等于把留出集
    搬进训练集，那正是本轮要防的 Goodhart。
    """

    def test_negative_distractor_no_longer_outranks_the_positive_answer(self):
        """红因（当前实现）：「用户不吃辣」靠 5 字的长度优势压过 9 字的正答。"""
        stored = ["用户不吃辣", "用户平时爱喝乌龙茶"]
        top = mr.rank("用户喜欢喝什么", stored)[0][0]
        self.assertEqual(
            top, stored[1],
            f"正向提问下 top-1 是 {top!r}：否定事实未被减分，靠短文本的 bigram 余弦"
            f"优势抢位，注入 prompt 即语义反转",
        )

    def test_slot_filling_fact_outranks_slot_repeating_fact(self):
        """红因（当前实现）：重复槽位名的干扰项与给出实例的答案 L3 同分。"""
        stored = ["用户喜欢谈论城市的话题", "用户去年搬去了天津"]
        top = mr.rank("用户住在哪个城市", stored)[0][0]
        self.assertEqual(top, stored[1], f"top-1 是 {top!r}，它只是重复了问题里的槽位名")

    def test_two_class_evidence_wins_a_real_ranking(self):
        """红因（当前实现）：命中两个类的事实压不过只命中一个类的事实。"""
        stored = ["用户养了一只狗", "用户在天津养了一只狗"]
        top = mr.rank("用户住在哪个城市养了什么宠物", stored)[0][0]
        self.assertEqual(top, stored[1], f"top-1 是 {top!r}，它只提供了一个类的证据")


class DocumentedLimitationTests(unittest.TestCase):
    """钉住已知局限：断言盲区**存在**，将来若修好则测试变红提醒同步文档。"""

    def test_l4_remains_object_blind(self):
        """L4 不看极性词支配的对象是否是被问的槽位。

        「用户喜欢在公园里散步」的「喜欢」支配的是散步，与查询问的槽位无关，却照样
        拿到正向偏好分。修它需要让 L4 以 L3 的类重叠为条件，而那会连带静默掉
        RC-5 要救的那些对（query 问的槽位与否定事实所属类不重叠），两者冲突。
        RC-3a 落地后这个盲区在 golden ∪ v1 ∪ v2 上不再决定任何一对的胜负，所以
        本轮如实记录而不硬修。
        """
        probe = MappingProxyType({
            "槽位": mr.ConceptClass(name="槽位", head=("槽位名",), member=("槽位值",)),
        })
        with mock.patch.object(mr, "CONCEPT_LEXICON", probe):
            unrelated = mr.preference_bonus("用户的槽位名", "用户喜欢在别处散步")
        self.assertGreater(
            unrelated, 0.0,
            "L4 的对象盲已被修掉——请同步更新模块 docstring 的「刻意不做的事」段落",
        )

    def test_head_only_exclusion_does_not_fix_a_missing_member(self):
        """RC-3a 只解决「同分」，不解决「事实侧一个类都没命中」。

        若答案里的实例词根本不在词典（羽毛球、大厨、哮喘这类），L3 仍然为 0，
        RC-3a/RC-3b 都救不了它——那是词表覆盖问题，由按通用枚举规则扩词处理，
        而不是由这两条结构修复处理。这条测试把边界钉住，防止把两类问题混为一谈。
        """
        probe = MappingProxyType({
            "槽位": mr.ConceptClass(name="槽位", head=("槽位名",), member=("槽位值",)),
        })
        with mock.patch.object(mr, "CONCEPT_LEXICON", probe):
            self.assertEqual(mr.concept_bridge("用户的槽位名", "用户在做完全无关的事"), 0.0)


if __name__ == "__main__":
    unittest.main()
