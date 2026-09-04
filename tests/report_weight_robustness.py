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
from collections import Counter
from contextlib import ExitStack
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


def evaluate(factor_map: dict[str, float] | None = None,
             base: tuple[str, float] | None = None) -> dict[str, dict]:
    """在给定基值覆盖 + 扰动因子下，量一次三集。

    口径全部复用既有实现，本文件不另写第二份（第二份口径就是第二处会漂移的真相）：
    命中数与宏平均 P/R 走 score_holdout_v2——就是 v2 盲测集「计分口径先于分数定下」
    的那一套；命中对最小分差走 report_retrieval._min_margin(hits_only=True)——就是
    sensitivity 模式报「实测最恶劣方向」用的那一个。

    base 与 factor_map 的嵌套顺序是硬的：先 override 基值，再在内层按因子缩放，这
    样格子里的因子作用于被覆盖后的基值，而不是作用于仓库里的现状值。反过来嵌套等
    于扫了一个跟候选值无关的网格。
    """
    with ExitStack() as stack:
        if base is not None:
            stack.enter_context(wg.override(mr, base[0], base[1]))
        if factor_map:
            stack.enter_context(wg.perturbed(mr, factor_map))
        out: dict[str, dict] = {}
        for name, corpus in CORPORA.items():
            scored = score_holdout_v2(corpus)
            margin, index, excluded = _min_margin(corpus, hits_only=True)
            out[name] = {
                "hits": sum(1 for row in scored["rows"] if row["hit"]),
                "flags": [row["hit"] for row in scored["rows"]],
                "n": len(corpus),
                "precision": scored["precision"],
                "recall": scored["recall"],
                "margin": margin,
                "index": index,
                "excluded": excluded,
            }
        return out


def worst(result: dict[str, dict]) -> tuple[float, str, int]:
    """min over 三集 of 命中对最小分差 -> (分差, 所属集, 对号)。判据里的 worst()。"""
    return min((cell["margin"], name, cell["index"]) for name, cell in result.items())


def violations(result: dict[str, dict], limits: dict[str, int]) -> list[str]:
    """三条硬约束逐格检查；返回空列表＝该格无违约。门槛值全部来自 hard_constraints()。"""
    out = []
    for tag, name in (("C1", "golden"), ("C2", "v1"), ("C3", "v2")):
        hits, limit = result[name]["hits"], limits[name]
        # C1/C2 是满分线（==），C3 是棘轮线（>=）：三集的门槛语义不同，不能一律用 >=
        bad = hits < limit if name == "v2" else hits != limit
        if bad:
            need = ">=" if name == "v2" else "=="
            out.append(f"{tag} {name}={hits} 违约(需 {need} {limit})")
    return out


def worst_over_grid(base: tuple[str, float]) -> dict:
    """在给定基值下跑完整 88 格，取主目标（min over 配置 of worst(config)）。

    违约格不参与主目标（判据里对 inf 陷阱的处置），但只要有一格违约，该候选值整体
    淘汰——此时 objective 只是给复核者看的信息量，不构成任何采纳理由。
    """
    limits = hard_constraints()
    baseline = evaluate(base=base)
    records = []
    for label, factor_map in wg.all_configs():
        result = evaluate(factor_map, base)
        margin, owner, index = worst(result)
        changed = {name: (baseline[name]["hits"], result[name]["hits"])
                   for name in CORPORA if result[name]["hits"] != baseline[name]["hits"]}
        lost = {name: [i for i, (b, a) in enumerate(zip(baseline[name]["flags"], result[name]["flags"]))
                       if b and not a]
                for name in changed}
        gained = {name: [i for i, (b, a) in enumerate(zip(baseline[name]["flags"], result[name]["flags"]))
                         if a and not b]
                  for name in changed}
        records.append({
            "label": label,
            "margin": margin,
            "owner": owner,
            "index": index,
            "violations": violations(result, limits),
            "infinite": sorted(name for name, cell in result.items()
                               if math.isinf(cell["margin"])),
            "changed": changed,
            "lost": lost,
            "gained": gained,
            "hits": {name: result[name]["hits"] for name in CORPORA},
        })
    pool = [record for record in records if not record["violations"]] or records
    best = min(pool, key=lambda record: record["margin"])
    loss_tally: dict[str, Counter] = {name: Counter() for name in CORPORA}
    gain_tally: dict[str, Counter] = {name: Counter() for name in CORPORA}
    for record in records:
        for name, indices in record["lost"].items():
            loss_tally[name].update(indices)
        for name, indices in record["gained"].items():
            gain_tally[name].update(indices)
    return {
        "base": base,
        "baseline": baseline,
        "records": records,
        "objective": best["margin"],
        "objective_where": (best["label"], best["owner"], best["index"]),
        "violating": [record for record in records if record["violations"]],
        "flipped": [record for record in records if record["changed"]],
        "infinite": [record for record in records if record["infinite"]],
        "loss_tally": loss_tally,
        "gain_tally": gain_tally,
    }


def _tally_text(tally: Counter, total: int) -> str:
    """把「哪几对被翻掉、各被翻掉几次」压成一行。次数分母是 88 格。"""
    if not tally:
        return "无"
    return " ".join(f"#{i}(x{c}/{total})" for i, c in sorted(tally.items()))


def print_candidate(name: str, value: float, summary: dict, live: float) -> None:
    baseline = summary["baseline"]
    total = len(summary["records"])
    tag = "  <- 现状" if value == live else ""
    print("-" * 132)
    print(f"候选 {name}={value:g}{tag}")
    print("-" * 132)
    cells = []
    for key in CORPORA:
        cell = baseline[key]
        cells.append(f"{key} {cell['hits']}/{cell['n']} P={cell['precision']:.4f} "
                     f"R={cell['recall']:.4f} 命中对最小分差={cell['margin']:.4f}(#{cell['index']})")
    print("  基线（未扰动）  " + " | ".join(cells))
    label, owner, index = summary["objective_where"]
    print(f"  88 格主目标（最恶劣命中对分差）= {summary['objective']:.4f}  在 {label} / {owner} / #{index}")
    print(f"  违约格 {len(summary['violating'])}/{total}"
          f"   造成命中变化的格 {len(summary['flipped'])}/{total}"
          f"   出现 +inf 的格 {len(summary['infinite'])}/{total}")
    for key in CORPORA:
        lost = _tally_text(summary["loss_tally"][key], total)
        gained = _tally_text(summary["gain_tally"][key], total)
        if lost != "无" or gained != "无":
            print(f"    {key:<7} 掉过的对 {lost}   捡到的对 {gained}")
    if summary["violating"]:
        reasons = Counter(reason
                          for record in summary["violating"]
                          for reason in record["violations"])
        print("    违约原因分布：" + "；".join(f"{reason} x{c}" for reason, c in reasons.most_common()))
        print("    违约格清单（前 12）：" + ", ".join(
            f"{record['label']}[{'; '.join(record['violations'])}]"
            for record in summary["violating"][:12])
            + ("..." if len(summary["violating"]) > 12 else ""))
    ranked = sorted((record for record in summary["records"] if not record["violations"]),
                    key=lambda record: record["margin"])[:5]
    print("    最恶劣前五格（仅无违约格）：" + ", ".join(
        f"{record['label']}={record['margin']:.4f}({record['owner']} #{record['index']})"
        for record in ranked))


def decide(name: str, rows: list[tuple[float, dict]], live: float) -> None:
    """机械地把判据套到扫描结果上。这一段的每一行都能由上面的表格逐字核对。"""
    limits = hard_constraints()
    print("=" * 132)
    print("决策（判据机械套用；「存活」= 三条硬约束在全部 88 格上逐格通过）")
    print("=" * 132)
    print(f"{'基值':<12}{'基线 v2 命中':>12}{'主目标':>10}{'相对现状':>12}"
          f"{'违约格':>8}{'命中变化格':>12}   判定")
    print("-" * 132)
    status = next(summary for value, summary in rows if value == live)
    for value, summary in rows:
        ratio = (summary["objective"] / status["objective"]
                 if status["objective"] else float("inf"))
        alive = not summary["violating"]
        verdict = "存活" if alive else f"淘汰（{len(summary['violating'])} 格违约）"
        if value == live:
            verdict += " <- 现状"
        print(f"{value:<12.4g}{summary['baseline']['v2']['hits']:>12}"
              f"{summary['objective']:>10.4f}{ratio:>11.1f}x"
              f"{len(summary['violating']):>8}{len(summary['flipped']):>12}   {verdict}")
    print("-" * 132)
    survivors = [(value, summary) for value, summary in rows if not summary["violating"]]
    print(f"  硬约束门槛（逐格检查，不只查基线）：C1 golden=={limits['golden']}、"
          f"C2 v1=={limits['v1']}、C3 v2>={limits['v2']}")
    print(f"  存活候选：{[f'{value:g}' for value, _ in survivors] or '无'}")
    if survivors:
        best_value, best = max(survivors, key=item_objective)
        print(f"  存活候选中主目标最大者：{best_value:g}（{best['objective']:.4f}）；"
              f"现状 {live:g}（{status['objective']:.4f}）")
    # 诱惑清单：命中涨了、分差没改善。判据要求这次诱惑与这次拒绝都如实报出来。
    print()
    print("  诱惑清单（命中数或 P/R 变好、但主目标没有改善的候选）——判据禁止拿它们当采纳理由：")
    temptations = []
    for value, summary in rows:
        if value == live:
            continue
        better_hits = any(summary["baseline"][key]["hits"] > status["baseline"][key]["hits"]
                          for key in CORPORA)
        fewer_flips = len(summary["flipped"]) < len(status["flipped"])
        better_pr = (summary["baseline"]["v2"]["precision"] > status["baseline"]["v2"]["precision"]
                     or summary["baseline"]["v2"]["recall"] > status["baseline"]["v2"]["recall"])
        improved = summary["objective"] > status["objective"]
        if (better_hits or fewer_flips or better_pr) and not improved:
            temptations.append((value, better_hits, fewer_flips, better_pr, summary))
    if not temptations:
        print("    无（没有任何候选在约束侧变好而主目标不变好）")
    for value, better_hits, fewer_flips, better_pr, summary in temptations:
        why = [label for flag, label in ((better_hits, "三集命中数有涨"),
                                        (fewer_flips, "造成命中变化的格数更少"),
                                        (better_pr, "v2 宏平均 P/R 更好看")) if flag]
        print(f"    {name}={value:g}：{'、'.join(why)}，但主目标 "
              f"{summary['objective']:.4f} <= 现状 {status['objective']:.4f}"
              f"，且违约 {len(summary['violating'])} 格 —— 按判据拒绝")

    # 主筛子对全体判负时（含现状），筛子本身就失去了区分力，必须自报
    total = len(status["records"])
    print()
    if status["violating"]:
        shallow = depth(status)
        print(f"  自报判据缺陷之一：现状值 {live:g} 自己在逐格硬约束下也不存活"
              f"（{len(status['violating'])}/{total} 格违约，最浅缺口 {shallow}）。")
        if not survivors:
            print("    本轮所有候选值一律判负，「存活」这个筛子失去区分力：它只能当比较量用"
                  "（比违约格数、违约深度与波及面），")
            print("    不能当通过/淘汰用。也就是说，逐格零回归在本轮扫描到的取值范围内不可达"
                  "——注意这个结论的范围仅限本轮候选表，")
            print("    不能推广成「对本架构不可达」：候选表是预登记的，边界外的取值本轮没扫。")
        else:
            alive = ", ".join(f"{value:g}" for value, _s in survivors)
            print(f"    但存活候选（{alive}）说明逐格零回归**是可达的**，只是现状值不在那个"
                  "区域里；此时筛子仍有区分力，")
            print("    判据照常适用，缺陷只剩下面这一条。")
        print("    本轮不据此改判据——改在看见结果之后，就是照着结果倒推。若下一轮要"
              "据此调权重，")
        print("    必须先重新登记判据（把违约格数与深度提为主目标或次级目标），再跑扫描。")
        print()
        print("  次级比较（信息量，不构成采纳理由）：")
        print(f"    {'基值':<10}{'违约格':>8}{'最浅缺口':>10}{'波及对数':>10}{'主目标':>10}")
        for value, summary in rows:
            print(f"    {value:<10.4g}{len(summary['violating']):>8}{depth(summary):>10}"
                  f"{distinct_lost_pairs(summary):>10}{summary['objective']:>10.4f}")

    print()
    objectives = [summary["objective"] for _value, summary in rows]
    owners = Counter(f"{summary['objective_where'][1]} #{summary['objective_where'][2]}"
                     for _value, summary in rows)
    print("  自报判据缺陷之二：主目标对约束侧的改善不敏感。本轮 "
          f"{len(rows)} 个候选值的主目标全落在 {min(objectives):.4f}-{max(objectives):.4f}")
    print(f"    这个窄带里（最恶劣格的归属分布：{dict(owners.most_common())}），"
          f"而同期违约格数从 {min(len(s['violating']) for _v, s in rows)} 变到 "
          f"{max(len(s['violating']) for _v, s in rows)}。")
    print("    原因是主目标量的是「一个已判对的结论离被推翻有多远」，它量不到「有多少格根本"
          "判错了」；后者落在约束侧。")
    print("    所以一个能把命中翻转清零的候选值，在主目标上可以纹丝不动。两个口径都要看，"
          "只看一个会得出反直觉的结论。")
    print("    这一条同样不在本轮改：判据是先登记的那一份，改它就是照着结果倒推。")
    print()
    print("  结论（判据机械推出，不是手写）：")
    if not survivors:
        print(f"    没有任何候选值在全部 {total} 格上通过三条硬约束（现状值自己也没通过），")
        print(f"    按判据「若不存在 -> 保持现状值不动」：{name} 保持 {live:g}，负面结果写进文档。")
    else:
        best_value, best = max(survivors, key=item_objective)
        if best["objective"] <= status["objective"]:
            print(f"    唯一/最优存活候选 {best_value:g} 的主目标 {best['objective']:.4f} "
                  f"<= 现状 {status['objective']:.4f}，未改善，")
            print(f"    按判据「显著改善才采纳」：{name} 保持 {live:g}。"
                  f"该存活候选在约束侧的优势已列入诱惑清单并拒绝。")
        else:
            print(f"    存活候选 {best_value:g} 主目标 {best['objective']:.4f} > "
                  f"现状 {status['objective']:.4f}（{best['objective'] / status['objective']:.1f}x），")
            print("    判据只写了「显著改善」而没给倍数门槛——这是判据的第二个缺陷。"
                  "本轮不临时补门槛，")
            print("    如实把倍数报出来，由复核者判断；不在看见结果之后才定义什么叫显著。")


def item_objective(item: tuple[float, dict]) -> float:
    return item[1]["objective"]


def depth(summary: dict) -> int:
    """违约深度 = 违约格里「三集命中数缺口之和」的最小值；零违约返回 0。

    「违约格数」只说坏了几格，不说坏得多深。同样是 9 格违约，掉到 23 与掉到 20 是
    两件差很远的事。缺口 = 门槛值 - 实测命中数，逐集取正部再求和，越小越浅。
    """
    limits = hard_constraints()
    gaps = [sum(max(0, limits[name] - record["hits"][name]) for name in CORPORA)
            for record in summary["violating"]]
    return min(gaps) if gaps else 0


def distinct_lost_pairs(summary: dict) -> int:
    """掉过的对（跨三集去重计数）：违约格数相同时，波及面越窄越好。"""
    return sum(len(tally) for tally in summary["loss_tally"].values())


def sweep(which: str) -> None:
    name, values = CANDIDATES[which]
    problems = check_candidates_are_anchored()
    if problems:
        raise SystemExit("锚定校验未过，扫描没有参照点，拒跑：" + "; ".join(problems))
    live = getattr(mr, name)
    kept = ", ".join(f"{w}={getattr(mr, w):g}" for w in untouched_weights(name))
    limits = hard_constraints()
    total = wg.grid_sizes()["total"]
    print("=" * 132)
    print(f"N10-2 扫描：{name} ∈ {[f'{v:g}' for v in values]}（一次只动这一个变量，"
          f"本轮不动 {kept}）")
    print("=" * 132)
    print("判据（先写后跑，全文见 criteria 模式）：主目标 = min over 88 格 of min over 三集 of")
    print("命中对最小分差；硬约束 C1/C2/C3 在全部 88 格上逐格检查，不只在基线权重下检查。")
    print(f"门槛值运行时现读：C1 golden=={limits['golden']}、C2 v1=={limits['v1']}、"
          f"C3 v2>={limits['v2']}；网格 {total} 格。")
    print()
    rows: list[tuple[float, dict]] = []
    for value in values:
        summary = worst_over_grid((name, value))
        rows.append((value, summary))
        print_candidate(name, value, summary, live)
    print()
    decide(name, rows, live)


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
