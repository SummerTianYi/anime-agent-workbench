"""Task B working file: Tianyi's long-term memory store.

Pilot (already implemented): session-scoped fact roundtrip on sqlite —
add / get / session isolation / restart persistence. Gate g1_memory
enforces it from day one.

Task B implements score_retrieval() so the golden set reaches
precision/recall >= 0.8 (see tasks/B-memory-system/SPEC.md), plus any
consolidation design. Keep stdlib-only.
"""
from __future__ import annotations

import math
import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class MemoryFact:
    fact_id: int
    session_id: int
    scope: str  # "session" or "global"
    fact: str
    source_request_id: str


class MemoryStore:
    def __init__(self, path: Path | str | None = None) -> None:
        if path is None:
            import tempfile

            handle = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
            handle.close()
            path = Path(handle.name)
        self.path = Path(path)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS facts ("
            " fact_id INTEGER PRIMARY KEY AUTOINCREMENT,"
            " session_id INTEGER NOT NULL,"
            " scope TEXT NOT NULL,"
            " fact TEXT NOT NULL,"
            " source_request_id TEXT NOT NULL DEFAULT '')"
        )
        self.connection.commit()

    def add(self, fact: str, session_id: int, scope: str = "session", source_request_id: str = "") -> int:
        if scope not in {"session", "global"}:
            raise ValueError(f"unknown scope: {scope}")
        cursor = self.connection.execute(
            "INSERT INTO facts (session_id, scope, fact, source_request_id) VALUES (?, ?, ?, ?)",
            (session_id, scope, fact, source_request_id),
        )
        self.connection.commit()
        return int(cursor.lastrowid)

    def recall(self, session_id: int, limit: int = 10) -> list[MemoryFact]:
        """Facts visible inside one session: its own rows plus global rows."""
        rows = self.connection.execute(
            "SELECT * FROM facts WHERE scope = 'global' OR session_id = ? ORDER BY fact_id DESC LIMIT ?",
            (session_id, limit),
        ).fetchall()
        return [_row_to_fact(row) for row in rows]

    def close(self) -> None:
        self.connection.close()


def _row_to_fact(row: sqlite3.Row) -> MemoryFact:
    return MemoryFact(
        fact_id=int(row["fact_id"]),
        session_id=int(row["session_id"]),
        scope=str(row["scope"]),
        fact=str(row["fact"]),
        source_request_id=str(row["source_request_id"]),
    )


def score_retrieval(golden: list[dict]) -> dict[str, float] | None:
    """Score the lexical retriever (retrieve_relevant) against a golden set.

    Each golden item: {"query": str, "stored": [facts...], "relevant": [facts...]}.
    Returns micro-averaged precision/recall plus per-item detail, or None if
    golden is empty.
    """
    if not golden:
        return None
    hits = 0
    retrieved_total = 0
    relevant_total = 0
    per_item = []
    for item in golden:
        query = str(item.get("query", ""))
        stored = [str(f) for f in item.get("stored", [])]
        relevant = set(item.get("relevant", []))
        got = set(retrieve_relevant(query, stored))
        hit = len(got & relevant)
        hits += hit
        retrieved_total += len(got)
        relevant_total += len(relevant)
        per_item.append(
            {
                "query": query,
                "retrieved": sorted(got),
                "missed": sorted(relevant - got),
                "false_positives": sorted(got - relevant),
            }
        )
    precision = hits / retrieved_total if retrieved_total else 0.0
    recall = hits / relevant_total if relevant_total else 0.0
    return {"precision": precision, "recall": recall, "per_item": per_item}


# --- lexical retriever -----------------------------------------------------
# Chinese-friendly lexical retrieval: function characters are stripped, the
# remaining text is tokenized into characters and character bigrams, tokens
# are weighted by smoothed IDF over the candidate facts of the current item,
# and abstract attribute nouns in the query (职业/爱好/颜色/...) are expanded
# into low-weight concrete indicator words. This bridges pairs like
# "用户的职业" -> "用户是后端工程师" that share no lexical token.

_STOP_CHARS = set("的了是在最了为对吗呢吧啊嘛哦什哪怎谁用户您请很也还又都就")

# abstract attribute noun -> typical concrete indicator words (query expansion,
# deliberately generic; expansion matches weigh 0.4x a direct match)
_EXPANSION = {
    "颜色": "蓝 红 绿 黄 白 黑 紫 粉 棕 灰 颜色",
    "生日": "出生 生日 诞辰 岁 蛋糕 星座",
    "称呼": "叫 名字 姓名 昵称 称谓 称呼",
    "职业": "工程师 程序 上班 工作 公司 加班 同事 设计师 医生 老师 后端 前端",
    "爱好": "喜欢 兴趣 周末 游戏 唱歌 画画 旅游 徒步 健身 运动 休闲",
    "宠物": "猫 狗 鸟 鱼 养 宠物",
    "城市": "工作 住 生活 地址 位置 城市",
}

_EXPANSION_WEIGHT = 0.4
_UNIGRAM_WEIGHT = 0.5
_RELATED_RATIO = 0.5  # co-retrieve facts scoring at least this fraction of the best


def _content_chars(text: str) -> list[str]:
    return [c for c in text if c not in _STOP_CHARS and not c.isspace()]


def _tokens(text: str) -> tuple[set[str], set[str]]:
    chars = _content_chars(text)
    return set(chars), {a + b for a, b in zip(chars, chars[1:])}


def _query_parts(query: str) -> tuple[set[str], set[str], set[str], set[str]]:
    """(direct unigrams, direct bigrams, expansion unigrams, expansion bigrams)."""
    q_uni, q_bi = _tokens(query)
    exp_uni: set[str] = set()
    exp_bi: set[str] = set()
    for key, indicators in _EXPANSION.items():
        if key in query:
            for word in indicators.split():
                w_uni, w_bi = _tokens(word)
                exp_uni |= w_uni
                exp_bi |= w_bi
    return q_uni, q_bi, exp_uni, exp_bi


def retrieve_relevant(query: str, stored: list[str], limit: int = 3) -> list[str]:
    """Rank candidate facts against a query; returns the relevant subset."""
    if not stored:
        return []
    q_uni, q_bi, q_exp_uni, q_exp_bi = _query_parts(query)
    fact_uni = []
    fact_bi = []
    for fact in stored:
        fu, fb = _tokens(fact)
        fact_uni.append(fu)
        fact_bi.append(fb)

    df_uni: dict[str, int] = {}
    df_bi: dict[str, int] = {}
    for fu in fact_uni:
        for token in fu:
            df_uni[token] = df_uni.get(token, 0) + 1
    for fb in fact_bi:
        for token in fb:
            df_bi[token] = df_bi.get(token, 0) + 1
    n = len(stored)
    idf_u = {t: math.log((n + 1) / (d + 0.5)) for t, d in df_uni.items()}
    idf_b = {t: math.log((n + 1) / (d + 0.5)) for t, d in df_bi.items()}

    scores = []
    for i, fact in enumerate(stored):
        score = 0.0
        for token in q_uni & fact_uni[i]:
            score += idf_u.get(token, 0.0) * _UNIGRAM_WEIGHT
        for token in q_bi & fact_bi[i]:
            score += idf_b.get(token, 0.0)
        for token in q_exp_uni & fact_uni[i]:
            score += idf_u.get(token, 0.0) * _UNIGRAM_WEIGHT * _EXPANSION_WEIGHT
        for token in q_exp_bi & fact_bi[i]:
            score += idf_b.get(token, 0.0) * _EXPANSION_WEIGHT
        scores.append((score, i))

    best = max(score for score, _ in scores)
    if best <= 0.0:
        return [stored[0]]  # no lexical signal at all: deterministic fallback
    picked = [
        stored[i]
        for score, i in sorted(scores, key=lambda pair: (-pair[0], pair[1]))
        if score >= best * _RELATED_RATIO
    ]
    return picked[:limit]
