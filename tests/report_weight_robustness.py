"""N10 权重鲁棒性：判据、口径与决策规程。

为什么这个文件先于实验落盘
--------------------------
阶段二的极性修复（RC-4 / RC-7）提高了命中数，同时降低了权重鲁棒性：结构性网格
里出现了把 v2 命中数拉低的配置，全体扰动下「命中对最小分差」也比阶段一的实测值
低了一个数量级（发现编号 N10）。这是真实代价，不能就这么交给外部复核者。

但「调权重」这件事极易滑向「为了让某几对通过而调参」。所以判据先写死、先提交，
再跑实验：本文件的第一格 commit 只含判据与空跑框架，**不含任何本轮实测分数**；
连硬约束的门槛值都是运行时从语料规模与既有棘轮常量现读的，不硬编码在这里。扫描
实现与结果落在后一格。复核者只要比对两格 commit 的先后与 diff，就能确认判据不是
照着结果倒推的——这与 v2 盲测集「计分口径先于分数定下」用的是同一种纪律。

判据（先写，后跑，可被 diff 证伪）
==================================

主目标（唯一）
    在 88 格扰动网格上，最大化「最恶劣命中对分差」：

        objective(candidate) = min over 全部 88 个扰动配置 of  worst(config)
        worst(config)        = min over 三集 of  命中对的最小 (top1 - top2)

    「命中对的最小分差」量的是**一个已经判对的结论离被推翻有多远**，这才是权重
    鲁棒性的含义。它与「全体对的最小分差」是两个不同的量（后者量的是哪对最接近
    随机，在 v2 上恒由零字面重叠那几对贡献），M15 关心的是前者，本判据也是。

    取 min over 88 格而不是取基线值：只看基线等于把鲁棒性问题又变回命中数问题。

硬约束（三条全满足才允许采纳；任一不满足即淘汰该候选值）
    C1  golden 命中数 == golden 可判定对数（满分，零回归）
    C2  v1 命中数     == v1 可判定对数（满分，零回归）
    C3  v2 命中数     >= 既有棘轮常量（零回归）

    三条都在**全部 88 格上逐格检查**，不只在基线权重下检查。门槛值运行时现读：
    C1/C2 的满分线取自语料里「stored 非空且 relevant 非空」的对数，C3 取自
    tests/test_holdout_v2.py 的 V2_RATCHET_HITS（阶段二已钉的棘轮常量，不是本
    轮扫描的产物）。

明确禁止的选择理由
    「这个值能让某几对（例如 v2 的 #7 / #23）通过」**不是**合法的采纳理由。
    命中数是约束，不是目标。若某候选值让 v2 命中数上涨、但最恶劣命中对分差没有
    改善，按判据它必须被拒绝，而且这个诱惑与这次拒绝要如实写进报告——隐瞒它等
    于让复核者无法判断有没有 cherry-pick。
    同理，「这个值让宏平均 P/R 更好看」也不是理由。P/R 与命中数一样属于约束侧，
    主目标只有一个：最恶劣命中对分差。

一次只动一个变量
    主扫描只动 W_PREFERENCE（既有归因显示，造成命中下降的配置有共同因子，指向
    它相对 W_BIGRAM 偏低）。附带扫描只动 W_BIGRAM，独立一轮。
    **不做二维联合寻优**：联合寻优的搜索空间大到足以「找到」任何想要的结论，那
    就是过拟合，与「为了让某几对通过而调参」是同一种错误，只是更难被发现。

口径陷阱的显式处置
    某配置下若三集命中对全空，min 会得到 +inf，看起来像「分差无穷大＝最稳健」。
    这是假的：那种配置已经把该判对的全判错了。处置是把它标为违约（触发 C1/C2/C3
    之一），违约配置不参与主目标，且该候选值整体淘汰。inf 一律显式检出并报告，
    不许静默当成好结果。

决策规程
    若存在满足三条硬约束、且最恶劣命中对分差显著改善的候选值 → 采纳，并重做全
    部消融与三集棘轮；棘轮常量按新实测值重新保守取整，取整论证沿用阶段二的方
    法：余量必须小于「翻转一对」造成的宏平均变化量，否则棘轮挡不住一对的回归。
    若不存在 → 保持现状值不动，把「扫了几个值、无一能在零回归下改善最恶劣分差」
    这个负面结果如实写进文档。负面结果同样是有效产出：它把「是否该调权重」这个
    问题从悬空变成已闭合。
    无论结论如何，完整扫描表都要报出来。

用法
----
    ./.venv/bin/python tests/report_weight_robustness.py criteria
        只打印判据、网格构成、候选值与硬约束门槛的来源。**不产生任何分数。**
    ./.venv/bin/python tests/report_weight_robustness.py sweep pre
    ./.venv/bin/python tests/report_weight_robustness.py sweep big
        对单个权重扫全部候选值，每个候选值跑完整 88 格。
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

TESTS = Path(__file__).resolve().parent
REPO = TESTS.parent
for _p in (str(REPO), str(TESTS)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from src import memory_ranker as mr  # noqa: E402
from test_holdout_v2 import HoldoutV2ScoringTests, score_holdout_v2  # noqa: E402

# 棘轮常量是测试类属性而不是模块级常量，现读而不重写：重写一份就会与棘轮失同步，
# 而 C3 的全部证据力正来自「门槛值是既有那个」。
V2_RATCHET_HITS = HoldoutV2ScoringTests.V2_RATCHET_HITS
from report_retrieval import CORPORA, _hits, _min_margin, _text  # noqa: E402
import weight_grid as wg  # noqa: E402

# 候选值按升序排，所以现状值不必是首项（big 那轮的现状值排在第 4）。是否在场由
# check_candidates_are_anchored() 运行时与 mr 的常量交叉校验，避免现状被改动后本
# 表悄悄失真——扫描表里没有现状那一行，任何改善或恶化都失去参照点。顺序即报告
# 里的行顺序。
CANDIDATES: dict[str, tuple[str, tuple[float, ...]]] = {
    "pre": ("W_PREFERENCE", (0.10, 0.125, 0.15, 0.175, 0.20, 0.25)),
    "big": ("W_BIGRAM", (0.15, 0.20, 0.25, 0.30, 0.35)),
}


def decidable(corpus: list[dict]) -> int:
    """stored 非空且 relevant 非空的对数，即该集的「满分线」。"""
    return sum(1 for pair in corpus
               if [_text(f) for f in pair["stored"]] and {_text(f) for f in pair["relevant"]})


def hard_constraints() -> dict[str, int]:
    """三条硬约束的门槛值。全部现读，本文件里不硬编码任何实测分数。"""
    return {
        "golden": decidable(CORPORA["golden"]),          # C1 满分线
        "v1": decidable(CORPORA["v1"]),                  # C2 满分线
        "v2": V2_RATCHET_HITS,                           # C3 既有棘轮常量
    }


def check_candidates_are_anchored() -> list[str]:
    """两项机器校验，把判据里靠自觉的部分变成能失败的断言。

    A 现状值必须**在**候选表里。否则「零回归」无从对照：扫描表里没有现状那一行，
      任何改善或恶化都失去参照点，也就无法排除「挑了个好看的基线来比」。
    B 每轮只动一个变量。候选表里只允许出现一个权重名，其余三个权重在整轮扫描中
      保持 mr 里的当下取值不动。判据禁止二维联合寻优，这里就是它的执行点。
    """
    problems = []
    for which, (name, values) in CANDIDATES.items():
        live = getattr(mr, name)
        if live not in values:
            problems.append(f"{which}: mr.{name} 现值 {live} 不在候选表 {values} 里")
        if len(values) != len(set(values)):
            problems.append(f"{which}: 候选表有重复值 {values}")
        if name not in wg.WEIGHTS:
            problems.append(f"{which}: {name} 不是四个权重之一")
    return problems


def untouched_weights(name: str) -> tuple[str, ...]:
    """本轮扫描中保持不动的其余三个权重（「一次只动一个变量」的另一半）。"""
    return tuple(w for w in wg.WEIGHTS if w != name)


def evaluate(factor_map: dict[str, float], base: tuple[str, float] | None = None) -> dict:
    """在给定基值覆盖 + 扰动因子下，量一次三集。

    返回命中数、宏平均 P/R、命中对最小分差（含所属集与对号）、以及违约清单。
    """
    raise NotImplementedError("扫描实现在后一格 commit；本格只落判据与框架")


def worst_over_grid(base: tuple[str, float]) -> dict:
    """在给定基值下跑完整 88 格，取主目标（min over 配置 of worst(config)）。"""
    raise NotImplementedError("扫描实现在后一格 commit；本格只落判据与框架")


def sweep(which: str) -> None:
    raise NotImplementedError("扫描实现在后一格 commit；本格只落判据与框架")


def print_criteria() -> None:
    """打印判据与网格构成。本函数刻意不产生任何分数。"""
    sizes = wg.grid_sizes()
    limits = hard_constraints()
    print("=" * 100)
    print("N10 权重鲁棒性判据（先写后跑；本模式不产生任何分数）")
    print("=" * 100)
    body = __doc__.split("判据（先写，后跑，可被 diff 证伪）")[1].split("用法")[0]
    body = [ln for ln in body.strip().split("\n") if set(ln.strip()) != {"="}]
    print("\n".join(body).strip())
    print()
    print("-" * 100)
    print("扰动网格构成（定义点 tests/weight_grid.py，与 sensitivity 模式共用同一份枚举）")
    print("-" * 100)
    print(f"  单权重扰动   {sizes['singles']:>3}  = 4 个权重 × {{0.5, 2.0}}")
    print(f"  全体缩放     {sizes['uniform']:>3}  = 四个因子全 0.5 / 全 2.0（分差同比缩放是算术必然，单列）")
    print(f"  结构性网格   {sizes['grid']:>3}  = 3^4=81 个组合，显式跳过全 1.0，再减掉上面 2 个")
    print(f"  合计         {sizes['total']:>3}  格（基线不计入扰动，M16 口径）")
    print()
    print("-" * 100)
    print("硬约束门槛值的来源（运行时现读，本文件不硬编码）")
    print("-" * 100)
    for name, corpus in CORPORA.items():
        print(f"  {name:<7} 语料 {len(corpus):>3} 对，其中可判定 {decidable(corpus):>3} 对")
    print(f"  C1 golden 命中数必须 == {limits['golden']}（可判定对数，即满分）")
    print(f"  C2 v1     命中数必须 == {limits['v1']}（可判定对数，即满分）")
    print(f"  C3 v2     命中数必须 >= {limits['v2']}"
          f"（取自 HoldoutV2ScoringTests.V2_RATCHET_HITS，阶段二已钉的棘轮常量）")
    print()
    print("-" * 100)
    print("候选值（一次只动一个变量；现状值必须在表内，已与实现常量交叉校验）")
    print("-" * 100)
    problems = check_candidates_are_anchored()
    for which, (name, values) in CANDIDATES.items():
        live = getattr(mr, name)
        kept = ", ".join(f"{w}={getattr(mr, w):g}" for w in untouched_weights(name))
        mark = [f"{v:g}" + ("<-现状" if v == live else "") for v in values]
        print(f"  {which:<4} {name:<14} 现值={live:g}  候选={mark}")
        print(f"       本轮不动的其余三个权重：{kept}")
    print("  锚定校验（现状值在表内 + 每轮只动一个变量）:",
          "PASS" if not problems else "FAIL " + "; ".join(problems))
    print()
    print("不做 W_PREFERENCE × W_BIGRAM 的二维联合寻优：搜索空间大到足以「找到」任何")
    print("想要的结论，那就是过拟合。附带扫描 W_BIGRAM 时独立一轮，两轮结果分开报。")


MODES = {"criteria": print_criteria, "sweep": sweep}


def main(argv: list[str]) -> int:
    mode = argv[1] if len(argv) > 1 else "criteria"
    if mode not in MODES:
        print(f"未知模式 {mode!r}，可用：{sorted(MODES)}")
        return 2
    if mode == "sweep":
        if len(argv) < 3 or argv[2] not in CANDIDATES:
            print(f"sweep 需要第二个参数，可用：{sorted(CANDIDATES)}")
            return 2
        sweep(argv[2])
    else:
        MODES[mode]()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
