"""N10 判据机器本身的锁：门槛值、违约语义、主目标取值、inf 陷阱、锚定校验。

为什么锁机器而不锁结论
----------------------
扫描结论（本轮：保持现状值不动）写在 commit 正文与文档里，它是**一次测量的结果**，
下一轮重测就可能变，不该被断言钉死。但得出结论所用的那台机器必须被钉死：门槛值取
自哪里、C1/C2 与 C3 的比较语义是否不同、主目标是不是 min over 三集、命中对全空时的
+inf 有没有被当成「最稳健」吞掉、现状值离开候选表时会不会静默失去参照点。机器错了，
结论一定错，而且错得很像对的。

这里全部是合成输入或单次测量，不跑 88 格：一格扫描要几秒，放进单测会让套件从零点
几秒变成十几秒，代价与收益不成比例。完整扫描由 `report_weight_robustness.py sweep`
复跑，可复现性由「连跑两次输出逐字节相同」保证。
"""
from __future__ import annotations

import math
import unittest
from collections import Counter
from unittest import mock

import report_weight_robustness as rw
import test_holdout_v2 as hv2
from src import memory_ranker as mr

# 棘轮常量现读而不重写。用模块限定名而不把测试类绑到本模块的命名空间里：
# unittest 的 discover 会把模块里任何 TestCase 子类当成自己的用例，所以不管叫
# HoldoutV2ScoringTests 还是叫别的名字，只要绑上来，test_holdout_v2 的 8 个用例
# 就会在本文件里被重复跑一遍，把单测总数算脏。
def ratchet(name: str):
    return getattr(hv2.HoldoutV2ScoringTests, name)


def fake(hits: dict[str, int], margins: dict[str, float] | None = None) -> dict[str, dict]:
    """造一份 evaluate() 形状的测量结果，只填判据用到的字段。"""
    margins = margins or {}
    return {
        name: {
            "hits": hits[name],
            "n": len(rw.CORPORA[name]),
            "precision": 1.0,
            "recall": 1.0,
            "margin": margins.get(name, 0.5),
            "index": 0,
            "excluded": 0,
            "flags": [],
        }
        for name in rw.CORPORA
    }


class ThresholdTests(unittest.TestCase):
    """门槛值必须现读，不许在扫描脚本里硬编码一份副本。"""

    def test_thresholds_come_from_the_corpora_and_the_existing_ratchet(self):
        limits = rw.hard_constraints()
        self.assertEqual(limits["golden"], rw.decidable(rw.CORPORA["golden"]))
        self.assertEqual(limits["v1"], rw.decidable(rw.CORPORA["v1"]))
        self.assertEqual(limits["v2"], ratchet("V2_RATCHET_HITS"))
        self.assertEqual(limits, {"golden": 8, "v1": 12, "v2": 24})

    def test_decidable_skips_pairs_without_a_right_answer(self):
        # v2 的 32 对里有 2 对 relevant 为空：没有正确答案，不能算进满分线
        self.assertEqual(rw.decidable(rw.CORPORA["v2"]), 30)
        self.assertEqual(len(rw.CORPORA["v2"]), 32)


class ViolationSemanticsTests(unittest.TestCase):
    """C1/C2 是满分线（==），C3 是棘轮线（>=）。语义混用会让判据静默失效。"""

    def setUp(self):
        self.limits = rw.hard_constraints()

    def test_a_full_score_line_rejects_both_sides(self):
        self.assertEqual(rw.violations(fake({"golden": 8, "v1": 12, "v2": 24}), self.limits), [])
        self.assertTrue(any("C1" in v for v in
                            rw.violations(fake({"golden": 7, "v1": 12, "v2": 24}), self.limits)))
        self.assertTrue(any("C2" in v for v in
                            rw.violations(fake({"golden": 8, "v1": 10, "v2": 24}), self.limits)))

    def test_the_ratchet_line_only_rejects_below(self):
        self.assertEqual(rw.violations(fake({"golden": 8, "v1": 12, "v2": 23}), self.limits),
                         ["C3 v2=23 违约(需 >= 24)"])
        # 涨到 25 不算违约：棘轮是下限。但涨命中不构成采纳理由，那由判据正文管。
        self.assertEqual(rw.violations(fake({"golden": 8, "v1": 12, "v2": 25}), self.limits), [])

    def test_violations_are_reported_per_constraint_not_as_one_blob(self):
        found = rw.violations(fake({"golden": 7, "v1": 10, "v2": 22}), self.limits)
        self.assertEqual(len(found), 3, msg="三条约束各报一条，合并成一条就无法归因")


class ObjectiveTests(unittest.TestCase):
    """主目标 = min over 三集 of 命中对最小分差，且必须报出所属集与对号。"""

    def test_worst_names_the_owner_and_the_pair(self):
        margins = {"golden": 0.2676, "v1": 0.0500, "v2": 0.0067}
        result = fake({"golden": 8, "v1": 12, "v2": 24}, margins)
        result["v2"]["index"] = 5
        margin, owner, index = rw.worst(result)
        self.assertEqual((margin, owner, index), (0.0067, "v2", 5))

    def test_the_infinite_margin_trap_is_not_swallowed_as_most_robust(self):
        """三集命中对全空 -> _min_margin 返回 +inf，看起来像「分差无穷大＝最稳健」。"""
        result = fake({"golden": 0, "v1": 0, "v2": 0},
                      {"golden": math.inf, "v1": math.inf, "v2": math.inf})
        margin, _owner, _index = rw.worst(result)
        self.assertTrue(math.isinf(margin), msg="这就是判据点名的那个陷阱形态")
        self.assertEqual(len(rw.violations(result, rw.hard_constraints())), 3,
                         msg="inf 必须同时被判为三条全违约，不许静默当选最稳健")

    def test_a_corpus_with_no_hits_at_all_is_still_a_violation_not_a_free_pass(self):
        result = fake({"golden": 8, "v1": 12, "v2": 0}, {"v2": math.inf})
        self.assertNotEqual(rw.worst(result)[1], "v2", msg="min 不该被 +inf 那一集抢走")
        self.assertTrue(any("C3" in v for v in rw.violations(result, rw.hard_constraints())))


class MeasurementTests(unittest.TestCase):
    """evaluate() 的口径必须与既有实现同源，且退出后权重逐字节恢复。"""

    def test_the_shipped_weights_reproduce_the_three_corpus_baseline(self):
        result = rw.evaluate()
        self.assertEqual({name: result[name]["hits"] for name in rw.CORPORA},
                         {"golden": 8, "v1": 12, "v2": 24})
        self.assertAlmostEqual(result["v2"]["precision"],
                               ratchet("V2_RATCHET_PRECISION"), places=2)
        self.assertAlmostEqual(result["v2"]["recall"],
                               ratchet("V2_RATCHET_RECALL"), places=2)
        self.assertEqual(rw.violations(result, rw.hard_constraints()), [],
                         msg="基线权重下三集必须零违约，否则判据的参照点本身就不成立")

    def test_overriding_the_base_does_not_leak_into_the_module(self):
        before = {name: getattr(mr, name) for name in rw.wg.WEIGHTS}
        rw.evaluate({"W_BIGRAM": 2.0}, ("W_PREFERENCE", 0.25))
        self.assertEqual(before, {name: getattr(mr, name) for name in rw.wg.WEIGHTS},
                         msg="扫描跑完必须把权重还原，否则后面的格子全被污染")

    def test_the_factors_act_on_the_overridden_base_not_on_the_shipped_one(self):
        """嵌套顺序是硬的：先 override 基值，再在内层按因子缩放。"""
        with mock.patch.object(mr, "W_PREFERENCE", 0.20):
            with rw.wg.perturbed(mr, {"W_PREFERENCE": 0.5}):
                self.assertAlmostEqual(mr.W_PREFERENCE, 0.10)


class AnchoringTests(unittest.TestCase):
    """现状值一旦离开候选表，扫描就失去参照点；这必须被机器发现，不能靠自觉。"""

    def test_a_live_value_outside_the_candidate_table_is_caught(self):
        with mock.patch.object(mr, "W_PREFERENCE", 0.11):
            problems = rw.check_candidates_are_anchored()
        self.assertTrue(problems, msg="现值 0.11 不在候选表里，必须报错")
        self.assertIn("W_PREFERENCE", problems[0])

    def test_the_shipped_values_are_inside_their_tables(self):
        self.assertEqual(rw.check_candidates_are_anchored(), [])

    def test_each_round_moves_exactly_one_variable(self):
        for which, (name, values) in rw.CANDIDATES.items():
            self.assertIn(name, rw.wg.WEIGHTS)
            self.assertEqual(len(rw.untouched_weights(name)), len(rw.wg.WEIGHTS) - 1,
                             msg=f"{which} 那轮应只有 {name} 在动")
            self.assertNotIn(name, rw.untouched_weights(name))
            self.assertEqual(len(values), len(set(values)), msg="候选值重复会让表格两行同义")


class SecondaryMetricTests(unittest.TestCase):
    """次级比较量：违约格数只说坏了几格，违约深度与波及面才说坏得多深、多广。"""

    def summary(self, violating_hits: list[dict], lost: dict[str, list[int]]) -> dict:
        return {
            "violating": [{"hits": hits} for hits in violating_hits],
            "loss_tally": {name: Counter(lost.get(name, [])) for name in rw.CORPORA},
        }

    def test_no_violation_means_zero_depth(self):
        self.assertEqual(rw.depth(self.summary([], {})), 0)

    def test_depth_separates_a_shallow_breach_from_a_deep_one(self):
        """同样 9 格违约，掉到 23 与掉到 20 是两件差很远的事，必须能区分。"""
        shallow = self.summary([{"golden": 8, "v1": 12, "v2": 23}] * 9, {})
        deep = self.summary([{"golden": 8, "v1": 12, "v2": 20}] * 9, {})
        self.assertEqual(rw.depth(shallow), 1)
        self.assertEqual(rw.depth(deep), 4)

    def test_depth_is_the_min_over_cells_and_the_sum_over_corpora(self):
        mixed = self.summary([{"golden": 7, "v1": 12, "v2": 23},   # 缺口 1 + 1 = 2
                              {"golden": 8, "v1": 12, "v2": 21}],  # 缺口 3
                             {})
        self.assertEqual(rw.depth(mixed), 2, msg="取最浅那一格，不是取总和也不是取最深")

    def test_breadth_counts_distinct_lost_pairs_across_corpora(self):
        found = self.summary([], {"v2": [7, 7, 23], "v1": [6]})
        self.assertEqual(rw.distinct_lost_pairs(found), 3, msg="#7 被翻两次只算一对")


if __name__ == "__main__":
    unittest.main()
