"""Retrieval analysis harness: v2 detail, per-layer ablation, weight sensitivity.

固化在 tests/ 下而不是 evidence/ 下的原因：本轮不许动 evidence/（阶段三统一重写，
数字还在变），而这三组分析必须可被 QA 独立复跑——脚本本身就是可审计的痕迹，报告
里的每个数字都应该能由 `./.venv/bin/python tests/report_retrieval.py <mode>` 重现。

五个模式：
  v2          逐对命中明细 + 宏平均 P/R + 按 D1-D11 分组的失败分布
  ablation    逐层消融：kill L1-L5 各自在 golden + v1 + v2 上的命中数与判定翻转
  sensitivity 权重敏感性：单权重扰动 + 全组合网格，找实测最恶劣方向
  lexicon     词典审计对照表：按规则新增的词 × 恰好落在 v2 里的词 × 仍未覆盖
              的对，外加「刻意不收的词若收进来会翻转几对」的反事实
  l2          RC-2 长度稀释的判定依据：四种 L2 归一化口径 × 三集，逐对 L2 比值，
              外加 W_BIGRAM 从 0 扫到 3 倍——bigram_similarity 的 docstring 引的
              每个数字都出自本模式

五个模式共用同一套评测口径（从 tests/test_holdout_v2.py import），所以「口径」只有
一处定义；分析脚本自己另写一份口径就等于制造第二处会漂移的真相。
"""
from __future__ import annotations

import math
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
                  + f" {'min_margin(仅命中对)':>40}")
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


# ---------------------------------------------------------------------------
# lexicon audit
# ---------------------------------------------------------------------------
# 扩词前那份词典的 member 逐字转录。来源是 src/memory_ranker.py 在扩词提交之前
# 的 git blob（sha1 938baf5a48ee1cf814ba2fdb6d516928b7a89c5a，可用
# `git cat-file -p <该 blob>` 复核），转录后由下面第一条自检断言钉住：八类合计
# 必须是 88 个词，且每一个都仍然是现行词典的成员（本轮只增不删）。
PRE_EXPANSION_MEMBERS = {
    "颜色": ("红", "橙", "黄", "绿", "青", "蓝", "紫", "黑", "白", "灰", "粉", "棕", "金", "银"),
    "城市": ("北京", "上海", "广州", "深圳", "杭州", "南京", "成都", "武汉", "西安",
             "苏州", "天津", "重庆", "家乡", "籍贯"),
    "称呼": ("叫", "昵称", "老板", "老师", "先生", "女士", "小姐", "同学"),
    "生日": ("月", "日", "号", "年龄", "岁", "星座"),
    "宠物": ("猫", "狗", "兔子", "仓鼠", "鹦鹉", "乌龟", "金鱼", "蜥蜴", "养"),
    "过敏": ("花粉", "海鲜", "芒果", "尘螨", "敏感", "忌口", "乳糖", "酒精", "药物"),
    "职业": ("上班", "公司", "工程师", "程序员", "老师", "教师", "医生", "护士",
             "设计师", "会计", "律师", "司机", "职员"),
    "爱好": ("喜欢", "热爱", "徒步", "登山", "跑步", "游泳", "骑车", "唱歌", "画画",
             "读书", "旅游", "摄影", "钓鱼", "健身", "运动"),
}

# 刻意不收的词，与不收它的理由。理由原文在 src/memory_lexicon.py 各类的
# 「刻意不收」注释里；这里再列一遍是为了跑反事实：把它们单独塞回词典，看能翻转
# 几对。这个数字就是「不许照失败条目补词」这条纪律的真实代价，必须如实报出。
DELIBERATE_EXCLUSIONS = (
    ("职业", ("大厨",), "口语职业别称这条规则是看到某一对失败才想到的，属事后归纳"),
    ("爱好", ("体育馆",), "场地名词是活动的周边物而不是活动名"),
    ("爱好", ("相机",), "器材名词同上；且该对已被点名超出词表方案的能力边界"),
    ("爱好", ("拍鸟",), "特定圈子的说法，不是常见休闲活动清单里的标准条目"),
    ("生日", ("本命年",), "生肖纪年与生日是两个不同槽位，收它等于新增一个类去追一对样例"),
    ("生日", ("属相",), "同上"),
    ("过敏", ("哮喘",), "疾病名需要一个新的疾病类与新的 head，属槽位架构变更而非词表扩充"),
    ("过敏", ("不吃",), "L4 拥有否定极性、L3 拥有概念实例，两层不许争同一条证据"),
    # 下面两条是「组合探针」：单独加任一个都不翻转，因为 L3 要求双侧都命中同一个类。
    # 把它们列进来是为了量化「两条排除合起来的价签」，而不是暗示它们应该被收。
    ("生日", ("多大", "本命年"), "疑问形式不入表 + 生肖纪年不入表：两条排除必须同时撤销才可能翻转"),
    ("城市", ("黄土高原",), "能力边界探针：黄土高原是高原不是城市，收它等于把地理常识硬编码进槽位"),
)


def _lexicon_with(class_name: str, extra: tuple[str, ...]):
    """Return a copy of the live lexicon with `extra` appended to one class."""
    from types import MappingProxyType

    patched = {}
    for key, concept in mr.CONCEPT_LEXICON.items():
        patched[key] = (
            mr.ConceptClass(name=concept.name, head=concept.head,
                            member=(*concept.member, *extra))
            if key == class_name else concept
        )
    return MappingProxyType(patched)


def report_lexicon() -> None:
    v2_blob = mr.normalize("\n".join(
        [_text(p["query"]) for p in HOLDOUT_V2]
        + [_text(f) for p in HOLDOUT_V2 for f in p["stored"]]
        + [_text(f) for p in HOLDOUT_V2 for f in p["relevant"]]
    ))

    print("=" * 108)
    print("词典审计对照表 —— 按规则新增的词 × 恰好落在 v2 里的词 × v2 仍未覆盖的对")
    print("=" * 108)

    total_old = sum(len(v) for v in PRE_EXPANSION_MEMBERS.values())
    assert total_old == 88, f"转录的扩词前词典不是 88 个成员：{total_old}"
    live = mr.CONCEPT_LEXICON
    for name, old in PRE_EXPANSION_MEMBERS.items():
        missing = [w for w in old if w not in live[name].member]
        assert not missing, f"{name} 丢失了扩词前的成员（本轮只增不删）：{missing}"
    print(f"扩词前 88 个成员全部保留（只增不删），来源 blob sha1 938baf5a…；现行合计 "
          f"{sum(len(c.member) for c in live.values())} 个\n")

    print("-" * 108)
    print(f"{'类':<6}{'旧':>5}{'新':>6}{'新增':>6}{'删除':>6}{'新增∩v2':>9}{'占比':>8}  新增里落在 v2 的词")
    print("-" * 108)
    all_added: list[str] = []
    all_added_in_v2: list[str] = []
    for name, concept in live.items():
        old = PRE_EXPANSION_MEMBERS[name]
        new = concept.member
        added = [w for w in new if w not in old]
        removed = [w for w in old if w not in new]
        hit = [w for w in added if mr.normalize(w) in v2_blob]
        all_added += added
        all_added_in_v2 += hit
        share = f"{len(hit) / len(added):.3f}" if added else "n/a"
        print(f"{name:<6}{len(old):>5}{len(new):>6}{len(added):>6}{len(removed):>6}"
              f"{len(hit):>9}{share:>8}  {' '.join(hit) if hit else '(无)'}")
    print("-" * 108)
    print(f"合计  {total_old:>5}{sum(len(c.member) for c in live.values()):>6}"
          f"{len(all_added):>6}{0:>6}{len(all_added_in_v2):>9}"
          f"{len(all_added_in_v2) / len(all_added):>8.3f}")
    print()
    print("反 Goodhart 判据：新增词里落在 v2 的占比越低，越说明词表是按通用规则生成")
    print("而不是从失败条目倒推。上面这个合计占比就是任务书要的那个数字。")

    # --- 覆盖缺口：查询问到了某个槽位，但正确答案里没有该类任何 member ---
    print()
    print("=" * 108)
    print("v2 里仍然没被覆盖的对（查询触发了某类 head，而 relevant 事实里没有该类任何 member）")
    print("=" * 108)
    print(f"{'#':>3} {'类':<6} query -> relevant")
    print("-" * 108)
    gaps = 0
    for index, pair in enumerate(HOLDOUT_V2):
        relevant = [_text(f) for f in pair["relevant"]]
        if not relevant:
            continue
        query_norm = mr.normalize(_text(pair["query"]))
        rel_norms = [mr.normalize(f) for f in relevant]
        for concept in live.values():
            if not any(head in query_norm for head in concept.head):
                continue
            if any(mr._masked_hits(rel, concept.member) for rel in rel_norms):
                continue
            gaps += 1
            print(f"{index:>3} {concept.name:<6} {_text(pair['query'])} -> {relevant[0]}")
    print("-" * 108)
    print(f"共 {gaps} 处覆盖缺口。本仓禁用分词器，所以「没被覆盖的词」只能报到")
    print("「对 × 类」这个粒度——把缺口定位到具体字符需要词级切分，正是本架构的能力边界。")

    # --- 反事实：把刻意不收的词单独塞回去，看能翻转几对 ---
    print()
    print("=" * 108)
    print("反事实：把每个「刻意不收」的词单独塞回词典，三集各翻转几对")
    print("=" * 108)
    print(f"{'类':<6}{'词':<8}{'在v2':>6}{'golden':>9}{'v1':>7}{'v2':>7}  翻转的 v2 对编号 / 不收它的理由")
    print("-" * 108)
    base = {name: _hits(corpus) for name, corpus in CORPORA.items()}
    base_total = sum(sum(flags) for flags in base.values())
    for class_name, words, reason in DELIBERATE_EXCLUSIONS:
        label = "+".join(words)
        in_v2 = "是" if all(mr.normalize(w) in v2_blob for w in words) else "否"
        with mock.patch.object(mr, "CONCEPT_LEXICON", _lexicon_with(class_name, words)):
            alt = {name: _hits(corpus) for name, corpus in CORPORA.items()}
        flips = {
            name: [i for i, (b, a) in enumerate(zip(base[name], alt[name])) if b != a]
            for name in CORPORA
        }
        delta = sum(sum(f) for f in alt.values()) - base_total
        print(f"{class_name:<6}{label:<8}{in_v2:>6}"
              f"{sum(alt['golden']):>4}/{len(GOLDEN):<4}"
              f"{sum(alt['v1']):>3}/{len(HOLDOUT_GOLDEN):<3}"
              f"{sum(alt['v2']):>3}/{len(HOLDOUT_V2):<3}"
              f"  {flips['v2'] or '无'} (净{delta:+d})  {reason}")
    print("-" * 108)
    print(f"基线（不算扰动）：golden {sum(base['golden'])}/{len(GOLDEN)}、"
          f"v1 {sum(base['v1'])}/{len(HOLDOUT_GOLDEN)}、v2 {sum(base['v2'])}/{len(HOLDOUT_V2)}")
    print("「净」是三个集合计命中数的变化。这一列就是纪律的价签：照失败条目补词能买到")
    print("多少分，以及那些分会不会同时污染 golden 与 v1。")


# ---------------------------------------------------------------------------
# RC-2: L2 normalization variants
# ---------------------------------------------------------------------------
# 四种口径。cosine 是现状；damp 是审查发现 M3 当时驳回的那个改法，这里作为
# 对照组一并实测，把「驳回」从定性判断变成有数字的判断；overlap 与 qcontain
# 是本轮新试的两个**不引入任何新参数**的替代归一化。
#   cosine    dot / (||q|| * ||f||)                      对称归一化
#   overlap   dot / min(||q||, ||f||)                    Szymkiewicz-Simpson 重叠系数
#   qcontain  dot / ||q||                                查询包含度（非对称）
#   damp      cosine * min(len)/max(len)                 余弦再乘长度阻尼
def _dot(left, right) -> int:
    return sum(count * right[gram] for gram, count in left.items())


def _cnorm(counter) -> float:
    return math.sqrt(sum(count * count for count in counter.values()))


def _pick_order(a, b):
    """Replicate _bigram_profile's degradation rule so the variants differ only
    in the denominator."""
    n = 2 if min(len(a.normalized), len(b.normalized)) >= 2 else 1
    return (a.bigrams, b.bigrams) if n == 2 else (a.unigrams, b.unigrams)


def _l2_variant(kind: str):
    def variant(a, b) -> float:
        if not a.normalized or not b.normalized:
            return 0.0
        left, right = _pick_order(a, b)
        if not left or not right:
            return 0.0
        dot = _dot(left, right)
        if dot == 0:
            return 0.0
        if left == right:
            return 1.0
        nl, nr = _cnorm(left), _cnorm(right)
        if kind == "cosine":
            return dot / (nl * nr)
        if kind == "overlap":
            return min(1.0, dot / min(nl, nr))
        if kind == "qcontain":
            return min(1.0, dot / nl)
        if kind == "damp":
            la, lb = len(a.normalized), len(b.normalized)
            return (dot / (nl * nr)) * (min(la, lb) / max(la, lb))
        raise AssertionError(kind)

    return variant


L2_KINDS = ("cosine", "overlap", "qcontain", "damp")


def _fmt(indices: list[int]) -> str:
    """Compact flip list for the wide tables: [] / [21] / [2,3,4,5,10,11]."""
    return "[" + ",".join(str(i) for i in indices) + "]"


def _miss_indices(corpus: list[dict], flags: list[bool]) -> list[int]:
    """Pairs that have a correct answer but did not get it at top-1."""
    return [i for i, (pair, hit) in enumerate(zip(corpus, flags))
            if pair["relevant"] and not hit]


def report_l2() -> None:
    base = {name: _hits(corpus) for name, corpus in CORPORA.items()}

    print("=" * 132)
    print("RC-2 判定依据 一：四种 L2 归一化口径 × 三集")
    print("=" * 132)
    print(f"{'口径':<10}" + "".join(f"{n:>40}" for n in CORPORA))
    print("-" * 132)
    for kind in L2_KINDS:
        patched = mr._bigram_profile if kind == "cosine" else _l2_variant(kind)
        with mock.patch.object(mr, "_bigram_profile", patched):
            hits = {n: _hits(c) for n, c in CORPORA.items()}
            cells = []
            for n in CORPORA:
                flips = [i for i, (b, a) in enumerate(zip(base[n], hits[n])) if b != a]
                gained = [i for i in flips if hits[n][i]]
                lost = [i for i in flips if not hits[n][i]]
                margin = _min_margin(CORPORA[n], hits_only=True)[0]
                cells.append(f"{sum(hits[n])}/{len(CORPORA[n])}"
                             f" +{_fmt(gained)} -{_fmt(lost)} m={margin:.4f}")
        tag = "  <- 现状" if kind == "cosine" else ""
        print(f"{kind:<10}" + "".join(f"{c:>40}" for c in cells) + tag)
    print("-" * 132)
    print("m 是**命中对**的最小分差（M15 的口径）。它塌到 0.0000 意味着「赢的那一对」")
    print("是靠候选顺序撞对的，不是靠结构——这正是 overlap / qcontain 的实测结果。")

    print()
    print("=" * 132)
    print("RC-2 判定依据 二：v2 未命中对在四种口径下的 L2（干扰 / 应答 / 比值）")
    print("=" * 132)
    misses = _miss_indices(HOLDOUT_V2, base["v2"])
    print(f"{'#':>3} {'|干|':>4} {'|应|':>4} " + " ".join(f"{k:>26}" for k in L2_KINDS))
    print("-" * 132)
    tally = {k: [0, 0, 0] for k in L2_KINDS}          # favour / tie / against
    for i in misses:
        pair = HOLDOUT_V2[i]
        query = _text(pair["query"])
        relevant = {_text(f) for f in pair["relevant"]}
        stored = [_text(f) for f in pair["stored"]]
        answer = next(f for f in stored if f in relevant)
        distractor = mr.rank(query, stored)[0][0]
        cells = []
        for kind in L2_KINDS:
            fn = mr._bigram_profile if kind == "cosine" else _l2_variant(kind)
            d = fn(mr._profile(query), mr._profile(distractor))
            a = fn(mr._profile(query), mr._profile(answer))
            ratio = (a / d) if d else float("inf")
            if ratio > 1.0001:
                tally[kind][0] += 1
                mark = ">"
            elif ratio < 0.9999:
                tally[kind][2] += 1
                mark = "<"
            else:
                tally[kind][1] += 1
                mark = "="
            cells.append(f"{d:.4f}/{a:.4f}{mark}{ratio:5.2f}")
        print(f"{i:>3} {len(mr.normalize(distractor)):>4} {len(mr.normalize(answer)):>4} "
              + " ".join(f"{c:>26}" for c in cells))
    print("-" * 132)
    for kind in L2_KINDS:
        f, t, a = tally[kind]
        print(f"  {kind:<9} L2 站应答一边 {f} 对 / 弃权 {t} 对 / 仍偏干扰 {a} 对")
    print("比值=1.00 表示 L2 弃权：长度偏置被消掉了，但胜负被推给 L3，而 L3 是对称")
    print("桥接——任何给出同槽位具体值的干扰项一样能桥到查询的槽位上。")

    print()
    print("=" * 132)
    print("RC-2 判定依据 三：把 L2 整层的权重从 0 扫到 3 倍")
    print("=" * 132)
    print(f"{'W_BIGRAM':>9} " + "".join(f"{n:>40}" for n in CORPORA))
    print("-" * 132)
    for weight in (0.0, mr.W_BIGRAM / 2, mr.W_BIGRAM, mr.W_BIGRAM * 2, mr.W_BIGRAM * 3):
        with mock.patch.object(mr, "W_BIGRAM", weight):
            hits = {n: _hits(c) for n, c in CORPORA.items()}
            cells = []
            for n in CORPORA:
                flips = [i for i, (b, a) in enumerate(zip(base[n], hits[n])) if b != a]
                gained = [i for i in flips if hits[n][i]]
                lost = [i for i in flips if not hits[n][i]]
                margin = _min_margin(CORPORA[n], hits_only=True)[0]
                cells.append(f"{sum(hits[n])}/{len(CORPORA[n])}"
                             f" +{_fmt(gained)} -{_fmt(lost)} m={margin:.4f}")
        tag = "  <- 现状" if weight == mr.W_BIGRAM else ""
        print(f"{weight:>9.2f} " + "".join(f"{c:>40}" for c in cells) + tag)
    print("-" * 132)
    print("W_BIGRAM=0 那一行是本判定的关键读数：拿掉 L2 的长度偏置的同时也拿掉了")
    print("L2 的内容信号。两者在 v2 上的价签相差多少，就是「RC-2 值不值得修」的答案。")


MODES = {
    "v2": report_v2,
    "diagnose": report_diagnose,
    "ablation": report_ablation,
    "sensitivity": report_sensitivity,
    "lexicon": report_lexicon,
    "l2": report_l2,
}

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "v2"
    if mode not in MODES:
        raise SystemExit(f"unknown mode {mode!r}; choose from {sorted(MODES)}")
    MODES[mode]()
