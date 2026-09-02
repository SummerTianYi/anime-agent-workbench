"""Task B working file: Tianyi's long-term memory store.

Pilot (already implemented): session-scoped fact roundtrip on sqlite —
add / get / session isolation / restart persistence. Gate g1_memory
enforces it from day one.

Task B adds the retrieval half: score_retrieval() delegates to the
five-layer ranker in src/memory_ranker.py (golden set precision/recall
>= 0.8, see tasks/B-memory-system/SPEC.md), recall_relevant() ranks the
session-visible facts for a query, and format_memory_prompt() renders
facts into an extra_system snippet for the harness. Keep stdlib-only.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from . import memory_ranker


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

    def _visible_facts(self, session_id: int) -> list[MemoryFact]:
        """Unlimited variant of recall() scope, newest first.

        recall() 的 SQL 是冻结语义不动；排序必须看到全部可见行，否则
        相关度最高的旧事实会被新近窗口截掉。scope 谓词与 recall()
        逐字一致（global 行 + 本 session 行），跨会话零泄漏不由本方法
        另行决策。
        """
        rows = self.connection.execute(
            "SELECT * FROM facts WHERE scope = 'global' OR session_id = ? ORDER BY fact_id DESC",
            (session_id,),
        ).fetchall()
        return [_row_to_fact(row) for row in rows]

    def recall_relevant(self, session_id: int, query: str, limit: int = 1) -> list[MemoryFact]:
        """Rank session-visible facts against a query, most relevant first.

        Contract: session_id + raw query in -> up to `limit` MemoryFact out.
        Scope semantics are inherited verbatim from recall() (own rows +
        global rows), so cross-session leakage stays impossible by
        construction. Empty query means "no retrieval intent": fall back to
        recency order instead of scoring against an empty string.
        """
        visible = self._visible_facts(session_id)
        if not query.strip():
            return visible[:limit]
        ranked = memory_ranker.rank(query, [item.fact for item in visible])
        by_text = {item.fact: item for item in visible}
        return [by_text[text] for text, _ in ranked[:limit]]

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


def format_memory_prompt(facts: list[MemoryFact]) -> str:
    """Render facts into an extra_system snippet for the harness.

    Contract: MemoryFact list in -> str out; empty list yields "" so the
    harness can concatenate unconditionally. 面向 LLM 的文本用中文全角
    标点，与 BASE_SYSTEM_PROMPT 文风一致；只注入 fact 正文，存储层元数据
    （fact_id/session_id/scope）不进 prompt。标题行同时声明「程序提供」
    来源与不确定时的应对，呼应人设 prompt 的真实边界段，降低模型把
    记忆当当前对话内容编造下去的风险。
    """
    if not facts:
        return ""
    lines = "\n".join(f"- {item.fact}" for item in facts)
    return f"【已知记忆】\n以下是程序提供的用户长期记忆，仅在相关时自然引用；不确定时不要编造。\n{lines}"


def score_retrieval(golden: list[dict]) -> dict[str, float] | None:
    """Score the retrieval implementation against a golden set.

    Each golden item: {"query": str, "stored": [facts...], "relevant":
    [facts...]}. Returns {"precision": float, "recall": float}; the Optional
    in the signature is the gate's PENDING protocol (None = unimplemented)
    and is never returned now that Task B is implemented. Evaluation
    protocol (top-1 + macro average, edge conventions) is documented on
    memory_ranker.score_retrieval.
    """
    return memory_ranker.score_retrieval(golden)
