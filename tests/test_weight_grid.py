"""88 格扰动网格的结构锁 + 「唯一定义点」锁（N10-1 / 审查发现 M14、M16）。

为什么给一个纯搬移的重构配测试
------------------------------
本轮把网格枚举与扰动施加方式从 tests/report_retrieval.py 提到 tests/weight_grid.py，
六个报告模式的输出逐字节未变（重构的证据）。但「输出未变」只证明这一次没搬坏，不
证明以后不会：M14 的缺陷形态正是「复现方法里的脚本枚举去重后只产出 9 个配置，覆
盖不了表格里那两行」，M16 的缺陷形态正是「把基线当成一个扰动配置计数」。这两个缺
陷都不是输出错，而是**网格本身的构成**错——输出照样自洽，复核者照抄命令却复现不
出表格。所以构成必须被机器锁住，而不是靠人读代码。

三组断言
--------
GridShapeTests        网格构成：8 + 2 + 78 = 88，基线不在其中，标签唯一。
PerturbedTests        扰动施加：因子作用于当下取值，退出后逐字节恢复，可与 override
                      嵌套（N10 扫候选基值时正是这个嵌套）。
SingleSourceTests     唯一定义点：report_retrieval 不再自带第二份枚举或第二份扰动
                      实现，WEIGHTS 与 weight_grid 里是同一个对象。
"""
from __future__ import annotations

import unittest
from pathlib import Path

import weight_grid as wg
from src import memory_ranker as mr

TESTS = Path(__file__).resolve().parent


class GridShapeTests(unittest.TestCase):
    """M16 的计数口径：基线不算扰动；88 = 8 + 2 + 78。"""

    def test_the_grid_is_exactly_8_plus_2_plus_78(self):
        sizes = wg.grid_sizes()
        self.assertEqual(sizes, {"singles": 8, "uniform": 2, "grid": 78, "total": 88})
        grouped = wg.build_grid()
        self.assertEqual(len(wg.all_configs()), 88)
        self.assertEqual(
            len(grouped["singles"]) + len(grouped["uniform"]) + len(grouped["grid"]),
            len(wg.all_configs()),
            msg="all_configs 必须是三段拼接，不能多也不能少",
        )

    def test_the_baseline_is_not_counted_as_a_perturbation(self):
        """全 1.0 的组合被显式跳过——它就是基线，混进来会把 88 变成 89。"""
        for label, factors in wg.all_configs():
            self.assertFalse(
                all(value == 1.0 for value in factors.values()),
                msg=f"{label} 是基线，不该出现在扰动网格里",
            )

    def test_single_weight_perturbations_touch_exactly_one_weight(self):
        for label, factors in wg.build_grid()["singles"]:
            self.assertEqual(len(factors), 1, msg=label)
            self.assertIn(next(iter(factors)), wg.WEIGHTS)
            self.assertIn(next(iter(factors.values())), wg.SINGLE_LEVELS)

    def test_uniform_scaling_is_separated_from_the_structural_grid(self):
        """四个因子全同＝分数同比缩放，是算术恒等式而不是结构信息，必须单列。"""
        for label, factors in wg.build_grid()["uniform"]:
            self.assertEqual(len(set(factors.values())), 1, msg=label)
        for label, factors in wg.build_grid()["grid"]:
            self.assertGreater(len(set(factors.values())), 1, msg=label)
            self.assertEqual(len(factors), len(wg.WEIGHTS), msg=label)

    def test_every_config_label_is_unique_and_covers_all_four_weights(self):
        labels = [label for label, _ in wg.all_configs()]
        self.assertEqual(len(labels), len(set(labels)), msg="标签重复会让表格两行无法区分")
        # 结构性网格里 3^4=81 个组合减去全 1.0 与 2 个全体缩放 = 78，逐一在场
        for _label, factors in wg.build_grid()["grid"]:
            for value in factors.values():
                self.assertIn(value, wg.FACTOR_LEVELS)

    def test_the_grid_enumerates_every_cell_of_the_product_space(self):
        """M14：表格里的每一行都必须能由这一份枚举产出，包括「改 2 个」与「改 4 个」。"""
        changed_counts = {}
        for _label, factors in wg.build_grid()["grid"]:
            k = sum(1 for v in factors.values() if v != 1.0)
            changed_counts[k] = changed_counts.get(k, 0) + 1
        for n_changed in (1, 2, 3, 4):
            self.assertIn(n_changed, changed_counts, msg=f"没有「改 {n_changed} 个权重」的行")
        # 组合数学核对：改了 k 个权重的组合数是 C(4,k)*2^k，k=1..4 合计 80；其中
        # k=4 有 16 个，2 个是全体缩放已被单列，故结构性网格里 k=4 剩 14 个。
        self.assertEqual(changed_counts, {1: 8, 2: 24, 3: 32, 4: 14})
        self.assertEqual(sum(changed_counts.values()), 78)


class PerturbedTests(unittest.TestCase):
    """扰动施加方式的语义锁：因子作用于当下取值，且退出后必须逐字节恢复。"""

    def test_factors_scale_the_live_value_and_restore_it(self):
        before = {name: getattr(mr, name) for name in wg.WEIGHTS}
        with wg.perturbed(mr, {"W_BIGRAM": 0.5, "W_CONCEPT": 2.0}):
            self.assertAlmostEqual(mr.W_BIGRAM, before["W_BIGRAM"] * 0.5)
            self.assertAlmostEqual(mr.W_CONCEPT, before["W_CONCEPT"] * 2.0)
            self.assertEqual(mr.W_PREFERENCE, before["W_PREFERENCE"])
            self.assertEqual(mr.W_TRANSIENT, before["W_TRANSIENT"])
        after = {name: getattr(mr, name) for name in wg.WEIGHTS}
        self.assertEqual(before, after, msg="扰动退出后权重必须完全恢复")

    def test_override_sets_an_absolute_value_and_nests_with_perturbed(self):
        """N10 扫候选基值用的正是这个嵌套：因子作用于被覆盖后的基值。"""
        before = mr.W_PREFERENCE
        with wg.override(mr, "W_PREFERENCE", 0.20):
            self.assertEqual(mr.W_PREFERENCE, 0.20)
            with wg.perturbed(mr, {"W_PREFERENCE": 0.5}):
                self.assertAlmostEqual(mr.W_PREFERENCE, 0.10)
            self.assertEqual(mr.W_PREFERENCE, 0.20)
        self.assertEqual(mr.W_PREFERENCE, before)

    def test_a_failed_measurement_inside_the_context_still_restores(self):
        before = {name: getattr(mr, name) for name in wg.WEIGHTS}
        with self.assertRaises(RuntimeError):
            with wg.perturbed(mr, {name: 2.0 for name in wg.WEIGHTS}):
                raise RuntimeError("量到一半炸了")
        self.assertEqual(before, {name: getattr(mr, name) for name in wg.WEIGHTS},
                         msg="异常路径下也必须恢复，否则后面的格子全部被污染")


class SingleSourceTests(unittest.TestCase):
    """唯一定义点：第二份枚举或第二份扰动实现就是 M14 的复发条件。"""

    def test_report_retrieval_no_longer_carries_its_own_copy(self):
        import report_retrieval as rr

        source = (TESTS / "report_retrieval.py").read_text(encoding="utf-8")
        self.assertFalse(hasattr(rr, "_perturbed"), msg="本地扰动实现复活了")
        self.assertFalse(hasattr(rr, "_stop"), msg="本地扰动实现复活了")
        self.assertNotIn("import itertools", source,
                         msg="网格枚举又回到 report_retrieval 里了")
        self.assertIs(rr.WEIGHTS, wg.WEIGHTS,
                      msg="权重名必须与 weight_grid 是同一个对象，不是另一份副本")

    def test_the_grid_definition_lives_in_exactly_one_file(self):
        # 排除定义点本身，也排除本文件：断言里出现的字面量自己就会命中，那是自指
        skip = {"weight_grid.py", Path(__file__).name}
        copies = [path.name for path in sorted(TESTS.glob("*.py"))
                  if path.name not in skip
                  and "itertools.product" in path.read_text(encoding="utf-8")]
        self.assertEqual(copies, [], msg=f"这些文件里还有第二份网格枚举：{copies}")


if __name__ == "__main__":
    unittest.main()
