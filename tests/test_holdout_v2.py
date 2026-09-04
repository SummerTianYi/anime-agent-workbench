"""Blind holdout v2 wiring: the scoring calibre is fixed BEFORE any score is read.

可复核性（这是本文件最重要的性质，不是措辞）
    本文件的第一版 commit 里**不含任何 v2 实测分数**，也不含任何阈值断言：口径
    注释、sha256 审计锁、评分函数、以及「口径本身是否被正确实现」的构造性测试全部
    先落地并提交，之后才第一次运行 v2 评分，实测值再作为**后一格 commit** 填进棘轮
    断言。复核者只要比对这两格 commit 的先后与 diff，就能确认口径不是照着分数倒推
    的。用 git 核对的命令写在文件末尾的注释里。

    同一格 commit 里还刻意不含对 CONCEPT_LEXICON 的任何扩充——先量后改，改的依据
    只能是通用知识枚举规则，不许是「v2 哪几对失败就把那几对的词加进词典」。后者与
    「改评测集迁就实现」是同一种 Goodhart，只是方向相反。

计分口径（先定，后看分数）
    检索策略固定 top-1，与 memory_ranker.score_retrieval 和闸门 g1_memory 同口径：
    真实用途是往 extra_system 注入一条最相关记忆，所以只取分数最高的一条。

    单对定义（retrieved = top-1 的那一条，relevant = 标注的正确答案集合）：

      precision_i = |retrieved ∩ relevant| / |retrieved|
      recall_i    = |retrieved ∩ relevant| / |relevant|

    四类特殊形状的处置与理由：

    1. relevant 为空（D10 的 2 对，含「stored 为空」与「query 是纯标点」）
       recall 分母为 0 → **跳过，不计入 recall 宏平均**。
       理由：空 relevant 意味着「没有正确答案」。记满分会奖励乱返回（随便返回一条
       也算 recall=1），记 0 分会惩罚正确返回空（明明该返回空却必然得 0），两种
       都会把这一对的信号变成噪声，所以从 recall 侧摘出去。
       precision 侧**仍然计分**：stored 非空时，返回非空即记 0.0（扣分），返回空
       记 1.0。这样「查询无检索意图时应返回空」这个行为仍被考核，不会因为 recall
       跳过就完全失去约束。

    2. stored 为空（D10 的 1 对）
       retrieved 必然为空，两个指标的分母都是 0 → **precision 与 recall 都跳过**。
       它的真实考核价值不在分数，而在「实现不许崩」：有独立断言钉住 rank() 对空
       candidate 列表返回空、不抛异常。

    3. 多 relevant（D9 的 3 对）
       如实按 top-1 口径算，**不**为了让数字好看而改成 top-|relevant|。于是命中一条
       relevant 得 precision_i = 1.0、recall_i = 1/|relevant| = 0.5。
       这正是 v2 设计来解耦 P 与 R 的地方：top-1 策略在多 relevant 对上必然压低
       recall，这是**策略选择的结果，不是检索失败**。宏平均里它照实计入，读数字时
       要连着这条口径一起读。

    4. stored 只有 1 条（D11 的 1 对）
       无判别力（任何打分都命中），**如实计入**并在明细里标注 shape="single"，不
       从宏平均里摘出去——摘出去等于替读者决定哪对不算数，反而降低可审计性。

    宏平均：precision 在「stored 非空」的对上求均值（分母 31），recall 在
    「relevant 非空」的对上求均值（分母 30）。两个分母不同是上述口径的直接后果，
    明细里逐对给出 counted_p / counted_r 两个布尔位，谁进哪个平均一目了然。

    为什么不直接改 memory_ranker.score_retrieval 来承载这套口径：那个函数是闸门
    g1_memory 与 golden 集的接口面，它的「relevant 为空记 recall 0.0」是给「评测集
    不应出现此形状」准备的确定性兜底。v2 刻意包含该形状来考核退化输入，所以口径属
    于评测层，在测试侧实现，不动冻结接口。
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import unittest
from collections import Counter
from pathlib import Path
from unittest import mock

TESTS = Path(__file__).resolve().parent
REPO = TESTS.parent
for _path in (str(REPO), str(TESTS)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from src import memory_ranker as mr  # noqa: E402

# v2 语料从 Taylor 交付的文件直接 import，不复制一份副本：副本会静默失同步，
# 而「不许改语料」这条纪律只有在单一数据源下才可机器验证。
from holdout_v2 import HOLDOUT_V2  # noqa: E402

# v1 留出集与其审计锁从既有测试文件 import，H2 改造要用三集并集。
from test_memory_retrieval import (  # noqa: E402
    HOLDOUT_GOLDEN,
    HOLDOUT_GOLDEN_SHA256,
    _holdout_digest,
)

from acceptance.gates.g1_memory import GOLDEN  # noqa: E402

# v2 审计锁（仿照阶段一给 v1 加的 HOLDOUT_GOLDEN_SHA256）。
#
# 纪律（写死在这里，因为注释是唯一能被 diff 看见的地方）：v2 一经定稿即为验收
# 基准，不许为了让实现通过而修改、重排、弱化或删除其中任何一对。若实现不达标，
# 修的是实现，或者如实记录差距并把棘轮断言写成实测达到的值。重新钉这个 digest
# 本身就等于宣布「有人改了基准」，它在 diff 里藏不住。
#
# 常量放在**测试侧**而不是 holdout_v2.py 里：v2 文件是 Taylor 的交付物，本轮不许
# 改它一个字节（连加一行常量都不行，那会让「语料未被触碰」这条断言失去意义）。
# 序列化口径与 v1 完全一致：sort_keys + 紧凑分隔符 + ensure_ascii=False，否则空白
# 与转义差异会造成假阴。
HOLDOUT_V2_SHA256 = "201970d578e6760890c30ce7094c8c9c3cbcebe4d7f47663e2de39b9423490da"

# v2 语料的结构统计，逐项来自交付说明，用作接线正确性的交叉核对：如果我读错了
# 语料形状（比如把 stored 当成 relevant），这些断言会立刻红。
V2_PAIR_COUNT = 32
V2_STORED_LENGTH_DIST = {0: 1, 1: 1, 2: 4, 3: 22, 4: 4}
V2_MULTI_RELEVANT_COUNT = 3
V2_EMPTY_RELEVANT_COUNT = 2
V2_FIRST_OCCURRENCE_DIST = {"first": 12, "middle": 11, "last": 7, "n/a": 2}
V2_DIMENSION_DIST = {
    "D1": 4, "D2": 2, "D3": 2, "D4": 2, "D5": 4, "D6": 4,
    "D7": 5, "D8": 3, "D9": 3, "D10": 2, "D11": 1,
}

# 维度标注从 v2 源码的行注释里解析，不在本文件另建一份映射表：另建一份就等于
# 手抄，手抄会漂移。注释格式是 "# ---- D6 高字面重叠+D3；… ----"，第一个 D 编号
# 是主维度，其后的是副维度。
_DIMENSION_LINE = re.compile(r"^\s*#\s*----\s*(D\d.*?)\s*----\s*$")
_D_TAGS = re.compile(r"D(\d+)")


def _dimensions() -> list[tuple[str, tuple[str, ...]]]:
    """Parse (primary, secondary...) dimension tags per pair, in corpus order."""
    source = (TESTS / "holdout_v2.py").read_text(encoding="utf-8")
    tags: list[tuple[str, tuple[str, ...]]] = []
    for line in source.splitlines():
        match = _DIMENSION_LINE.match(line)
        if not match:
            continue
        found = [f"D{num}" for num in _D_TAGS.findall(match.group(1))]
        tags.append((found[0], tuple(found[1:])))
    return tags


def _text(value: object) -> str:
    """None -> "" and everything else -> str, same semantics as mr._as_text.

    在测试侧自己实现而不 import mr._as_text：评测层不该依赖实现层的私有符号，
    否则实现重构会静默改变评测口径。语义与 L3 的处置同源（None 不许变成能参与
    打分的字面量 "None"）。
    """
    return "" if value is None else str(value)


def score_holdout_v2(pairs: list[dict], ranker=mr.rank) -> dict:
    """Score one corpus under the calibre declared in this module's docstring.

    Contract: list of {"query","stored","relevant"} + a ranker callable in ->
    {"precision": float, "recall": float, "precision_n": int, "recall_n": int,
    "rows": [per-pair detail...]} out. A per-pair detail carries index, dims,
    shape, precision (None when skipped), recall (None when skipped),
    counted_p, counted_r, hit and the retrieved/top-2 texts.

    ranker 是参数而不是硬编码 mr.rank：消融与权重敏感性分析要传入被削弱的打分
    函数，评测口径本身必须保持不变，否则「哪一层造成了翻转」这个问题就无法归因。
    """
    dims = _dimensions()
    rows: list[dict] = []
    for index, pair in enumerate(pairs):
        query = _text(pair.get("query"))
        stored = [_text(fact) for fact in pair.get("stored", [])]
        relevant = {_text(fact) for fact in pair.get("relevant", [])}
        ranked = ranker(query, stored) if stored else []
        retrieved = {ranked[0][0]} if ranked else set()
        hits = len(retrieved & relevant)

        if not stored:
            precision = None          # 口径 2：分母为 0，两侧都跳过
        elif not relevant:
            precision = 0.0 if retrieved else 1.0   # 口径 1：返回非空即扣分
        else:
            precision = hits / len(retrieved) if retrieved else 0.0
        recall = (hits / len(relevant)) if relevant else None   # 口径 1/2

        if not stored:
            shape = "empty-stored"
        elif len(stored) == 1:
            shape = "single"
        elif len(relevant) > 1:
            shape = "multi-relevant"
        elif not relevant:
            shape = "empty-relevant"
        else:
            shape = "normal"
        primary, secondary = dims[index] if index < len(dims) else ("?", ())
        rows.append({
            "index": index,
            "dim": primary,
            "dim2": secondary,
            "shape": shape,
            "query": query,
            "relevant": sorted(relevant),
            "retrieved": ranked[0][0] if ranked else "",
            "runner_up": ranked[1][0] if len(ranked) > 1 else "",
            "top1_score": ranked[0][1] if ranked else 0.0,
            "top2_score": ranked[1][1] if len(ranked) > 1 else 0.0,
            "hit": bool(hits),
            "precision": precision,
            "recall": recall,
            "counted_p": precision is not None,
            "counted_r": recall is not None,
        })
    precisions = [row["precision"] for row in rows if row["counted_p"]]
    recalls = [row["recall"] for row in rows if row["counted_r"]]
    return {
        "rows": rows,
        "precision": sum(precisions) / len(precisions) if precisions else 0.0,
        "recall": sum(recalls) / len(recalls) if recalls else 0.0,
        "precision_n": len(precisions),
        "recall_n": len(recalls),
    }


class HoldoutV2AuditLockTests(unittest.TestCase):
    """The corpus is an acceptance baseline: its bytes are locked by digest."""

    def test_v2_data_is_hash_locked(self):
        canonical = json.dumps(HOLDOUT_V2, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        self.assertEqual(
            digest,
            HOLDOUT_V2_SHA256,
            "留出集 v2 被改动了。修的是实现，不是这份语料——重新钉 digest 等于宣布改基准",
        )

    def test_v2_file_bytes_match_the_pinned_lock(self):
        """语料文件的字节级指纹锁：连加一行常量都不许，否则「未触碰」失去意义。

        这把锁钉过两次，两次要证明的事不同，都记在这里：

          1. 首次钉于「把 v2 语料纳入版本控制」那一格。当时它要证明的是「语料定稿之后
             一个字节没动过」——包括不许为了让实现通过而加常量、改注释。
          2. N2 消毒时重钉。本仓要 push 到公开仓库，而仓库规则禁止 src/ 与
             tests/ 下出现用户主目录前缀或 Windows 盘符前缀这类绝对路径，注释也不
             例外；语料的隐私自述里恰好把这两类前缀当示例写了原样，故改为只描述
             约束。重钉只改了那一处注释：语料数据的规范化 sha256 前后同为
             HOLDOUT_V2_SHA256，由 test_v2_data_is_hash_locked 与
             test_v2_file_bytes_carry_no_absolute_path_literal 双向夹住。

        重钉的锁值本身就在 diff 里可见，审阅者能直接看到「谁改了基准、改了哪一行」。
        """
        blob = hashlib.sha256((TESTS / "holdout_v2.py").read_bytes()).hexdigest()
        self.assertEqual(
            blob,
            "95266b3dc670d5d9fbb914bbbc9793fb9b3f65d8e2b9514834fc58e16986ee7a",
            "tests/holdout_v2.py 的字节与记录的锁不符。改语料文件必须同时说清改了什么，"
            "并证明数据 digest（HOLDOUT_V2_SHA256）未变",
        )

    def test_v2_file_bytes_carry_no_absolute_path_literal(self):
        """N2 卫生锁：语料文件的字节不得含绝对路径字面量，且数据 digest 不得变。

        两条断言必须同时成立，缺一不可：只查字面量排除不了「顺手把语料也改了」；
        只查 digest 又阻不了注释里再写回一个主目录前缀。本文件自身也在禁止绝对路径的
        范围内，所以待查模式用 chr() 拼出来，源码里不出现任何一个原样字面量
        （否则这条测试会把自己所在的文件一起判红）。
        """
        slash, backslash = chr(47), chr(92)
        forbidden = (
            slash + "Users" + slash,
            "C:" + backslash,
            "D:" + backslash,
            "C:" + slash + "Users",
        )
        raw = (TESTS / "holdout_v2.py").read_bytes()
        blob_lines = raw.split(b"\n")
        hits = []
        for pat in forbidden:
            needle = pat.encode("utf-8")
            where = [str(n + 1) for n, ln in enumerate(blob_lines) if needle in ln]
            if where:
                hits.append(pat + " @ line " + ",".join(where))
        self.assertEqual(
            hits,
            [],
            "tests/holdout_v2.py 的字节里出现了绝对路径字面量（N2）。本仓要 push 到公开"
            "仓库，而仓库规则禁止 src/ 与 tests/ 下出现用户主目录前缀或 Windows 盘符前缀"
            "这类绝对路径，注释与字符串也不例外。失败消息刻意只报模式与行号——用 "
            "assertNotIn(needle, raw) 会把整份语料 dump 出来，红因反而看不见",
        )
        canonical = json.dumps(HOLDOUT_V2, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        self.assertEqual(
            hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
            HOLDOUT_V2_SHA256,
            "消毒只许动注释：语料数据 digest 变了就等于改了验收基准",
        )

    def test_v1_lock_is_still_intact(self):
        """护栏：v2 接线不许顺手改到 v1 的锁（改它等于为迁就实现修改基准）。"""
        self.assertEqual(_holdout_digest(HOLDOUT_GOLDEN), HOLDOUT_GOLDEN_SHA256)


class HoldoutV2StructureTests(unittest.TestCase):
    """Cross-check my reading of the corpus against the delivered statistics."""

    def test_pair_count(self):
        self.assertEqual(len(HOLDOUT_V2), V2_PAIR_COUNT)

    def test_stored_length_distribution(self):
        dist = dict(sorted(Counter(len(pair["stored"]) for pair in HOLDOUT_V2).items()))
        self.assertEqual(dist, V2_STORED_LENGTH_DIST)

    def test_multi_and_empty_relevant_counts(self):
        self.assertEqual(sum(1 for p in HOLDOUT_V2 if len(p["relevant"]) > 1), V2_MULTI_RELEVANT_COUNT)
        self.assertEqual(sum(1 for p in HOLDOUT_V2 if not p["relevant"]), V2_EMPTY_RELEVANT_COUNT)

    def test_relevant_is_always_a_subset_of_stored(self):
        """语料自述的不变量：接线前必须先确认它成立，否则命中判定毫无意义。"""
        for index, pair in enumerate(HOLDOUT_V2):
            self.assertTrue(
                set(pair["relevant"]) <= set(pair["stored"]),
                f"第 {index} 对的 relevant 不是 stored 的子集",
            )

    def test_first_occurrence_positions_are_spread(self):
        """v2 的关键设计：答案不再恒在 stored[0]（v1 的 M8 盲区）。"""
        positions: Counter[str] = Counter()
        for pair in HOLDOUT_V2:
            if not pair["relevant"] or not pair["stored"]:
                positions["n/a"] += 1
                continue
            first = min(pair["stored"].index(answer) for answer in pair["relevant"])
            last = len(pair["stored"]) - 1
            positions["first" if first == 0 else ("last" if first == last else "middle")] += 1
        self.assertEqual(dict(positions), V2_FIRST_OCCURRENCE_DIST)

    def test_dimension_annotations_cover_every_pair(self):
        """维度标注必须能逐对解析出来，否则分组失败分布无从谈起。"""
        dims = _dimensions()
        self.assertEqual(len(dims), V2_PAIR_COUNT, "解析出的维度标注行数与对数不符")
        dist = dict(sorted(Counter(primary for primary, _ in dims).items(),
                           key=lambda kv: int(kv[0][1:])))
        self.assertEqual(dist, V2_DIMENSION_DIST)

    def test_v2_does_not_reuse_v1_answers_verbatim(self):
        """诊断用事实：v2 与 v1 的答案文本重叠度，判断它是否真的「未见过」。"""
        v1_answers = {fact for pair in HOLDOUT_GOLDEN for fact in pair["relevant"]}
        v2_answers = {fact for pair in HOLDOUT_V2 for fact in pair["relevant"]}
        self.assertEqual(v1_answers & v2_answers, set(), "v2 与 v1 共享答案文本，不算未见样本")


class ScoringCalibreTests(unittest.TestCase):
    """Prove the scorer implements the declared calibre, on constructed shapes.

    这些断言用的是**构造样例**而不是 v2 数据，所以在读到任何 v2 分数之前就能写、
    就能绿——它们考核的是「口径有没有被正确实现」，与实现好坏无关。
    """

    @staticmethod
    def _always_first(query, candidates):
        """Ranker stub whose top-1 is candidates[0].

        与 mr.rank 同契约：返回列表已按分数降序，所以评分层取 ranked[0]。
        桩必须同时把顺序与分数排对，否则桩自己在说谎（本机实测踩过：只把
        分数升序排、不改候选顺序，ranked[0] 仍是 candidates[0]）。
        """
        return [(fact, float(len(candidates) - i)) for i, fact in enumerate(candidates)]

    @staticmethod
    def _always_last(query, candidates):
        """Ranker stub whose top-1 is candidates[-1] (the worst possible pick)."""
        ordered = list(reversed(candidates))
        return [(fact, float(len(ordered) - i)) for i, fact in enumerate(ordered)]

    def test_normal_pair_hit_scores_one_and_one(self):
        result = score_holdout_v2(
            [{"query": "q", "stored": ["a", "b"], "relevant": ["a"]}], self._always_first
        )
        self.assertEqual((result["precision"], result["recall"]), (1.0, 1.0))
        self.assertEqual((result["precision_n"], result["recall_n"]), (1, 1))

    def test_normal_pair_miss_scores_zero_and_zero(self):
        result = score_holdout_v2(
            [{"query": "q", "stored": ["a", "b"], "relevant": ["a"]}], self._always_last
        )
        self.assertEqual((result["precision"], result["recall"]), (0.0, 0.0))

    def test_empty_relevant_is_skipped_for_recall_but_scored_for_precision(self):
        """口径 1：recall 跳过（分母 0），precision 仍计分且返回非空即扣分。"""
        result = score_holdout_v2(
            [{"query": "q", "stored": ["a", "b"], "relevant": []}], self._always_first
        )
        row = result["rows"][0]
        self.assertIsNone(row["recall"])
        self.assertFalse(row["counted_r"])
        self.assertEqual(row["precision"], 0.0, "无正确答案时返回非空必须扣分")
        self.assertTrue(row["counted_p"])
        self.assertEqual(result["recall_n"], 0)
        self.assertEqual(result["recall"], 0.0, "无样本可评时按 0.0 报，不是 None")

    def test_empty_relevant_with_empty_retrieval_scores_precision_one(self):
        """口径 1 的另一半：正确返回空记满分，这样「该返回空」的行为有奖有罚。"""
        result = score_holdout_v2(
            [{"query": "q", "stored": ["a"], "relevant": []}], lambda query, candidates: []
        )
        row = result["rows"][0]
        self.assertEqual(row["precision"], 1.0)
        self.assertIsNone(row["recall"])

    def test_empty_stored_is_skipped_on_both_axes(self):
        """口径 2：两个分母都是 0，两侧都跳过，但实现不许崩。"""
        result = score_holdout_v2([{"query": "q", "stored": [], "relevant": []}])
        row = result["rows"][0]
        self.assertEqual(row["shape"], "empty-stored")
        self.assertIsNone(row["precision"])
        self.assertIsNone(row["recall"])
        self.assertEqual((result["precision_n"], result["recall_n"]), (0, 0))

    def test_multi_relevant_under_top_one_caps_recall_at_one_over_n(self):
        """口径 3：top-1 命中一条 relevant 得 precision=1.0、recall=1/|relevant|。"""
        result = score_holdout_v2(
            [{"query": "q", "stored": ["a", "b", "c"], "relevant": ["a", "c"]}],
            self._always_first,
        )
        row = result["rows"][0]
        self.assertEqual(row["shape"], "multi-relevant")
        self.assertEqual((row["precision"], row["recall"]), (1.0, 0.5))

    def test_single_candidate_pair_is_counted_and_flagged(self):
        """口径 4：无判别力也如实计入，只在明细里标注 shape。"""
        result = score_holdout_v2([{"query": "q", "stored": ["a"], "relevant": ["a"]}])
        row = result["rows"][0]
        self.assertEqual(row["shape"], "single")
        self.assertTrue(row["counted_p"] and row["counted_r"])
        self.assertEqual((result["precision"], result["recall"]), (1.0, 1.0))

    def test_macro_averages_use_the_declared_denominators(self):
        """宏平均分母：precision 数 stored 非空的对，recall 数 relevant 非空的对。"""
        corpus = [
            {"query": "q1", "stored": ["a", "b"], "relevant": ["a"]},
            {"query": "q2", "stored": ["a", "b"], "relevant": []},
            {"query": "q3", "stored": [], "relevant": []},
            {"query": "q4", "stored": ["a", "b"], "relevant": ["a", "b"]},
        ]
        result = score_holdout_v2(corpus, self._always_first)
        self.assertEqual(result["precision_n"], 3, "只有 stored 为空那对被摘出 precision")
        self.assertEqual(result["recall_n"], 2, "relevant 为空的两对被摘出 recall")
        self.assertAlmostEqual(result["precision"], (1.0 + 0.0 + 1.0) / 3)
        self.assertAlmostEqual(result["recall"], (1.0 + 0.5) / 2)

    def test_none_fields_do_not_become_scorable_literals(self):
        """与 L3 同源：接线层也不许把 None 折成字面量 "None" 参与打分。"""
        result = score_holdout_v2(
            [{"query": None, "stored": ["用户住在none区", "用户喜欢蓝色"], "relevant": ["用户喜欢蓝色"]}]
        )
        self.assertEqual(result["rows"][0]["query"], "")
        self.assertEqual(result["precision"], 0.0, "空查询下由同分保留输入序决定，不靠 'None' 骗命中")

    def test_scorer_is_ranker_agnostic_so_ablation_stays_comparable(self):
        """ranker 可注入：消融时口径不变，翻转才能归因到被削弱的那一层。"""
        corpus = [{"query": "q", "stored": ["a", "b"], "relevant": ["b"]}]
        self.assertEqual(score_holdout_v2(corpus, self._always_first)["recall"], 0.0)
        self.assertEqual(score_holdout_v2(corpus, self._always_last)["recall"], 1.0)


class HoldoutV2ScoringTests(unittest.TestCase):
    """Run the real corpus and report honestly, whatever the numbers are.

    本类在第一版 commit 里**只做不依赖分数的结构性断言**：跑通、产出 32 行明细、
    分母与口径一致。宏平均的棘轮阈值刻意留空，等第一次看到实测数字后再由后一格
    commit 填入——这样 git 历史能证明阈值不是先于口径拍出来的。
    """

    @classmethod
    def setUpClass(cls):
        cls.result = score_holdout_v2(HOLDOUT_V2)

    def test_every_pair_produces_one_detail_row(self):
        self.assertEqual(len(self.result["rows"]), V2_PAIR_COUNT)

    def test_denominators_match_the_declared_calibre(self):
        self.assertEqual(self.result["precision_n"], V2_PAIR_COUNT - 1, "只有 stored 为空那对不进 precision")
        self.assertEqual(self.result["recall_n"], V2_PAIR_COUNT - V2_EMPTY_RELEVANT_COUNT)

    def test_empty_stored_pair_does_not_crash_the_ranker(self):
        """口径 2 的真实考核价值：退化输入下实现必须安静返回空。"""
        self.assertEqual(mr.rank("用户喜欢什么颜色", []), [])

    def test_scores_are_within_unit_interval(self):
        for row in self.result["rows"]:
            for key in ("precision", "recall"):
                if row[key] is not None:
                    self.assertGreaterEqual(row[key], 0.0)
                    self.assertLessEqual(row[key], 1.0)

    def test_macro_averages_are_reportable(self):
        self.assertIsInstance(self.result["precision"], float)
        self.assertIsInstance(self.result["recall"], float)

    # ------------------------------------------------------------------
    # 棘轮阈值（ratchet）。钉住的是**实测达到过的水平**，不是目标。
    #
    # 保守取整的论证：向下取到 2 位小数。余量必须小于「翻转一对」造成的宏平均
    # 变化量，否则阈值松到失去棘轮意义。实测这两个量：
    #   precision 0.7741935483870968 -> 阈值 0.77，余量 0.0042；
    #     掉一对命中（24->23）会让它变成 0.7419，跌 0.0323，是余量的 7.7 倍
    #   recall 0.75 -> 阈值 0.75，余量 0.0000；
    #     掉一对命中会让它变成 0.7167，跌 0.0333
    # 两者都能被单对退步触发，同时不会被无害的浮点扰动误触发。
    # ------------------------------------------------------------------
    V2_RATCHET_PRECISION = 0.77
    V2_RATCHET_RECALL = 0.75
    V2_RATCHET_HITS = 24

    def test_v2_precision_ratchet(self):
        """目标是 0.80，当前实测 0.7742（n=31），差距 0.0258。

        差距成因：未命中 6 对里 4 对是 D7（零字面重叠语义桥接），1 对 D6
        （高字面重叠干扰），1 对 D8（口语转述）。D7 的 4 对分别是「用户多大了」
        ↔「明年就本命年了，属龙」、「身体状况怎么样」↔「有轻度哮喘」、「有什么
        爱好」↔「背着相机去郊外拍鸟」、「家乡在哪里」↔「从小在黄土高原的窑洞里
        长大」——这四条要靠文化常识或多步推理（本命年→生肖→年龄、窑洞→黄土
        高原→籍贯），闭合词表 + 字符 bigram 的架构够不到，任何词表方案都不该
        指望命中，本轮如实归类为「超出本架构能力边界」，不为它们扭曲设计。

        改进路径：(1) 写入时就打结构化槽位标签（年龄/籍贯/健康状况/爱好…），
        把语义桥接从检索期推断前移到写入期标注；(2) 放开「纯标准库、禁分词库、
        禁向量模型」的约束，引入分词或句向量。两者都不是本轮范围。

        本条红了怎么办：**停下如实报告**，不要把阈值调低，也不要照着失败对补词
        （后者是与「改评测集迁就实现」同一种 Goodhart，只是方向相反）。
        """
        self.assertGreaterEqual(
            self.result["precision"], self.V2_RATCHET_PRECISION,
            f"v2 precision 退步：实测 {self.result['precision']!r} < 棘轮 "
            f"{self.V2_RATCHET_PRECISION}，未命中对 = "
            f"{[row['index'] for row in self.result['rows'] if not row['hit'] and row['recall'] is not None]}",
        )

    def test_v2_recall_ratchet(self):
        """目标是 0.80，当前实测 0.7500（n=30），差距 0.0500。

        recall 低于 precision 的结构性原因：top-1 策略在 D9 的 3 个多 relevant 对
        上必然把 recall 压到 1/|rel| = 0.50（precision 仍是 1.00）。这是策略选择的
        结果而非检索失败——3 对 × 0.50 的损失摊到 30 对分母上就是 0.05，正好是
        与 0.80 的全部差距。换句话说：**若多 relevant 对按 top-|rel| 取，recall 会
        是 0.80**。本轮刻意不改成 top-|rel|，因为那会掩盖 P 与 R 的解耦，而 v2 设计
        这 3 对正是为了暴露它。

        其余口径与 test_v2_precision_ratchet 相同：红了停下报告，不调阈值不补词。
        """
        self.assertGreaterEqual(
            self.result["recall"], self.V2_RATCHET_RECALL,
            f"v2 recall 退步：实测 {self.result['recall']!r} < 棘轮 {self.V2_RATCHET_RECALL}",
        )

    def test_v2_hit_count_ratchet(self):
        """命中对数的棘轮：24/32。

        宏平均可能被 P 与 R 的反向变化互相掩盖（一对从「命中但只中一条 relevant」
        变成「未命中」时两者同向，但另一些组合不会），所以补一条直接钉命中对数的
        断言。按维度分组的实测：D1 4/4、D2 2/2、D3 2/2、D4 2/2、D5 4/4、D6 3/4、
        D7 1/5、D8 2/3、D9 3/3、D10 不计（退化对）、D11 1/1。
        """
        hits = sum(1 for row in self.result["rows"] if row["hit"])
        self.assertGreaterEqual(
            hits, self.V2_RATCHET_HITS,
            f"v2 命中对数退步：{hits} < 棘轮 {self.V2_RATCHET_HITS}",
        )


class ThreeCorpusRatchetTests(unittest.TestCase):
    """golden / v1 / v2 三集的不回归棘轮——本轮所有改动都必须让三集只升不降。

    golden 与 v1 的既有断言（test_memory_retrieval.py 的 ScoreRetrievalTests）只是
    >=0.8 的**门槛**：从 1.000 掉到 0.85 不会红。本轮做了 L1-L8/L11/M19 九条延后项、
    H2 判据改造、RC-3/RC-4/RC-5/RC-7 四轮修复与规则驱动扩词（词典 88 -> 612），
    每一次都可能悄悄吃掉 golden 或 v1 的命中，所以这里把实测满分钉成棘轮。

    红了怎么办：用户纪律写的是「如实报告并停下，不要回退修复也不要特判」。把阈值
    从 1.0 调低就等于特判。
    """

    FULL_RATCHET = 1.0

    def test_golden_is_still_perfect(self):
        scored = mr.score_retrieval(GOLDEN)
        self.assertGreaterEqual(scored["precision"], self.FULL_RATCHET, f"golden precision 退步：{scored}")
        self.assertGreaterEqual(scored["recall"], self.FULL_RATCHET, f"golden recall 退步：{scored}")

    def test_v1_holdout_is_still_perfect(self):
        scored = mr.score_retrieval(HOLDOUT_GOLDEN)
        self.assertGreaterEqual(scored["precision"], self.FULL_RATCHET, f"v1 precision 退步：{scored}")
        self.assertGreaterEqual(scored["recall"], self.FULL_RATCHET, f"v1 recall 退步：{scored}")

    def test_all_three_corpora_are_scored_by_the_same_rank_function(self):
        """三集必须走同一个 rank()，否则棘轮之间不可比、消融也无法对照。

        判据是**调用计数**而不是「函数对象相等」：初版写的 _ranker_of() 无条件
        return mr.rank，assertIs 恒真，属零判别力（与 H2 被审查者证伪的那条断言
        同类），自查时抓出来重写。现在数的是 rank() 实际被调用了几次——把 mr.rank
        换成哨兵之后，三集各自必须触发「与语料对数相同」的调用次数。任何一集被
        悄悄换成别的排序器，对应那条计数就会红。

        注意 score_holdout_v2 的 ranker 是**默认参数**，在 def 执行时就绑定了当时
        的 mr.rank；patch 之后默认值仍指向原函数，所以这里显式传 ranker=mr.rank，
        读的是 patch 生效后的模块属性。这个绑定语义也正是
        test_scorer_is_ranker_agnostic_so_ablation_stays_comparable 存在的原因：
        消融时显式注入被削弱的排序器，计分口径保持不变。
        """
        calls: list[int] = []
        real_rank = mr.rank

        def sentinel(query, candidates):
            calls.append(1)
            return real_rank(query, candidates)

        with mock.patch.object(mr, "rank", sentinel):
            mr.score_retrieval(GOLDEN)
            golden_calls = len(calls)
            mr.score_retrieval(HOLDOUT_GOLDEN)
            v1_calls = len(calls) - golden_calls
            score_holdout_v2(HOLDOUT_V2, ranker=mr.rank)
            v2_calls = len(calls) - golden_calls - v1_calls

        self.assertEqual(golden_calls, len(GOLDEN), "golden 每对必须恰好调用一次 rank()")
        self.assertEqual(v1_calls, len(HOLDOUT_GOLDEN), "v1 每对必须恰好调用一次 rank()")
        # v2 的 stored 为空那对按口径 2 **不调用** ranker（score_holdout_v2 里是
        # `ranker(query, stored) if stored else []`），期望值必须扣掉它，否则这条
        # 断言会把「按口径跳过」误判成「少跑了一对」——第一次跑就是这么红的（31!=32）。
        # 扣减项取 V2_STORED_LENGTH_DIST[0] 而不是硬写 1，是为了让「空 stored 的对数」
        # 与语料结构统计互相钉住：任何一边漂移都会红。
        v2_expected = len(HOLDOUT_V2) - V2_STORED_LENGTH_DIST[0]
        self.assertEqual(
            v2_calls, v2_expected,
            "v2 里只有 stored 为空的对可以不调用 rank()（口径 2）；调用次数与"
            "「有候选可排的对数」不符，说明跳过条件被放宽或收紧了",
        )


# 复核「口径先于分数」的命令（在仓库根目录执行）：
#   git log --oneline -- tests/test_holdout_v2.py
#   git show <第一格>:tests/test_holdout_v2.py | grep -c "棘轮\|RATCHET"
# 第一格里应当找不到任何实测宏平均数值；阈值出现在其后那一格的 diff 里。

if __name__ == "__main__":
    unittest.main(verbosity=2)
