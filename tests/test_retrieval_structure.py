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

    def test_l2_still_dilutes_the_longer_fact(self):
        """RC-2：L2 的余弦口径把长事实里的查询内容稀释掉，本轮判定不可原则性修复。

        机制级证据，用合成句、不引用任何评测集：下面每组的两条事实包含完全相同的
        查询内容，长的那条只是多带了修饰语，余弦却只有短的那条的 ~0.56 倍——分母
        里的 ||f|| 随事实变长而增长，而分子只由共享 bigram 决定。v2 的 6 个未命中
        对全是这个形态（比值 0.23~0.71）。

        为什么不在实现里修：bigram_similarity 的 docstring 记了三种替代口径在三集
        上的实测。要点是把 L2 整层拿掉（W_BIGRAM=0）时 v2 24->19，只有 #21 翻成
        命中而另外 6 对翻成未命中——长度偏置只绑住 1 对，L2 的内容信号值 6 对，
        任何抹平偏置的改法都同时抹掉内容信号。不引入新参数的重叠系数与查询包含度
        确实能让 L2 弃权，但净命中为零，且命中对最小分差从 0.0067 塌到 0.0000。

        断言口径（做过变异演练，演练结果改写了本条断言）：钉死的是 cosine 下实测
        的稀释比值本身，不是「长事实得分更低」这个方向。方向断言抓不到长度阻尼——
        阻尼把比值从 0.559 进一步压到 0.351，方向一致却是另一种口径，初版断言在
        阻尼变异下仍然绿，属于零判别力。四种口径在本用例上的比值实测：cosine
        0.559/0.562、重叠系数 0.845/0.926、查询包含度 1.000/1.000、长度阻尼
        0.351/0.257。容差 0.01 与最近的替代口径至少相差 0.20，足够区分，同时对
        无害的浮点扰动宽容。换掉 L2 的归一化口径会让本条红，逼着改动者同步
        bigram_similarity docstring 里那一大段判定记录，而不是悄悄推翻它。
        """
        cases = (
            ("用户喜欢什么颜色", "用户喜欢蓝色",
             "用户喜欢蓝色，尤其是那种很深、偏灰的蓝", 0.559017),
            ("用户的家乡在哪里", "用户在湖南长沙",
             "用户说过他老家在湖南长沙，湘江边上那个城市", 0.561951),
        )
        for query, short, long, expected_ratio in cases:
            short_score = mr.bigram_similarity(query, short)
            long_score = mr.bigram_similarity(query, long)
            self.assertGreater(
                short_score, long_score,
                f"L2 不再偏短事实：{short!r} 与 {long!r} 的关系变了，请同步 docstring",
            )
            self.assertAlmostEqual(
                long_score / short_score, expected_ratio, delta=0.01,
                msg="L2 的稀释幅度变了：归一化口径被动过，RC-2 的判定记录需要重写",
            )

    def test_single_char_members_cross_match_into_other_classes(self):
        """N1（本轮新发现）：单字 member 会被无关复合词误命中。

        颜色类的 member 全是单字，而中文单字经常作为语素藏在无关复合词里：
        「花粉」含「粉」、「银行」含「银」、「黄土」含「黄」。危害的具体形态是
        最后一行断言：查询问颜色时，一条与颜色毫无关系的事实会拿到桥接分。

        但它在本轮三个评测集上**没有造成任何一对误判**——L3 需要双侧都命中同一
        个类才计分，而查询侧很少同时含颜色 head，所以它是一个潜伏的假阳性源，
        不是一个已发生的故障。本轮不修它，三条理由：
          1. 无原则性判据。同样的论证会杀掉宠物类的「猫」「狗」——它们也是单字
             且是必需证据（「用户养了一只猫」没有 head 词，全靠 member 命中）。
             「哪些单字有歧义」需要一份复合词表才能回答，那与本仓「纯标准库、
             禁分词库」的约束冲突，也会把反过拟合审计的分母搅乱。
          2. 无实测收益。三个集合计 52 对语料（查询×候选比较 130 次），修它翻转 0 对。
          3. 有实测风险。颜色类的真实命中路径（「藏青色」里的「青」）依赖单字
             member，收紧会直接伤到 D11 那一对。
        将来若引入词级切分，这条会变红提醒同步文档。
        """
        lexicon = mr.CONCEPT_LEXICON
        self.assertEqual(mr._concept_hit_parts(mr.normalize("花粉"), lexicon["颜色"]), (0, 1))
        self.assertEqual(mr._concept_hit_parts(mr.normalize("在银行上班"), lexicon["颜色"]), (0, 1))
        self.assertEqual(mr._concept_hit_parts(mr.normalize("黄土高原"), lexicon["颜色"]), (0, 1))
        self.assertGreater(
            mr.concept_bridge("用户喜欢什么颜色", "用户在银行上班"), 0.0,
            "N1 已被修掉——请同步更新本条 docstring 里的三条不修理由",
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


class LexiconMaskingInvariantTests(unittest.TestCase):
    """词典扩到 612 个成员之后必须重新钉住的不变量（第 3 块 3.2b 的连带更新）。

    这四条不是缺陷复现，而是**护栏**：它们断言的性质在写下来的当下就成立，
    存在的意义是让将来的词典变更无法静默破坏 L3 的计数口径。每条都在
    docstring 里写清它守的是哪一条口径、以及破坏它会让哪个已修的缺陷复活。
    """

    def test_longer_member_suppresses_the_shorter_ones_it_contains(self):
        """嵌套成员只算一条证据：M4 的口径在扩词后仍然成立。

        _masked_scan 保证「更长的成员压住它所包含的更短成员」。用例里的四个
        颜色词都能被两个单字成员平铺（银灰 = 银 + 灰），贪心必须只报长词——
        报两条就等于把一种颜色数成两条证据，正是审查发现 M4 的形态。
        「产品经理」压住「经理」是同一性质在四字成员上的样子。
        """
        lexicon = mr.CONCEPT_LEXICON
        cases = (
            ("颜色", "银灰", ("银", "灰")),
            ("颜色", "金黄", ("金", "黄")),
            ("颜色", "粉红", ("粉", "红")),
            ("颜色", "灰白", ("灰", "白")),
            ("职业", "产品经理", ("经理",)),
            ("职业", "项目经理", ("经理",)),
            ("过敏", "动物皮毛", ()),
            ("爱好", "密室逃脱", ()),
        )
        for name, text, contained in cases:
            words = (*lexicon[name].head, *lexicon[name].member)
            for short in contained:
                self.assertIn(short, words, f"用例已失效：{name} 里没有 {short}")
            self.assertIn(text, words, f"用例已失效：{name} 里没有 {text}")
            self.assertEqual(
                mr._masked_scan(mr.normalize(text), words), [text],
                f"{name} 的「{text}」被拆成了多条证据",
            )

    def test_matched_evidence_never_exceeds_the_text_it_came_from(self):
        """命中词两两不重叠 ⇒ 它们的总字符数不可能超过被扫描文本的长度。

        这是「同一份证据不被数两次」的可执行形式。扫描对象取词典自己的全部
        head 与 member（612 + 12 个词），并对每个词跑全部八个类：一个词在
        自己类里应当只报一条，在别的类里至多报若干条互不重叠的命中。
        """
        texts = [
            mr.normalize(word)
            for concept in mr.CONCEPT_LEXICON.values()
            for word in (*concept.head, *concept.member)
        ]
        self.assertGreater(len(texts), 600, "词典规模与本条的覆盖声明不符")
        for text in texts:
            for concept in mr.CONCEPT_LEXICON.values():
                matched = mr._masked_scan(text, (*concept.head, *concept.member))
                self.assertLessEqual(
                    sum(len(word) for word in matched), len(text),
                    f"{concept.name} 在「{text}」上重复计数：{matched}",
                )
                self.assertEqual(
                    len(set(matched)), len(matched),
                    f"{concept.name} 在「{text}」上把同一个词报了两次：{matched}",
                )

    def test_head_and_member_never_share_a_word(self):
        """head 与 member 的交集必须为空（memory_lexicon 的约束 3）。

        同一个词既命名槽位又填充槽位会让 RC-3a 的双侧 head-only 排除失去意义：
        _concept_hit_parts 判定一个命中词属于 head 还是 member，只看它在不在
        concept.head 里，交集词永远被判成 head，于是「一侧给出了值」再也无法
        与「两侧都只是在重复槽位名」区分开。
        """
        overlap = {
            name: sorted(set(concept.head) & set(concept.member))
            for name, concept in mr.CONCEPT_LEXICON.items()
            if set(concept.head) & set(concept.member)
        }
        self.assertEqual(overlap, {}, f"head 与 member 有交集：{overlap}")

    def test_no_member_is_listed_twice_within_a_class(self):
        """同类 member 不许重复。

        重复成员不会改变 _masked_scan 的结果（掩码保证同一段字符只被占一次），
        所以它是一种静默冗余：既让词典规模与反过拟合审计的分母虚高，也让
        「按规则生成词表」的审计对照表里同一个词出现两次。
        """
        dupes = {
            name: sorted({w for w in concept.member if concept.member.count(w) > 1})
            for name, concept in mr.CONCEPT_LEXICON.items()
            if len(set(concept.member)) != len(concept.member)
        }
        self.assertEqual(dupes, {}, f"这些类有重复成员：{dupes}")


# 规则原文（RC-4，可在不看任何评测集的前提下独立复述）：
#   极性谓词 = 极性前缀 + 单字活动动词 V。
#     事实侧否定前缀「不」，事实侧肯定前缀「爱」；
#     查询侧否定取向另有「不能 + V」与「V + 不了」两个构式。
#   V 的选取标准：汉语里能直接跟在「不/爱」后面构成偏好陈述的日常单字活动动词。
# 这条规则**在实现里已经有实例**：NEGATIVE_MARKERS 收了「不吃」、POSITIVE_MARKERS
# 收了「爱吃」、QUERY_NEGATIVE_MARKERS 收了「不能吃」与「吃不了」。所以本组测试要求
# 的是补全一条既有规则的产物集，而不是为某一对失败发明一条新规则——后者正是
# 任务书禁止的 Goodhart 形态。动词元组在本文件里独立写一遍是刻意的：测试是规则的
# 外部陈述，实现里那份是规则的产物，两份漂移时本组测试就会红。
_POLARITY_VERBS = (
    "吃", "喝", "玩", "看", "去", "用", "碰", "穿", "戴",
    "试", "尝", "买", "听", "抽", "唱", "画", "读", "跑",
)


class PolarityVerbRuleTests(unittest.TestCase):
    """RC-4：极性标记词表只收了「吃」一个动词，规则的其他产物全部缺席。

    diagnose 实测（v2 #7）：query「用户喜欢喝什么饮品」polarity=+1（RC-5 已修好），
    干扰项「用户不喝酒」与正确答案「用户每天早上要喝一杯手冲咖啡」在 L3/L5 上都为 0，
    L4 本应是唯一的判别层，但「不喝」不在 NEGATIVE_MARKERS 里，于是 `_polarity_hits`
    给出 (0,0)、L4 对这条**明确的否定陈述**完全静默，胜负落回 L2 的长度偏置
    （干扰 5 字 L2=0.1768 vs 答案 14 字 L2=0.0981），干扰项抢到 top-1。

    原则性依据不需要 v2：「不吃」与「不吃香菜」在汉语里是同一种构词，表里承认前者
    却漏掉后者，没有任何语言学依据。补全规则产物后实测（三集，本机）：golden 8/8、
    v1 12/12 均零翻转，v2 23/32 -> 24/32（只翻转 #7，且命中对最小分差 0.0067 不变）。
    反 Goodhart 审计：规则产出 34 个新词（不+V 17 个、爱+V 17 个），其中恰好落在 v2
    里的只有「不喝」1 个，占比 0.029；另外 33 个在三个集合计 52 对语料上**零翻转**——
    这一点是本组测试存在的意义：如果只加「不喝」，它与「看哪对失败就补哪个词」在
    代码上无法区分。
    """

    def test_every_negated_verb_is_a_negative_polarity_marker(self):
        """「不 + V」的每一个产物都必须被读成一条否定极性证据。"""
        for verb in _POLARITY_VERBS:
            text = mr.normalize(f"用户不{verb}这个")
            self.assertEqual(
                mr._polarity_hits(text), (0, 1),
                f"「不{verb}」没被 NEGATIVE_MARKERS 认出：规则产物集不完整",
            )

    def test_every_affirmative_verb_is_a_positive_polarity_marker(self):
        """「爱 + V」的每一个产物都必须被读成一条肯定极性证据。

        这一侧在三个评测集上实测零翻转（17 个新词全是惰性的）。仍然要补，理由是
        两张表必须对同一个动词集对称：只有否定侧补全的表会让「用户爱喝手冲咖啡」
        读作中性而「用户不喝酒」读作否定，L4 的带符号语义就偏向否定事实。
        """
        for verb in _POLARITY_VERBS:
            text = mr.normalize(f"用户爱{verb}这个")
            self.assertEqual(
                mr._polarity_hits(text), (1, 0),
                f"「爱{verb}」没被 POSITIVE_MARKERS 认出：两张表对动词集不对称",
            )

    def test_query_side_negative_orientation_covers_every_verb(self):
        """查询侧的「不能 + V」与「V + 不了」都必须把取向判成 -1。

        现状只认「不能吃」与「吃不了」，于是「用户不能喝什么」的 polarity 落到 0，
        L4 对整条查询静默——与 RC-5 修掉的缺口同形，只是发生在否定侧。这两个构式的
        34 个产物在 v2 里一个都没出现（占比 0.000）、在三个集上零翻转，补它买不到
        任何分数；补的理由纯粹是规则不完整，而这条自检用的探针句是合成的，不来自
        任何评测集。
        """
        for verb in _POLARITY_VERBS:
            for probe in (f"用户不能{verb}", f"用户{verb}不了"):
                self.assertEqual(
                    mr._query_context(probe).polarity, -1,
                    f"查询「{probe}」的取向没被判成负向：QUERY_NEGATIVE_MARKERS 不完整",
                )

    def test_an_explicit_negation_is_penalised_on_a_positive_preference_query(self):
        """正向偏好提问下，明确的否定陈述必须拿负分，而不是与中性事实同分。

        这是 RC-4 的行为级形态，与上面三条的标记级形态互为验证：标记级测「词被认出
        了」，本条测「认出来之后 L4 真的按符号用了它」。红的时候它返回 0.0，正是
        「L4 对否定事实静默」这一缺陷本身。
        """
        query = "用户喜欢喝什么饮品"
        self.assertEqual(mr._query_context(query).polarity, 1, "前置条件：RC-5 应已让本查询取正向")
        self.assertLess(
            mr.preference_bonus(query, "用户不喝酒"), 0.0,
            "L4 对「不喝酒」静默：否定事实与中性事实同分，正向提问下它靠 L2 长度优势抢位",
        )
        self.assertEqual(mr.preference_bonus(query, "用户每天早上要喝一杯手冲咖啡"), 0.0)


class NegationScopeTests(unittest.TestCase):
    """RC-7：否定前缀「不」支配任何肯定极性谓词，不只是手工列过的那一个。

    这是本轮在扩 RC-4 动词集时撞出来的**既有**缺陷，与 v2 无关：HEAD 上
    `_polarity_hits("用户不爱吃香菜")` 就返回 (1, 0)，`_polarity_hits("用户不热爱
    运动")` 与 `_polarity_hits("用户对钓鱼不感兴趣")` 同样返回 (1, 0)。后果是
    `preference_bonus("用户有什么忌口", "用户不爱吃香菜") == -0.5`：查询问的正是
    忌口、事实答的正是忌口，L4 却把它当反向证据扣分。

    旧实现只对「不喜欢」手工列了一个否定形式，那就是为什么它能蒙对这一条而
    蒙不对其他。扩完 RC-4 的动词集之后，这个漏圈的肯定谓词从 8 个变成 25 个，所以
    必须同时处置。修法选结构性规则而不是再补词：判「不 + 该谓词」是否连续出现，
    对将来新增的任何肯定谓词自动生效。
    """

    def test_negation_prefix_dominates_every_affirmative_predicate(self):
        """逐个肯定谓词验：前置「不」之后必须整条计作否定证据。"""
        for word in mr.POSITIVE_MARKERS:
            text = mr.normalize(f"用户不{word}这个")
            self.assertEqual(
                mr._polarity_hits(text), (0, 1),
                f"「不{word}」被读成了肯定极性：否定辖域没盖住这个谓词",
            )

    def test_a_bare_negation_elsewhere_does_not_flip_the_polarity(self):
        """辖域只看连续串：句尾一个不相干的「不」不得把肯定谓词翻成否定。

        没有这一条，上一条会被一个「只要句里有不就算否定」的惰实现蒙对。
        """
        self.assertEqual(
            mr._polarity_hits(mr.normalize("用户喜欢香菜，不过库存不多")), (1, 0),
            "不相干的「不」把肯定谓词翻成了否定：辖域判得比连续串宽",
        )
        self.assertEqual(
            mr._polarity_hits(mr.normalize("用户喜欢香菜，而且不挑牌子")), (1, 0),
        )

    def test_query_orientation_follows_the_negation_scope(self):
        """查询侧同一条规则：「不爱吃什么」问的是负向约束，不能因为含子串「爱吃」
        就判成正向——那会让 L4 去奖励与提问方向相反的事实。"""
        self.assertEqual(mr._query_context("用户喜欢喝什么").polarity, 1)
        self.assertEqual(mr._query_context("用户不喜欢什么").polarity, -1)
        self.assertEqual(mr._query_context("用户不爱吃什么").polarity, -1)
        self.assertEqual(mr._query_context("用户对什么不感兴趣").polarity, -1)

    def test_a_restriction_query_rewards_the_restriction_itself(self):
        """行为级：问忌口时，一条忌口陈述必须拿正分。

        红的时候它是 -0.5：符号完全反了。本条不引用 v2 的任何一对，用的是
        与 test_memory_retrieval 里已有那组忌口断言同形的合成句。
        """
        self.assertGreater(
            mr.preference_bonus("用户有什么忌口", "用户不爱吃香菜"), 0.0,
            "L4 把对题的忌口陈述当成反向证据扣分：否定辖域丢了",
        )
        self.assertLess(
            mr.preference_bonus("用户有什么忌口", "用户喜欢吃香菜"), 0.0,
            "对称校验：肯定事实在负向提问下必须拿负分",
        )


if __name__ == "__main__":
    unittest.main()
