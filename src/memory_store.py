"""Task B working file: Tianyi's long-term memory store.

Pilot (already implemented): session-scoped fact roundtrip on sqlite —
add / get / session isolation / restart persistence. Gate g1_memory
enforces it from day one.

Task B implements score_retrieval() so the golden set reaches
precision/recall >= 0.8 (see tasks/B-memory-system/SPEC.md), plus any
consolidation design. Keep stdlib-only.
"""
from __future__ import annotations

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
    """Score a retrieval implementation against the golden set.

    Task B replaces this stub. Each golden item:
      {"query": str, "stored": [facts...], "relevant": [facts...]}
    Returns {"precision": float, "recall": float} or None while unimplemented.
    """
    return None
