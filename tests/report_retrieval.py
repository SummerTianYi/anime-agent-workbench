"""Retrieval analysis harness: v2 detail, per-layer ablation, weight sensitivity.

固化在 tests/ 下而不是 evidence/ 下的原因：本轮不许动 evidence/（阶段三统一重写，
数字还在变），而这三组分析必须可被 QA 独立复跑——脚本本身就是可审计的痕迹，报告
里的每个数字都应该能由 `./.venv/bin/python tests/report_retrieval.py <mode>` 重现。

三个模式：
  v2          逐对命中明细 + 宏平均 P/R + 按 D1-D11 分组的失败分布
  ablation    逐层消融：kill L1-L5 各自在 golden + v1 + v2 上的命中数与判定翻转
  sensitivity 权重敏感性：单权重扰动 + 全组合网格，找实测最恶劣方向

三个模式共用同一套评测口径（从 tests/test_holdout_v2.py import），所以「口径」只有
一处定义；分析脚本自己另写一份口径就等于制造第二处会漂移的真相。
"""
from __future__ import annotations

import sys
from collections import Counter, defaultdict
from pathlib import Path
from unittest import mock

TESTS = Path(__file__).resolve().parent
REPO = TESTS.parent
for _path in (str(REPO), str(TESTS)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from src import memory_ranker as mr  # noqa: E402
from holdout_v2 import HOLDOUT_V2  # noqa: E402
from test_memory_retrieval import HOLDOUT_GOLDEN  # noqa: E402
from test_holdout_v2 import score_holdout_v2  # noqa: E402
from acceptance.gates.g1_memory import GOLDEN  # noqa: E402

# 三个评测集。名字固定，报告与断言都按这三个名字引用。
CORPORA = {"golden": GOLDEN, "v1": HOLDOUT_GOLDEN, "v2": HOLDOUT_V2}

WEIGHTS = ("W_BIGRAM", "W_CONCEPT", "W_PREFERENCE", "W_TRANSIENT")


def _hits(corpus: list[dict], ranker=mr.rank) -> list[bool]:
    """Per-pair top-1 hit flags; pairs with empty `relevant` are marked False.

    命中数口径与 score_holdout_v2 的 recall 侧一致：relevant 为空的对没有正确
    答案，不计入「命中」，但保留在列表里以维持与语料的逐对对齐（消融要看的是
    「哪一对翻转了」，对齐比长度更重要）。
    """
    flags: list[bool] = []
    for pair in corpus:
        stored = [_text(fact) for fact in pair["stored"]]
        relevant = {_text(fact) for fact in pair["relevant"]}
        if not stored or not relevant:
            flags.append(False)
            continue
        flags.append(ranker(_text(pair["query"]), stored)[0][0] in relevant)
    return flags


def _text(value: object) -> str:
    """None -> "" and everything else -> str (same semantics as mr._as_text).

    在分析层自己实现而不 import mr._as_text：评测层不该依赖实现层的私有符号，
    否则实现重构会静默改变分析口径（与 test_holdout_v2.py 里的同名函数同理）。
    """
    return "" if value is None else str(value)


def _min_margin(corpus: list[dict], ranker=mr.rank, hits_only: bool = False) -> tuple[float, int, int]:
    """Smallest (top1 - top2) gap -> (margin, owner index, excluded count).

    口径（必须写死，否则数字不可比）：只在**可判定且非退化**的对上取最小分差。
    排除两类：① stored < 2（没有 top2 可言）；② query 归一化后为空或 relevant
    为空——前者四层全为 0，分差恒为 0，后者没有正确答案。不排除的话 v2 的最小
    分差会被 #31（query 是纯标点，归一化后为空）钉在 0.0000，那个 0 不反映任何
    结构鲁棒性，只反映“这对本来就不该返回东西”（本机实测踩过）。

    hits_only=True 时再排除已经**未命中**的对。这是两个不同的量，必须分开：
    全体最小分差量的是「哪对最接近随机」（v2 上它恒由 D7 那几对贡献，因为它们
    L3/L4 全为 0、只剩微弱的 L2 信号）；而**命中对的最小分差**才量「一个已正确的
    判定离翻转有多远」，后者才是权重鲁棒性的含义（审查发现 M15 关心的是这个）。
    """
    best, best_index, excluded = float("inf"), -1, 0
    for index, pair in enumerate(corpus):
        stored = [_text(fact) for fact in pair["stored"]]
        relevant = {_text(fact) for fact in pair["relevant"]}
        query = _text(pair["query"])
        if len(stored) < 2 or not relevant or not mr.normalize(query):
            excluded += 1
            continue
        ranked = ranker(query, stored)
        if hits_only and ranked[0][0] not in relevant:
            excluded += 1
            continue
        gap = ranked[0][1] - ranked[1][1]
        if gap < best:
            best, best_index = gap, index
    return best, best_index, excluded


# ---------------------------------------------------------------------------
# v2 detail
# ---------------------------------------------------------------------------
def report_v2() -> None:
    result = score_holdout_v2(HOLDOUT_V2)
    rows = result["rows"]
    print("=" * 100)
    print("HOLDOUT v2 — 逐对命中明细（top-1，口径见 tests/test_holdout_v2.py docstring）")
    print("=" * 100)
    print(f"{'#':>3} {'dim':<5} {'shape':<14} {'P':>5} {'R':>5} {'hit':>4}  query -> retrieved")
    print("-" * 100)
    for row in rows:
        precision = "skip" if row["precision"] is None else f"{row['precision']:.2f}"
        recall = "skip" if row["recall"] is None else f"{row['recall']:.2f}"
        mark = "HIT" if row["hit"] else ("--" if row["relevant"] else "n/a")
        print(f"{row['index']:>3} {row['dim']:<5} {row['shape']:<14} {precision:>5} {recall:>5} {mark:>4}"
              f"  {row['query'][:16]} -> {row['retrieved'][:34]}")
    print("-" * 100)
    print(f"宏平均 precision = {result['precision']:.4f}  (n={result['precision_n']})")
    print(f"宏平均 recall    = {result['recall']:.4f}  (n={result['recall_n']})")

    print()
    print("=" * 100)
    print("按 D1-D11 分组的失败分布")
    print("=" * 100)
    print(f"{'dim':<5} {'pairs':>5} {'hits':>5} {'miss':>5} {'hit-rate':>9}  失败对编号")
    print("-" * 100)
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[row["dim"]].append(row)
    for dim in sorted(grouped, key=lambda tag: int(tag[1:])):
        group = grouped[dim]
        judgeable = [row for row in group if row["relevant"]]
        hits = sum(1 for row in judgeable if row["hit"])
        misses = [row["index"] for row in judgeable if not row["hit"]]
        rate = f"{hits / len(judgeable):.3f}" if judgeable else "n/a"
        print(f"{dim:<5} {len(group):>5} {hits:>5} {len(misses):>5} {rate:>9}  {misses}")
    print("-" * 100)
    judgeable_all = [row for row in rows if row["relevant"]]
    print(f"可判定对（relevant 非空）= {len(judgeable_all)}，命中 = "
          f"{sum(1 for row in judgeable_all if row['hit'])}，未命中 = "
          f"{sum(1 for row in judgeable_all if not row['hit'])}")

    print()
    print("未命中对的 top-1 与正确答案对照（诊断用）：")
    for row in judgeable_all:
        if row["hit"]:
            continue
        answers = " | ".join(answer[:40] for answer in row["relevant"])
        print(f"  #{row['index']:>2} [{row['dim']}] {row['query']}")
        print(f"        取到: {row['retrieved']}  ({row['top1_score']:.4f})")
        print(f"        应答: {answers}")
        if row["runner_up"]:
            print(f"        次位: {row['runner_up']}  ({row['top2_score']:.4f})"
                  f"  分差={row['top1_score'] - row['top2_score']:.4f}")


# ---------------------------------------------------------------------------
# per-layer ablation
# ---------------------------------------------------------------------------
# kill 的目标是**层的输出**而不是权重：把权重置零等价于该层输出恒 0（线性组合），
# 但层1 例外——normalize 是层2-层5 共享的前置，kill 它必须换成 identity 函数，
# 没有任何权重组合能表达「不归一化」。
#
# 标签用「层1..层5」而不是「L1..L5」：审查发现编号里已经有 L1（scope 谓词）、
# L2（入参校验）、L4（casefold 与标点剥离），两套 L 编号同时出现在一张表里会把
# 「打分器的第四层」与「缺陷 L4」混为一谈（它们恰好都涉 normalize，更容易误读）。
_LAYERS = (
    ("层1 normalize", "normalize", lambda text: text),
    ("层2 bigram", "_bigram_profile", lambda a, b: 0.0),
    ("层3 concept", "_concept_profile", lambda ctx, prof: 0.0),
    ("层4 preference", "_preference_profile", lambda ctx, prof: 0.0),
    ("层5 transient", "_transient_profile", lambda ctx, prof: 0.0),
)


def report_ablation() -> None:
    print("=" * 100)
    print("逐层消融：kill 各层后在 golden / v1 / v2 三集上的命中数与判定翻转")
    print("（层1-层5 = 打分器的五个层；与审查发现编号 L1/L2/L4 无关，两套编号不要混读）")
    print("=" * 100)
    baseline = {name: _hits(corpus) for name, corpus in CORPORA.items()}
    print(f"{'layer':<16} " + " ".join(f"{name:>26}" for name in CORPORA))
    print(f"{'':<16} " + " ".join(f"{'hits  flips  margin':>26}" for _ in CORPORA))
    print("-" * 100)
    for name, corpus in CORPORA.items():
        base_margin, _, excluded = _min_margin(corpus)
        base_hits = sum(baseline[name])
        print(f"{'BASELINE ' + name:<16} {base_hits:>3}/{len(corpus):<3} "
              f"{'-':>6} {base_margin:>10.4f}   (分差口径排除 {excluded} 对)")
    print("-" * 100)
    for label, attr, stub in _LAYERS:
        with mock.patch.object(mr, attr, stub):
            cells = []
            for name, corpus in CORPORA.items():
                killed = _hits(corpus)
                flips = sum(1 for before, after in zip(baseline[name], killed) if before != after)
                gained = sum(1 for b, a in zip(baseline[name], killed) if not b and a)
                lost = sum(1 for b, a in zip(baseline[name], killed) if b and not a)
                margin, _, _ = _min_margin(corpus)
                cells.append(f"{sum(killed):>3}/{len(corpus):<3} {flips:>3}({gained}+/{lost}-) {margin:>8.4f}")
        print(f"{label:<16} " + " ".join(f"{cell:>26}" for cell in cells))
    print("-" * 100)
    print("flips 列格式：翻转总数(转对+/转错-)。零翻转 = 该层在这三个集上无判定力。")
    print("注意区分两个不同的量：**判定力**（flips）与**分差贡献**（margin 降幅）。")
    print("一层可以零翻转却大幅拉开分差（鲁棒性贡献），也可以翻转很多而分差不变。")


# ---------------------------------------------------------------------------
# weight sensitivity
# ---------------------------------------------------------------------------
def _perturbed(factor_map: dict[str, float]):
    """Context manager that scales module weights by the given factors."""
    patches = [
        mock.patch.object(mr, name, getattr(mr, name) * factor)
        for name, factor in factor_map.items()
    ]
    for patch in patches:
        patch.start()
    return patches


def _stop(patches) -> None:
    for patch in patches:
        patch.stop()


def report_sensitivity() -> None:
    import itertools

    print("=" * 118)
    print("权重敏感性：单权重扰动 + 全体缩放 + 结构性组合网格（×0.5 / ×1 / ×2），三集")
    print("=" * 118)
    base = {name: sum(_hits(corpus)) for name, corpus in CORPORA.items()}
    print("BASELINE（不计入扰动，审查发现 M16 的计数口径）：")
    for name, corpus in CORPORA.items():
        all_m, _, all_x = _min_margin(corpus)
        hit_m, hit_i, hit_x = _min_margin(corpus, hits_only=True)
        print(f"  {name:<7} hits={base[name]:>3}/{len(corpus):<3}"
              f"  min_margin(全体)={all_m:.4f}(排除{all_x})"
              f"  min_margin(仅命中对)={hit_m:.4f}(排除{hit_x}, 在#{hit_i})")
    print()
    print("两个分差口径分开报的原因：全体最小分差量「哪对最接近随机」，仅命中对的最小")
    print("分差才量「一个已正确的判定离翻转有多远」——后者才是权重鲁棒性的含义。")
    print()

    singles: list[tuple[str, dict[str, float]]] = []
    for name in WEIGHTS:
        for factor in (0.5, 2.0):
            singles.append((f"{name} x{factor}", {name: factor}))

    uniform: list[tuple[str, dict[str, float]]] = []
    grid: list[tuple[str, dict[str, float]]] = []
    for factors in itertools.product((0.5, 1.0, 2.0), repeat=len(WEIGHTS)):
        if all(factor == 1.0 for factor in factors):
            continue                      # 基线不算扰动（M16）
        label = " ".join(f"{short}x{factor:g}" for short, factor in zip(
            ("BIG", "CON", "PRE", "TRA"), factors))
        target = uniform if len(set(factors)) == 1 else grid
        target.append((label, dict(zip(WEIGHTS, factors))))

    def run(title, configs, show_all=True):
        print("=" * 118)
        print(f"{title}（{len(configs)} 个）")
        print("=" * 118)
        if show_all:
            print(f"{'config':<34} " + " ".join(f"{name:>10}" for name in CORPORA)
                  + f" {'min_margin(仅命中对)':>34}")
            print("-" * 118)
        records = []
        for label, factor_map in configs:
            patches = _perturbed(factor_map)
            try:
                cells, hit_margins, all_margins = [], [], []
                for name, corpus in CORPORA.items():
                    hits = sum(_hits(corpus))
                    all_m, _, _ = _min_margin(corpus)
                    hit_m, hit_i, _ = _min_margin(corpus, hits_only=True)
                    cells.append(f"{hits:>3}/{len(corpus):<3}{'*' if hits != base[name] else ' '}")
                    all_margins.append((all_m, name, -1))
                    hit_margins.append((hit_m, name, hit_i))
            finally:
                _stop(patches)
            worst_hit = min(hit_margins)
            worst_all = min(all_margins)
            records.append((label, worst_hit[0], worst_hit[1], worst_hit[2], cells,
                            worst_all[0], worst_all[1]))
            if show_all:
                print(f"{label:<34} " + " ".join(f"{cell:>10}" for cell in cells)
                      + f" {worst_hit[0]:>12.4f} ({worst_hit[1]} #{worst_hit[2]})"
                      + f" {worst_all[0]:>12.4f} ({worst_all[1]})")
        print("-" * 118)
        worst = min(records, key=lambda record: record[1])
        print(f"实测最恶劣方向（仅命中对分差）: {worst[0]}"
              f"  min_margin={worst[1]:.4f}  在 {worst[2]} 第 {worst[3]} 对")
        flipped = [record for record in records if "*" in "".join(record[4])]
        print(f"造成命中数变化的配置: {len(flipped)}/{len(records)}"
              f"{'（无任何配置改变判定）' if not flipped else ''}")
        for record in flipped[:15]:
            print(f"    {record[0]:<34} " + " ".join(f"{cell:>10}" for cell in record[4])
                  + f"  仅命中对分差={record[1]:.4f}")
        top = sorted(records, key=lambda record: record[1])[:5]
        print("最恶劣前 5（按仅命中对分差升序）：")
        for record in top:
            print(f"    {record[0]:<34} margin={record[1]:.4f} ({record[2]} #{record[3]})"
                  f"   全体口径={record[5]:.4f} ({record[6]})")
        print()
        return records

    run("单权重扰动", singles)
    # 全体缩放单独报：四个权重乘同一个因子会把**所有**分数同比缩放，分差也跟着
    # 同比缩放，这是算术恒等式而不是结构信息。把它混在网格里当「最恶劣方向」报是
    # 测量缺陷（本机实测踩过：未分类时榜首恒为 BIGx0.5 CONx0.5 PREx0.5 TRAx0.5，
    # 它只是“把所有分差除以 2”，与哪个权重重要无关）。
    run("全体缩放（非结构性，分差同比缩放是算术必然）", uniform)
    run("结构性组合网格（相对权重变化，排除全体缩放）", grid)


# ---------------------------------------------------------------------------
# per-pair layered attribution
# ---------------------------------------------------------------------------
# 根因归因不许靠读代码猜：把每条未命中对的四层**加权后**贡献逐项打出来，谁把
# 干扰项抬上去的、谁没给正确答案该有的分，在数字上直接可见。QA 复跑同一个
# mode 就能核对报告里的每一句根因结论。
def report_diagnose() -> None:
    print("=" * 100)
    print("分层贡献归因：未命中对的 top-1 干扰项 vs 正确答案，四层加权贡献逐项对照")
    print("=" * 100)
    result = score_holdout_v2(HOLDOUT_V2)
    for row in result["rows"]:
        if not row["relevant"] or row["hit"]:
            continue
        pair = HOLDOUT_V2[row["index"]]
        stored = [_text(fact) for fact in pair["stored"]]
        query = row["query"]
        context = mr._query_context(query)
        answers = set(row["relevant"])
        print(f"\n#{row['index']:>2} [{row['dim']}{'+' + '+'.join(row['dim2']) if row['dim2'] else ''}]"
              f" query = {query}")
        print(f"     query 侧: stable={context.stable} polarity={context.polarity}"
              f" concept_hits={dict(zip(mr.CONCEPT_LEXICON, context.concept_hits)) or '{}'}")
        # 干扰项 = 实际取到的那条；正确答案 = 标注 relevant 里分数最高的一条
        #（多 relevant 时取最能代表「本该赢」的那条，避免挑软柿子）。
        picks = [row["retrieved"]] + sorted(
            (fact for fact in stored if fact in answers and fact != row["retrieved"]),
            key=lambda fact: -mr.score(query, fact),
        )
        for fact in picks[:2]:
            tag = "干扰" if fact == row["retrieved"] else "应答"
            profile = mr._profile(fact)
            l2 = mr.W_BIGRAM * mr._bigram_profile(context.profile, profile)
            l3 = mr.W_CONCEPT * mr._concept_profile(context, profile)
            l4 = mr.W_PREFERENCE * mr._preference_profile(context, profile)
            l5 = -mr.W_TRANSIENT * mr._transient_profile(context, profile)
            print(f"     [{tag}] total={l2 + l3 + l4 + l5:+.4f}"
                  f"  L2={l2:+.4f} L3={l3:+.4f} L4={l4:+.4f} L5={l5:+.4f}"
                  f"  |norm|={len(profile.normalized)}")
            print(f"            {fact}")
            print(f"            normalized: {profile.normalized}")
            for name, concept in mr.CONCEPT_LEXICON.items():
                fh = mr._concept_hits(profile.normalized, concept)
                qh = dict(zip(mr.CONCEPT_LEXICON, context.concept_hits))[name]
                if fh or qh:
                    words = mr._masked_scan(profile.normalized, (*concept.head, *concept.member))
                    kind = "head自匹配" if all(w in concept.head for w in words) else (
                        "member实例" if all(w in concept.member for w in words) else "混合")
                    print(f"            概念类[{name}] qh={qh} fh={fh} 命中词={words} -> {kind}")
    print()
    print("=" * 100)
    print("L2 长度稀释量化：同一 query 下，答案长度与 L2 得分的关系（cosine 的固有性质）")
    print("=" * 100)
    print(f"{'#':>3} {'len(干扰)':>9} {'L2(干扰)':>9} {'len(应答)':>9} {'L2(应答)':>9} {'比值':>7}")
    for row in result["rows"]:
        if not row["relevant"] or row["hit"]:
            continue
        query = row["query"]
        context = mr._query_context(query)
        best = max(row["relevant"], key=lambda fact: mr.score(query, fact))
        wrong = mr._profile(row["retrieved"])
        right = mr._profile(best)
        lw = mr._bigram_profile(context.profile, wrong)
        lr = mr._bigram_profile(context.profile, right)
        ratio = f"{lr / lw:.3f}" if lw else "n/a"
        print(f"{row['index']:>3} {len(wrong.normalized):>9} {lw:>9.4f}"
              f" {len(right.normalized):>9} {lr:>9.4f} {ratio:>7}")


MODES = {
    "v2": report_v2,
    "diagnose": report_diagnose,
    "ablation": report_ablation,
    "sensitivity": report_sensitivity,
}

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "v2"
    if mode not in MODES:
        raise SystemExit(f"unknown mode {mode!r}; choose from {sorted(MODES)}")
    MODES[mode]()
