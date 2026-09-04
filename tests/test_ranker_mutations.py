"""Task B mutation drill: do the evaluation sets actually bite?

审查发现 M11：原有测试只断言「实现达标」，从不检验「达标这件事是否真的
依赖被声明的机制」。变异演练的做法是在进程内把某一层的实现或权重换成缺陷
版本，然后看评测指标是否掉下来——掉不下来就说明该测试对这类缺陷无判别力。

本文件里每一条断言都是**先实测再写**的，实测结论分两类，两类都如实保留：

  有牙齿（4 路）：W_CONCEPT=0 → 留出集 8/12；rank() 不排序 → golden 5/8；
    清空全部 member → 留出集 8/12；清空整个词典 → golden 6/8。
  无牙齿（4 路）：W_TRANSIENT=0、W_PREFERENCE=0、_concept_hit_parts 退回朴素
    子串计数、_polarity_hits 退回两组独立计数——这 4 路在两个评测集上都
    保持满分。对它们只断言层内行为确实消失，**不许**断言指标跌破 0.8，
    因为那是实测为假的期望。

「无牙齿」本身是本轮最重要的产出之一：它量化了两个评测集的盲区（其中
rank() 不排序那一路还暴露出留出集 v1 的相关事实恒在 stored[0]，对顺序
零判别力，即审查发现 M8），直接决定下一轮留出集 v2 要怎么补。
"""
from __future__ import annotations

import dataclasses
import sys
import unittest
from pathlib import Path
from unittest import mock

TESTS = Path(__file__).resolve().parent
REPO = TESTS.parent
for _path in (str(REPO), str(TESTS)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from src import memory_ranker as mr  # noqa: E402

# 两份评测集都从 test_memory_retrieval 取，避免第三份副本静默失同步
from test_memory_retrieval import GOLDEN, HOLDOUT_GOLDEN  # noqa: E402

# v2 盲测集与它的官方计分器：N1 变异体要断言 v2 #24/#29 的逐对命中
from holdout_v2 import HOLDOUT_V2  # noqa: E402
from test_holdout_v2 import score_holdout_v2  # noqa: E402

THRESHOLD = 0.8
_WEIGHT_NAMES = ("W_BIGRAM", "W_CONCEPT", "W_PREFERENCE", "W_TRANSIENT")


def _top1_hits(golden: list[dict]) -> int:
    """Count pairs whose top-1 retrieval lands inside `relevant`."""
    return sum(
        1
        for item in golden
        if mr.rank(str(item["query"]), list(item["stored"]))[0][0] in set(item["relevant"])
    )


def _accuracy(golden: list[dict]) -> float:
    return _top1_hits(golden) / len(golden)


def _min_margin(golden: list[dict]) -> float:
    """Smallest (top1 - top2) gap over the set: how much room a flip needs."""
    gaps = []
    for item in golden:
        ranked = mr.rank(str(item["query"]), list(item["stored"]))
        gaps.append(ranked[0][1] - (ranked[1][1] if len(ranked) > 1 else 0.0))
    return min(gaps)


def _v2_rows() -> list[dict]:
    """v2 逐对明细，走 test_holdout_v2 的官方计分器（口径与验收一致）。"""
    return score_holdout_v2(HOLDOUT_V2)["rows"]


def _v2_hit_count() -> int:
    return sum(1 for row in _v2_rows() if row["hit"])


def _single_char_members() -> dict:
    """每个类的单字 member，按类名归组（N1 的语料面）。

    实测合计 28 个：颜色 15 / 生日 4 / 宠物 4 / 过敏 3 / 称呼 2。
    """
    return {
        name: [m for m in concept.member if len(m) == 1]
        for name, concept in mr.CONCEPT_LEXICON.items()
        if any(len(m) == 1 for m in concept.member)
    }


def _without_members(drop: set) -> dict:
    """整体 rebind：返回一个删掉 drop 里 (类名, member) 对的新词典。

    CONCEPT_LEXICON 是 MappingProxyType 只读视图，不能原地 __setitem__；沿用
    本文件既有的 dataclasses.replace 整体替换手法，配合 mock.patch.object rebind
    与 MutationDrill.addCleanup 的 assertIs 复原断言（见 setUp）。
    """
    return {
        name: dataclasses.replace(
            concept, member=tuple(m for m in concept.member if (name, m) not in drop)
        )
        for name, concept in mr.CONCEPT_LEXICON.items()
    }


class MutationDrill(unittest.TestCase):
    """Shared scaffolding: snapshot module state, restore it, prove restore."""

    def setUp(self):
        self._weights = {name: getattr(mr, name) for name in _WEIGHT_NAMES}
        self._lexicon = mr.CONCEPT_LEXICON
        self._rank = mr.rank
        self._concept_hits = mr._concept_hits
        self._concept_hit_parts = mr._concept_hit_parts
        self._polarity_hits = mr._polarity_hits
        # addCleanup 在测试方法结束后执行，此时 with 块已退出、mock 已还原，
        # 所以这里断言的是「没有任何变异泄漏到下一条测试」
        self.addCleanup(self._assert_module_restored)

    def _assert_module_restored(self):
        for name, value in self._weights.items():
            self.assertEqual(getattr(mr, name), value, f"{name} leaked a mutation")
        self.assertIs(mr.CONCEPT_LEXICON, self._lexicon)
        self.assertIs(mr.rank, self._rank)
        self.assertIs(mr._concept_hits, self._concept_hits)
        self.assertIs(mr._concept_hit_parts, self._concept_hit_parts)
        self.assertIs(mr._polarity_hits, self._polarity_hits)

    def assert_baseline_is_perfect(self):
        """Every route compares against this; if it moves the drill is void."""
        self.assertEqual(_top1_hits(GOLDEN), len(GOLDEN))
        self.assertEqual(_top1_hits(HOLDOUT_GOLDEN), len(HOLDOUT_GOLDEN))


class MetricTeethTests(MutationDrill):
    """The four routes where a real defect does move an evaluation metric."""

    def test_killing_l3_drops_holdout_below_threshold(self):
        self.assert_baseline_is_perfect()
        with mock.patch.object(mr, "W_CONCEPT", 0.0):
            # 判据用留出集而不是 golden：实测 golden 在 W_CONCEPT=0 时仍是
            # 8/8=1.000，并不跌破 0.8（L2 单独就能扛住 golden 的 8 对），断言
            # golden 跌破会写下一条实测为假的期望。留出集实测 8/12=0.667。
            self.assertEqual(_top1_hits(HOLDOUT_GOLDEN), 8)
            self.assertLess(_accuracy(HOLDOUT_GOLDEN), THRESHOLD)
            self.assertEqual(_top1_hits(GOLDEN), len(GOLDEN))

    def test_unsorted_rank_drops_golden_below_threshold(self):
        self.assert_baseline_is_perfect()
        with mock.patch.object(mr, "rank", lambda q, c: [(x, mr.score(q, x)) for x in c]):
            self.assertEqual(_top1_hits(GOLDEN), 5)
            self.assertLess(_accuracy(GOLDEN), THRESHOLD)
            # 如实记录盲区：留出集 v1 在「完全不排序」的缺陷实现下仍然 12/12，
            # 因为它每一对的相关事实都排在 stored[0]，同分/不排序都恰好命中
            # （审查发现 M8 的位置偏置）。这条断言不是通过证明，是缺陷证明。
            self.assertEqual(_top1_hits(HOLDOUT_GOLDEN), len(HOLDOUT_GOLDEN))

    def test_emptying_every_lexicon_member_drops_holdout_below_threshold(self):
        self.assert_baseline_is_perfect()
        head_only = {k: dataclasses.replace(v, member=()) for k, v in mr.CONCEPT_LEXICON.items()}
        with mock.patch.object(mr, "CONCEPT_LEXICON", head_only):
            # RC-3a 之后这一路的牙齿更强：member 全空意味着每个类都是双侧
            # head-only，L3 严格归零（修复前还残留 head 级匹配信号），留出集
            # 命中数由 9/12 降到 8/12。数字是实测的，不是估的。
            self.assertEqual(_top1_hits(HOLDOUT_GOLDEN), 8)
            self.assertLess(_accuracy(HOLDOUT_GOLDEN), THRESHOLD)

    def test_emptying_the_whole_lexicon_drops_golden_below_threshold(self):
        self.assert_baseline_is_perfect()
        with mock.patch.object(mr, "CONCEPT_LEXICON", {}):
            self.assertEqual(_top1_hits(GOLDEN), 6)
            self.assertLess(_accuracy(GOLDEN), THRESHOLD)
            # 留出集实测 10/12=0.833，仍 ≥0.8：这一路只有 golden 有牙齿
            self.assertGreaterEqual(_accuracy(HOLDOUT_GOLDEN), THRESHOLD)


class NoMetricTeethTests(MutationDrill):
    """Routes where both sets stay perfect: assert layer behavior, not metrics.

    这四路的共同点是「指标不动」，所以断言必须落在层内行为上。把它们的指标
    断言写成「跌破 0.8」会是伪造的红灯——实测两集都保持 1.000。
    """

    def test_killing_l5_leaves_metrics_untouched_and_silences_the_layer(self):
        self.assert_baseline_is_perfect()
        query, fact = "用户喜欢什么颜色", "用户最近特别喜欢蓝色"
        baseline_score = mr.score(query, fact)
        penalty = mr.transient_penalty(query, fact)
        base_weight = self._weights["W_TRANSIENT"]
        self.assertGreater(penalty, 0.0)
        with mock.patch.object(mr, "W_TRANSIENT", 0.0):
            # L5 在现有两个评测集上不改变任何 top-1 判定：关掉它两集都满分。
            # 本路只验证层内行为消失，不验证指标影响。
            self.assertEqual(_top1_hits(GOLDEN), len(GOLDEN))
            self.assertEqual(_top1_hits(HOLDOUT_GOLDEN), len(HOLDOUT_GOLDEN))
            # 时态降权项不再从合成里被减掉，分数恰好回填一个 W*L5
            self.assertAlmostEqual(
                mr.score(query, fact), baseline_score + base_weight * penalty, places=12
            )

    def test_killing_l4_keeps_metrics_but_collapses_the_safety_margin(self):
        self.assert_baseline_is_perfect()
        golden_margin = _min_margin(GOLDEN)
        holdout_margin = _min_margin(HOLDOUT_GOLDEN)
        with mock.patch.object(mr, "W_PREFERENCE", 0.0):
            self.assertEqual(_top1_hits(GOLDEN), len(GOLDEN))
            self.assertEqual(_top1_hits(HOLDOUT_GOLDEN), len(HOLDOUT_GOLDEN))
            # L4 的真实作用是放大安全余量而不是翻转判定：实测最小分差在
            # golden 上从 +0.2676 掉到 +0.2176，在留出集上从 +0.0500 掉到
            # +0.0000（第 6 对变回完全平局，只能靠输入序侥幸赢）
            self.assertLess(_min_margin(GOLDEN), golden_margin)
            self.assertAlmostEqual(_min_margin(HOLDOUT_GOLDEN), 0.0, places=10)
        self.assertAlmostEqual(holdout_margin, 0.05, places=10)
        # 极性相反的事实在 L4 下是负分，不是零分（M2 的修复点）
        self.assertLess(mr.preference_bonus("用户有什么兴趣", "用户不喜欢摄影"), 0.0)

    def test_reverting_to_naive_substring_counting_resurfaces_m4(self):
        self.assert_baseline_is_perfect()

        def naive(text, concept):
            head = sum(1 for w in concept.head if w in text)
            member = sum(1 for w in concept.member if w in text)
            return head, member

        # RC-3a/RC-3b 之后 L3 的原语是 _concept_hit_parts，_concept_hits 退化成
        # 它的求和包装、已不在打分路径上。变异必须打在真正的原语上：patch 一个
        # 没人调用的函数，指标当然不动，但那不是「这一路无牙齿」而是「假演练」
        # ——与 H2 那条零判别力断言是同一类错误。本条的 patch 点因此随之更新。
        with mock.patch.object(mr, "_concept_hit_parts", naive):
            # 指标不动（实测两集仍满分），但 M4 的反例复活：「生日」同时命中
            # head「生日」与 member「日」，同一份证据被数两次
            self.assertEqual(_top1_hits(GOLDEN), len(GOLDEN))
            self.assertEqual(_top1_hits(HOLDOUT_GOLDEN), len(HOLDOUT_GOLDEN))
            self.assertEqual(naive(mr.normalize("用户的生日"), mr.CONCEPT_LEXICON["生日"]), (1, 1))
        self.assertEqual(
            mr._concept_hit_parts(mr.normalize("用户的生日"), mr.CONCEPT_LEXICON["生日"]), (1, 0)
        )
        self.assertEqual(
            mr._concept_hits(mr.normalize("用户的生日"), mr.CONCEPT_LEXICON["生日"]), 1
        )

        def naive(text, concept):
            return sum(1 for w in (*concept.head, *concept.member) if w in text)

        with mock.patch.object(mr, "_concept_hits", naive):
            # 指标不动（实测两集仍满分），但 M4 的反例复活：「生日」同时命中
            # head「生日」与 member「日」，同一份证据被数两次
            self.assertEqual(_top1_hits(GOLDEN), len(GOLDEN))
            self.assertEqual(_top1_hits(HOLDOUT_GOLDEN), len(HOLDOUT_GOLDEN))
            self.assertEqual(naive(mr.normalize("用户的生日"), mr.CONCEPT_LEXICON["生日"]), 2)
        self.assertEqual(
            mr._concept_hits(mr.normalize("用户的生日"), mr.CONCEPT_LEXICON["生日"]), 1
        )

    def test_splitting_the_polarity_scan_resurfaces_m2(self):
        self.assert_baseline_is_perfect()

        def naive(text):
            positive = sum(1 for w in mr.POSITIVE_MARKERS if w in text)
            negative = sum(1 for w in mr.NEGATIVE_MARKERS if w in text)
            return positive, negative

        with mock.patch.object(mr, "_polarity_hits", naive):
            # 指标不动，但 M2 的语义反转复活：「不喜欢」里的子串「喜欢」被
            # 独立计成正向证据，与「不喜欢」抵消成 0 分，否定事实不再被扣分
            self.assertEqual(_top1_hits(HOLDOUT_GOLDEN), len(HOLDOUT_GOLDEN))
            self.assertEqual(naive(mr.normalize("用户不喜欢摄影")), (1, 1))
            self.assertEqual(mr.preference_bonus("用户有什么兴趣", "用户不喜欢摄影"), 0.0)
        self.assertEqual(mr._polarity_hits(mr.normalize("用户不喜欢摄影")), (0, 1))
        self.assertEqual(mr.preference_bonus("用户有什么兴趣", "用户不喜欢摄影"), -0.5)


class N1SingleCharMemberTests(MutationDrill):
    """N1（阶段三自报第 2 条）：把两条实测事实钉成变异测试。

    N1 = 单字 member 跨类误命中（花粉→粉∈颜色、银行→银∈颜色）。旧记载把不修
    理由写成「收紧会伤到 D11（v2 #29『藏青色』）」，本轮实测推翻：删掉颜色类全部
    15 个单字后 v2 #29 仍命中，因为 _masked_scan 最长优先贪心取到长词「藏青」而非
    单字「青」。真正成立的代价在别的类：删掉全词典 28 个单字 member 会丢 v1 #2/#3
    与 v2 #24。变异体 A 钉「贪心取长词、颜色类可安全收紧」，变异体 B 钉「不能一刀
    切禁止单字 member」。两者的断言值都先实测再写（见 analysis.md §9.1/§9.2）。
    """

    def test_variant_a_dropping_color_singles_keeps_all_three_sets_and_v2_29(self):
        # 基线（实测）：golden 8 / v1 12 / v2 24
        self.assertEqual(_top1_hits(GOLDEN), 8)
        self.assertEqual(_top1_hits(HOLDOUT_GOLDEN), 12)
        self.assertEqual(_v2_hit_count(), 24)
        color_singles = {("颜色", m) for m in _single_char_members()["颜色"]}
        self.assertEqual(len(color_singles), 15)  # 红橙黄绿青蓝紫黑白灰粉棕褐金银
        with mock.patch.object(mr, "CONCEPT_LEXICON", _without_members(color_singles)):
            # 三集命中数一个都不变——删颜色类单字是零代价的（旧「伤 D11」说法为假）
            self.assertEqual(_top1_hits(GOLDEN), 8)
            self.assertEqual(_top1_hits(HOLDOUT_GOLDEN), 12)
            self.assertEqual(_v2_hit_count(), 24)
            # v2 #29（D11「用户喜欢什么颜色」）仍命中：贪心取到长词「藏青」
            row29 = _v2_rows()[29]
            self.assertTrue(row29["hit"])
            self.assertEqual(row29["retrieved"], "用户最喜欢的颜色是藏青色")

    def test_variant_b_dropping_all_28_singles_loses_v1_2_3_and_v2_24(self):
        self.assertEqual(_top1_hits(GOLDEN), 8)
        self.assertEqual(_top1_hits(HOLDOUT_GOLDEN), 12)
        self.assertEqual(_v2_hit_count(), 24)
        all_singles = {(n, m) for n, ms in _single_char_members().items() for m in ms}
        # 全词典 28 个单字 member：颜色15 / 生日4 / 宠物4 / 过敏3 / 称呼2
        self.assertEqual(len(all_singles), 28)
        with mock.patch.object(mr, "CONCEPT_LEXICON", _without_members(all_singles)):
            # golden 不丢（8/8）：它的命中不依赖单字 member
            self.assertEqual(_top1_hits(GOLDEN), 8)
            # v1 丢 #2/#3：12 → 10
            self.assertEqual(_top1_hits(HOLDOUT_GOLDEN), 10)
            v1_flags = [
                mr.rank(str(it["query"]), list(it["stored"]))[0][0] in set(it["relevant"])
                for it in HOLDOUT_GOLDEN
            ]
            self.assertEqual([i for i, hit in enumerate(v1_flags) if not hit], [2, 3])
            # v2 丢 #24：24 → 23，且 #24 由命中翻为未命中
            self.assertEqual(_v2_hit_count(), 23)
            self.assertFalse(_v2_rows()[24]["hit"])


if __name__ == "__main__":
    unittest.main()
