"""The 88-cell perturbation grid: single point of definition.

为什么单独一个文件
------------------
tests/report_retrieval.py 的 sensitivity 模式与 N10 的权重鲁棒性扫描必须跑**同
一个**网格。如果两处各写一份枚举逻辑，两份表格的 88 行迟早对不上——审查发现
M14 指的正是这个缺陷的上一版形态：「复现方法」里的脚本枚举去重后只产出 9 个配
置，覆盖不了表格里「改 2 个权重」与「改 4 个权重」那两行，复核者照抄命令复现不
出表格。把网格提到这里，两个脚本共用一个定义点，「照抄命令能 100% 复现表格」才
有结构保证，而不是靠人工比对两份代码。

88 格的构成（与 M16 的计数口径一致：基线不算扰动）
----------------------------------------------------
    单权重扰动   8 = 4 个权重 × {0.5, 2.0}
    全体缩放     2 = 四个因子全为 0.5 / 全为 2.0
    结构性网格  78 = 3^4 = 81 个组合，显式跳过全 1.0（基线），再减掉上面那 2 个
    --------------------------------------------------------------
    合计        88

全体缩放单独分出来的理由：四个权重乘同一个因子会把所有分数同比缩放，分差也跟着
同比缩放，这是算术恒等式而不是结构信息。混在网格里当「最恶劣方向」报是测量缺陷。
"""
from __future__ import annotations

import itertools
from contextlib import contextmanager
from unittest import mock

# 顺序即标签顺序，改动会让既有报告里的配置名对不上
WEIGHTS = ("W_BIGRAM", "W_CONCEPT", "W_PREFERENCE", "W_TRANSIENT")
SHORT = {"W_BIGRAM": "BIG", "W_CONCEPT": "CON", "W_PREFERENCE": "PRE", "W_TRANSIENT": "TRA"}
FACTOR_LEVELS = (0.5, 1.0, 2.0)
SINGLE_LEVELS = (0.5, 2.0)


def build_singles() -> list[tuple[str, dict[str, float]]]:
    """8 个单权重扰动：每次只动一个权重，其余保持基值。"""
    return [(f"{name} x{factor}", {name: factor})
            for name in WEIGHTS for factor in SINGLE_LEVELS]


def build_product() -> tuple[list[tuple[str, dict[str, float]]], list[tuple[str, dict[str, float]]]]:
    """(全体缩放 2 个, 结构性网格 78 个)。全 1.0 的组合被显式跳过。"""
    uniform: list[tuple[str, dict[str, float]]] = []
    grid: list[tuple[str, dict[str, float]]] = []
    for factors in itertools.product(FACTOR_LEVELS, repeat=len(WEIGHTS)):
        if all(factor == 1.0 for factor in factors):
            continue                      # 基线不算扰动（M16 口径）
        label = " ".join(f"{SHORT[name]}x{factor:g}" for name, factor in zip(WEIGHTS, factors))
        target = uniform if len(set(factors)) == 1 else grid
        target.append((label, dict(zip(WEIGHTS, factors))))
    return uniform, grid


def build_grid() -> dict[str, list[tuple[str, dict[str, float]]]]:
    """{"singles": 8, "uniform": 2, "grid": 78}，三段合计 88 格。"""
    uniform, grid = build_product()
    return {"singles": build_singles(), "uniform": uniform, "grid": grid}


def all_configs() -> list[tuple[str, dict[str, float]]]:
    """88 格拉平成一个列表，顺序固定为 singles → uniform → grid。"""
    grouped = build_grid()
    return grouped["singles"] + grouped["uniform"] + grouped["grid"]


def grid_sizes() -> dict[str, int]:
    grouped = build_grid()
    sizes = {key: len(value) for key, value in grouped.items()}
    sizes["total"] = sum(sizes.values())
    return sizes


@contextmanager
def override(module, name: str, value: float):
    """把某个权重常量**设为绝对值**（不是乘因子），退出时恢复原值。

    N10 扫候选基值时用它：先 override 基值，再在其内层用 perturbed 跑 88 格，
    这样格子里的因子作用于被覆盖后的基值，而不是作用于仓库里的现状值。
    """
    with mock.patch.object(module, name, value):
        yield value


@contextmanager
def perturbed(module, factor_map: dict[str, float]):
    """按因子缩放若干权重；因子读取的是**当下**的模块属性值，故可与 override 嵌套。"""
    patches = [mock.patch.object(module, name, getattr(module, name) * factor)
               for name, factor in factor_map.items()]
    for patch in patches:
        patch.start()
    try:
        yield
    finally:
        for patch in reversed(patches):   # LIFO，与 start 顺序相反
            patch.stop()
