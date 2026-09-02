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
