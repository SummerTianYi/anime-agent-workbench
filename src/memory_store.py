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

        排序走下标而不走文本：facts 表无 UNIQUE 约束，同一文本合法地
        存在多行（global 行与 session 行重复沉淀是常态）。按文本建字典反查
        会让后一行覆盖前一行，结果把本会话行误标成 global 身份、并让 limit
        的槽位被同一行重复占用——下游按 fact_id/scope 做删除或全局化提升
        会操错行。sorted(reverse=True) 对同分保留原序（新近优先）。
        """
        visible = self._visible_facts(session_id)
        if not query.strip():
            return visible[:limit]
        order = sorted(
            range(len(visible)),
            key=lambda index: memory_ranker.score(query, visible[index].fact),
            reverse=True,
        )
        return [visible[index] for index in order[:limit]]

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


# 单条事实进 prompt 的长度上限，与 harness.parse_reply 的
# memory_candidate = value.strip()[:200] 同口径。add() 是公开 API，调用方
# 可以绕过 parse_reply 直接塞任意长文本，所以渲染层自带上限，不依赖上游
# 一定截过。
_MAX_FACT_CHARS = 200

# 段落标记中和表：BASE_SYSTEM_PROMPT 用【…】作段落标记（【身份】
# 【自我认知与真实边界】【音乐身份】【表达方式】【输出契约】），记忆正文里
# 出现同形括号就能伪造段落边界，故换成形近的〔〕。
_MARKER_TRANSLATION = str.maketrans({"【": "〔", "】": "〕"})


def _sanitize_fact(text: str) -> str:
    """Flatten one stored fact into a single inert line safe for prompt use.

    Contract: str in -> str out; the output contains no \\n / \\r / \\t, no
    【 and no 】, and is at most _MAX_FACT_CHARS characters long.

    三层消毒，顺序不可换：先按空白折叠成单行（消除换行/回车/制表符造成的
    结构突破），再中和段落标记，最后截断——截断只删尾部字符、不会重新引入
    换行，所以放在最后仍保证单行。

    段落标记为什么选「换成形近括号〔〕」而不是删除或零宽分隔：删除会丢信息，
    「用户喜欢【洛天依】这首歌」会变成「用户喜欢洛天依这首歌」，括号承载的
    「这是作品名」提示一并消失；零宽字符（U+200B）不可见，复制传播时容易丢失，
    部分 tokenizer 会忽略或额外切分，消毒效果不可审计；形近括号保留了括号语义
    与全部正文字符，只让字形不再等于 harness 的段落标记，属「不丢信息、只破坏
    结构歧义」。

    列表前缀 "- " 不单独中和：单行化后正文里的 "- " 不可能出现在行首（bullet
    前缀由渲染器自己加），伪造列表项只会退化成同一条 bullet 内部的普通文本。
    """
    flat = " ".join(text.split())
    return flat.translate(_MARKER_TRANSLATION)[:_MAX_FACT_CHARS]


def format_memory_prompt(facts: list[MemoryFact]) -> str:
    """Render facts into an extra_system snippet for the harness.

    Contract: MemoryFact list in -> str out; empty list yields "" so the
    harness can concatenate unconditionally. The output has exactly
    2 + len(facts) lines: a title, one instruction line, then one bullet per
    fact. Fact bodies are sanitized by _sanitize_fact() before rendering.

    面向 LLM 的文本用中文全角标点，与 BASE_SYSTEM_PROMPT 文风一致；只注入
    fact 正文，存储层元数据（fact_id/session_id/scope）不进 prompt。标题行同时
    声明「程序提供」来源与不确定时的应对，呼应人设 prompt 的真实边界段，降低
    模型把记忆当当前对话内容编造下去的风险。

    消毒是安全边界而不是美观处理：这段文本最终被拼进 system prompt，记忆正文
    若能改写行结构（换行、伪造【…】段落标记、伪造 "- " 列表项），就等于让
    落库文本获得与 BASE_SYSTEM_PROMPT 同级的指令权重；scope="global" 时该
    注入会跨所有后续会话持久生效。因此「行数 == 2 + len(facts)」与「除标题行
    外没有任何一行以【开头」是本函数对外承诺的不变量。
    """
    if not facts:
        return ""
    lines = "\n".join(f"- {_sanitize_fact(item.fact)}" for item in facts)
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
