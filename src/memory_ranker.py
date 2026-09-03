# main-repo-target: services/agent-core/agent_core/memory_ranker.py
"""Lexicon-free retrieval ranking for Tianyi's long-term memory facts.

Five-layer scoring model over raw Chinese text (no tokenizer, stdlib only):

  L1 normalize          NFKC fold, lowercase, strip whitespace + punctuation
  L2 bigram_similarity  character-bigram multiset cosine (dictionary-free)
  L3 concept_bridge     small concept lexicon bridges non-overlapping wordings
  L4 preference_bonus   explicit preference assertions ("喜欢 X") count as
                        stronger evidence for stable-attribute queries
  L5 transient_penalty  tense markers ("最近/今天") demote short-term states
                        when the query asks for a stable attribute

Layers are separate pure functions so each signal can be unit-tested and the
weight constants can be perturbed independently (sensitivity analysis lives
in evidence/task_b_retrieval_analysis.md).
"""
from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ConceptClass:
    """One semantic class: head words name the concept, members are typical
    values / synonymous surface forms used to detect hits."""

    name: str
    head: tuple[str, ...]
    member: tuple[str, ...]


# 概念词典：每类 head 是概念名，member 是典型取值/同义表达。
# 反过拟合硬约束（tests 里机器可验证）：每类 ≥3 个 member 不在评测 golden
# 集任何位置出现，词典因此是通用概念知识而非答案换皮。member 用子串
# 命中，允许跨类重叠（如「老师」同属称呼与职业）：真实概念本就有交叠，
# 桥接强度由双侧命中数共同决定，单类重叠不会单独拉开分差。
# head 一律不用单字（审查发现 M1）：单字做子串命中会让「超市/角色/脸色/
# 色号」被误判成城市/颜色类提问，稳定属性门控随之误开、L5 反噬对题的近期
# 事实。golden 的 8 个查询全部含双字 head，去掉单字不影响评测。
CONCEPT_LEXICON: dict[str, ConceptClass] = {
    "颜色": ConceptClass(
        name="颜色",
        head=("颜色",),
        member=("红", "橙", "黄", "绿", "青", "蓝", "紫", "黑", "白", "灰", "粉", "棕", "金", "银"),
    ),
    "城市": ConceptClass(
        name="城市",
        head=("城市",),
        member=("北京", "上海", "广州", "深圳", "杭州", "南京", "成都", "武汉", "西安", "苏州", "天津", "重庆", "家乡", "籍贯"),
    ),
    "称呼": ConceptClass(
        name="称呼",
        head=("称呼", "名字", "姓名"),
        member=("叫", "昵称", "老板", "老师", "先生", "女士", "小姐", "同学"),
    ),
    "生日": ConceptClass(
        name="生日",
        head=("生日", "出生"),
        member=("月", "日", "号", "年龄", "岁", "星座"),
    ),
    "宠物": ConceptClass(
        name="宠物",
        head=("宠物",),
        member=("猫", "狗", "兔子", "仓鼠", "鹦鹉", "乌龟", "金鱼", "蜥蜴", "养"),
    ),
    "过敏": ConceptClass(
        name="过敏",
        head=("过敏",),
        member=("花粉", "海鲜", "芒果", "尘螨", "敏感", "忌口", "乳糖", "酒精", "药物"),
    ),
    "职业": ConceptClass(
        name="职业",
        head=("职业", "工作"),
        member=("上班", "公司", "工程师", "程序员", "老师", "教师", "医生", "护士", "设计师", "会计", "律师", "司机", "职员"),
    ),
    "爱好": ConceptClass(
        name="爱好",
        head=("爱好", "兴趣"),
        member=("喜欢", "热爱", "徒步", "登山", "跑步", "游泳", "骑车", "唱歌", "画画", "读书", "旅游", "摄影", "钓鱼", "健身", "运动"),
    ),
}

# L1 剥离集：ASCII 标点 + CJK 标点/全角符号区 + 各类空白。宁可多剥：
# 字面相似度层只关心内容字符，标点在全角/半角混写时本身就不稳定。
_STRIP_RE = re.compile(
    "[\\s"
    "!-/:-@\\[-`{-~"
    "\u3000-\u303f"
    "\uff00-\uffef"
    "]+"
)


def normalize(text: str) -> str:
    """L1: fold to a comparison-safe form.

    Contract: any str in -> str out. NFKC (folds fullwidth ASCII to
    halfwidth), casefold, then strip whitespace and ASCII/CJK punctuation.
    CJK ideographs and digits survive; the result is what L2-L5 match on.
    """
    folded = unicodedata.normalize("NFKC", text).lower()
    return _STRIP_RE.sub("", folded)


def _ngram_multiset(text: str, n: int) -> Counter[str]:
    return Counter(text[i : i + n] for i in range(len(text) - n + 1))


def _cosine(left: Counter[str], right: Counter[str]) -> float:
    if not left or not right:
        return 0.0
    if left == right:
        # 数学上恒为 1，但 sqrt 浮点误差会给出 0.9999999999999998；
        # 「多重集相同必为 1.0」是对外契约，短路保精确。
        return 1.0
    dot = sum(count * right[gram] for gram, count in left.items())
    if dot == 0:
        return 0.0
    norm_left = math.sqrt(sum(count * count for count in left.values()))
    norm_right = math.sqrt(sum(count * count for count in right.values()))
    return dot / (norm_left * norm_right)


def bigram_similarity(a: str, b: str) -> float:
    """L2: character-bigram multiset cosine over normalized text.

    Contract: two raw strings in -> float in [0.0, 1.0] out. 1.0 iff the two
    normalized n-gram multisets are proportional — that includes identical
    strings AND repetition-only variants (哈哈 vs 哈哈哈哈), because cosine is
    scale-invariant. 0.0 for disjoint gram sets or empty input.
    Degradation rule: if either side normalizes to fewer than 2 chars it has
    no bigrams, so BOTH sides fall back to unigram multisets (mixed n-gram
    orders would always intersect in zero and silently kill the signal).

    审查发现 M3 的处置：旧 docstring 声称「1.0 只给归一化后完全相同的字符
    串」，但余弦对成比例向量恒为 1，契约与实现不符。两个修法里选「改契约」
    而不是「改实现」（在 _cosine 后乘 min(len)/max(len) 的长度阻尼）：阻尼会
    系统性惩罚「查询短、事实长」这一常态形态——golden 与留出集里的事实普遍
    长于查询——把 L2 从内容探测器变成长度探测器。成比例为 1 的语义是
    「n-gram 分布相同」，对重复型文本判为高度相似在检索语境里是可接受的：
    它们是同一个内容的重复，而不是不同内容。改实现会动所有 L2 数值、需重做
    全部权重敏感性与逐层消融，收益却是把一个诚实的性质藏起来。
    """
    left, right = normalize(a), normalize(b)
    if not left or not right:
        return 0.0
    n = 2 if min(len(left), len(right)) >= 2 else 1
    return _cosine(_ngram_multiset(left, n), _ngram_multiset(right, n))


def _masked_scan(text: str, words: tuple[str, ...]) -> list[str]:
    """Longest-first greedy scan over normalized text.

    Contract: normalized text + words in -> the matched words out, forming the
    largest non-overlapping subset the greedy finds; each word appears at most
    once in the result.

    最长优先贪心掩码（审查发现 M4）：`sum(1 for w in words if w in text)`
    对嵌套词重复计数——「颜色」会同时命中 head「颜色」与旧 head「色」，
    「生日」会同时命中「生日」与 member「日」。同样的证据强度只因该类词表
    存在嵌套关系就被抬高，跨类不可比，与 concept_bridge docstring「几何均值
    让单个弱命中不超过 head 级命中」的口径不符。贪心按词长降序取最大不重叠
    集合，是该问题的标准近似解；对本词表（最长 3 字）它给出的就是最优解。
    """
    used = bytearray(len(text))
    matched: list[str] = []
    for word in sorted(words, key=len, reverse=True):
        start = text.find(word)
        while start != -1:
            end = start + len(word)
            if not any(used[start:end]):
                used[start:end] = b"\x01" * len(word)
                matched.append(word)
                break
            start = text.find(word, start + 1)
    return matched


def _masked_hits(text: str, words: tuple[str, ...]) -> int:
    """Count the largest non-overlapping subset of `words` present in text."""
    return len(_masked_scan(text, words))


def _concept_hits(text: str, concept: ConceptClass) -> int:
    """Count head+member hits (substring, non-overlapping) in normalized text."""
    return _masked_hits(text, (*concept.head, *concept.member))


def concept_bridge(query: str, fact: str) -> float:
    """L3: lexicon-bridged semantic affinity in [0.0, 1.0].

    Contract: two raw strings in -> float out. For every concept class hit by
    BOTH sides (head or member, substring match on normalized text), the
    class contributes sqrt(qh*fh) / (sqrt(qh*fh) + 1) where qh/fh are the
    per-side hit counts; the result is the mean over contributing classes.
    One-sided hits contribute nothing — a bridge needs both banks, otherwise
    every fact sharing 「用户」 with the query would collect noise points.
    The geometric mean keeps a lone weak hit (e.g. query says 喜欢 which is
    an 爱好 member) from outranking a solid head-level match.
    """
    q, f = normalize(query), normalize(fact)
    contributions: list[float] = []
    for concept in CONCEPT_LEXICON.values():
        qh = _concept_hits(q, concept)
        fh = _concept_hits(f, concept)
        if qh == 0 or fh == 0:
            continue
        strength = math.sqrt(qh * fh)
        contributions.append(strength / (strength + 1.0))
    if not contributions:
        return 0.0
    return sum(contributions) / len(contributions)


# 合成权重：全局常量，禁止按样例逐条调参；扰动敏感性分析见
# evidence/task_b_retrieval_analysis.md。
W_BIGRAM = 0.30
W_CONCEPT = 0.55
W_PREFERENCE = 0.10
W_TRANSIENT = 0.35


# 偏好/断言谓词，按极性分两组（审查发现 M2）。旧实现把肯定与否定谓词
# 混在一个 PREFERENCE_MARKERS 里且不辨查询极性，于是查询「用户的爱好」下
# 「用户讨厌运动」拿到与「用户周末喜欢徒步」同等的加分并排到 top-1——
# 注入 extra_system 即语义反转，LLM 会据此以为用户喜欢运动。
# NEGATIVE_MARKERS 收「过敏」而不只「过敏于」：「用户对海鲜过敏」是负面约束
# 断言最典型的表达形式，也是忌口类提问最对题的证据。
POSITIVE_MARKERS: tuple[str, ...] = (
    "最喜欢", "喜欢", "希望", "热爱", "偏好", "爱吃", "感兴趣", "只想",
)
NEGATIVE_MARKERS: tuple[str, ...] = (
    "不喜欢", "讨厌", "不吃", "受不了", "忌讳", "过敏",
)

# 查询侧的负面取向词：问「忌口/讨厌/不能吃」时，否定谓词才是对题证据。
QUERY_NEGATIVE_MARKERS: tuple[str, ...] = (
    "不喜欢", "讨厌", "忌口", "忌讳", "禁忌", "不能吃", "吃不了", "受不了", "过敏",
)

# 时态标记：短期状态/临时行为的信号词。
# 「刚」是单字，会误伤「刚才/金刚」类词——已知噪声，只在稳定属性
# 提问下生效，影响面可控，换双字词会漏掉「刚换/刚养」这类真实表达。
TRANSIENT_MARKERS: tuple[str, ...] = (
    "最近", "这几天", "今天", "昨天", "刚", "正在", "临时",
)


def _marker_count(text: str, markers: tuple[str, ...]) -> int:
    return sum(1 for marker in markers if marker in text)


def _is_stable_attribute_query(query: str) -> bool:
    """Gate for L4/L5: does the query ask for a stable attribute?

    Contract: raw query in -> bool out. True iff the normalized query
    contains at least one CONCEPT_LEXICON head word (爱好/职业/城市/…).
    行为式提问（「周末一般干嘛」）不含 head 词，L4/L5 对它们保持静默。
    """
    q = normalize(query)
    return any(head in q for concept in CONCEPT_LEXICON.values() for head in concept.head)


def _query_polarity(query: str) -> int:
    """Classify the query's orientation: +1 positive, -1 negative, 0 silent.

    Contract: raw query in -> int out. -1 when the query itself asks for a
    negative orientation (忌口/讨厌/不能吃/过敏…), +1 when it asks for a stable
    attribute (normalized query contains a CONCEPT_LEXICON head word), 0
    otherwise — in which case L4 stays silent.

    负面判定优先于稳定属性判定：「用户对花过敏」既含 head「过敏」也含负面
    取向词，此时它问的是负面约束，按 -1 处理才对题。中性（0）保留旧行为：
    行为式提问（「周末一般干嘛」）不含 head 词，L4 对它们保持静默，否则
    闲聊查询也会被带偏好词的事实抢位。
    """
    if _masked_hits(normalize(query), QUERY_NEGATIVE_MARKERS):
        return -1
    if _is_stable_attribute_query(query):
        return 1
    return 0


def _polarity_hits(text: str) -> tuple[int, int]:
    """Joint polarity scan over normalized text -> (positive, negative) hits.

    Contract: normalized text in -> (int, int) out, both >= 0.

    两组必须一起扫描并共享掩码：「不喜欢」含子串「喜欢」，分开扫描会让
    肯定词与否定词各计一次、极性互相抵消。
    """
    matched = _masked_scan(text, POSITIVE_MARKERS + NEGATIVE_MARKERS)
    positive = sum(1 for word in matched if word in POSITIVE_MARKERS)
    return positive, len(matched) - positive


def preference_bonus(query: str, fact: str) -> float:
    """L4: polarity-aware predicate evidence, signed.

    Contract: raw query+fact in -> float in [-1.0, 1.0] out. Non-zero only when
    the query carries an orientation (see _query_polarity); predicates matching
    that orientation add, opposing ones subtract. Each side saturates at
    min(count, 2) / 2.

    「喜欢 X」是对偏好的显式肯定断言，「讨厌 X」是否定断言，两者对同一个
    提问的证据价值符号相反；「在 X」只陈述行为，不带极性信号。旧实现只加分
    不辨极性，问「爱好」时否定事实与肯定事实同分甚至更高（审查发现 M2）。
    饱和计数保留：多个同向谓词叠加只小幅增信，防止堆词刷分。
    """
    polarity = _query_polarity(query)
    if polarity == 0:
        return 0.0
    positive, negative = _polarity_hits(normalize(fact))
    matched, opposed = (positive, negative) if polarity > 0 else (negative, positive)
    return min(matched, 2) / 2.0 - min(opposed, 2) / 2.0


def transient_penalty(query: str, fact: str) -> float:
    """L5: short-term states get demoted, under the same stable-query gate.

    Contract: raw query+fact in -> float in [0.0, 1.0] out (subtracted from
    the final score by score()). Non-zero only when the query asks for a
    stable attribute AND the fact carries a tense marker (最近/今天/刚/…).
    Design rationale: 查询「用户的爱好/职业」问的是稳定属性，带时态标记
    的事实是短期状态，不该抢占稳定属性的召回位；反之问「最近干嘛」时
    这些事实恰恰对题，所以门控必须双向生效。
    """
    if not _is_stable_attribute_query(query):
        return 0.0
    hits = _marker_count(normalize(fact), TRANSIENT_MARKERS)
    return min(hits, 2) / 2.0


def score(query: str, fact: str) -> float:
    """Compose the five layers into one relevance score.

    Contract: raw query+fact in -> float out (may be negative when L5 fires
    hard). score = W_BIGRAM*L2 + W_CONCEPT*L3 + W_PREFERENCE*L4 -
    W_TRANSIENT*L5. The weights are module-level constants on purpose:
    per-example tuning would turn the lexicon into golden-set camouflage.
    """
    return (
        W_BIGRAM * bigram_similarity(query, fact)
        + W_CONCEPT * concept_bridge(query, fact)
        + W_PREFERENCE * preference_bonus(query, fact)
        - W_TRANSIENT * transient_penalty(query, fact)
    )


def rank(query: str, candidates: list[str]) -> list[tuple[str, float]]:
    """Order candidates by relevance, keeping the full list.

    Contract: raw query + candidate facts in -> [(fact, score), ...] out,
    descending by score. Ties keep input order (list.sort is stable), so
    results are reproducible across runs. Callers wanting top-k slice the
    result; score_retrieval and MemoryStore.recall_relevant both take top-1.
    """
    scored = [(candidate, score(query, candidate)) for candidate in candidates]
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored


def score_retrieval(golden: list[dict]) -> dict[str, float]:
    """Evaluate top-1 retrieval quality against a golden set.

    Contract: list of {"query": str, "stored": [facts...], "relevant":
    [facts...]} in -> {"precision": float, "recall": float} out (both keys
    always present; the gate reads them with .get(key, 0), so a missing key
    would silently score zero).

    口径（与 g1_memory 判定一致）：
      - 检索策略 top-1：每条查询只取分数最高的一条。真实用途是往
        extra_system 注入一条最相关记忆，且评测集 relevant 恒为单项；
        需要 top-k 的调用方直接用 rank()。
      - 单条：precision_i = |retrieved ∩ relevant| / |retrieved|（retrieved
        为空记 0.0）；recall_i = |retrieved ∩ relevant| / |relevant|
        （relevant 为空记 0.0，确定性口径，评测集不应出现此形状）。
      - 汇总：宏平均（macro），mean(precision_i) / mean(recall_i)。
      - 空 golden 集：无样本可评，两指标均记 0.0。
    """
    if not golden:
        return {"precision": 0.0, "recall": 0.0}
    precisions: list[float] = []
    recalls: list[float] = []
    for item in golden:
        query = str(item.get("query", ""))
        stored = [str(fact) for fact in item.get("stored", [])]
        relevant = {str(fact) for fact in item.get("relevant", [])}
        ranked = rank(query, stored)
        retrieved = {ranked[0][0]} if ranked else set()
        hits = len(retrieved & relevant)
        precisions.append(hits / len(retrieved) if retrieved else 0.0)
        recalls.append(hits / len(relevant) if relevant else 0.0)
    return {
        "precision": sum(precisions) / len(precisions),
        "recall": sum(recalls) / len(recalls),
    }
