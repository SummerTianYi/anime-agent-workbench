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
CONCEPT_LEXICON: dict[str, ConceptClass] = {
    "颜色": ConceptClass(
        name="颜色",
        head=("颜色", "色"),
        member=("红", "橙", "黄", "绿", "青", "蓝", "紫", "黑", "白", "灰", "粉", "棕", "金", "银"),
    ),
    "城市": ConceptClass(
        name="城市",
        head=("城市", "市"),
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
        # 「完全相同必为 1.0」是对外契约，短路保精确。
        return 1.0
    dot = sum(count * right[gram] for gram, count in left.items())
    if dot == 0:
        return 0.0
    norm_left = math.sqrt(sum(count * count for count in left.values()))
    norm_right = math.sqrt(sum(count * count for count in right.values()))
    return dot / (norm_left * norm_right)


def bigram_similarity(a: str, b: str) -> float:
    """L2: character-bigram multiset cosine over normalized text.

    Contract: two raw strings in -> float in [0.0, 1.0] out. 1.0 only for
    identical normalized forms, 0.0 for disjoint gram sets or empty input.
    Degradation rule: if either side normalizes to fewer than 2 chars it has
    no bigrams, so BOTH sides fall back to unigram multisets (mixed n-gram
    orders would always intersect in zero and silently kill the signal).
    """
    left, right = normalize(a), normalize(b)
    if not left or not right:
        return 0.0
    n = 2 if min(len(left), len(right)) >= 2 else 1
    return _cosine(_ngram_multiset(left, n), _ngram_multiset(right, n))


def _concept_hits(text: str, concept: ConceptClass) -> int:
    """Count head+member occurrences (substring) in already-normalized text."""
    return sum(1 for word in (*concept.head, *concept.member) if word in text)


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
