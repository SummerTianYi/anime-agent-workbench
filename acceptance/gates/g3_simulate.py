"""Gate 3: multi-turn simulated sessions with invariant checks.

A miniature chat loop (system prompt + harness parsing + sqlite history)
mirroring main-repo semantics: exactly one assistant reply per user turn,
reply normalized exactly once, history continuity, no orphan assistant turns.
"""
from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from acceptance.evals.providers import MockProvider  # noqa: E402
from acceptance.gates.g1_contract import parse_contract  # noqa: E402
from src.prompt_persona.system_prompt import ACTIVE_SYSTEM_PROMPT  # noqa: E402
from vendor.agent_core.voice_text import normalize_voice_text  # noqa: E402

USERS = ["你好", "今天好累啊", "记住，我最喜欢的颜色是蓝色", "你的生日和身高是多少？"]
SESSIONS = 10
TURNS = len(USERS)


def run():
    problems = []
    store = sqlite3.connect(":memory:")
    store.execute("CREATE TABLE messages (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id INT, role TEXT, content TEXT)")
    provider = MockProvider(required_facts=())
    for session in range(SESSIONS):
        history = []
        for turn in range(TURNS):
            user_text = USERS[turn]
            messages = [
                {"role": "system", "content": ACTIVE_SYSTEM_PROMPT},
                *history,
                {"role": "user", "content": user_text},
            ]
            result = provider.complete(messages)
            payload = parse_contract(result.text)
            if payload is None:
                problems.append(f"session{session}/turn{turn}: reply not valid contract JSON")
                continue
            spoken = normalize_voice_text(str(payload.get("reply", "")))
            if normalize_voice_text(spoken) != spoken:
                problems.append(f"session{session}/turn{turn}: normalize not idempotent")
            store.execute("INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)", (session, "user", user_text))
            store.execute("INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)", (session, "assistant", spoken))
            history.append({"role": "user", "content": user_text})
            history.append({"role": "assistant", "content": spoken})
    totals = store.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
    if totals != SESSIONS * TURNS * 2:
        problems.append(f"message count mismatch: {totals}")
    return problems


if __name__ == "__main__":
    issues = run()
    nl = chr(10)
    print(nl.join(issues) if issues else "G3_SIMULATE: PASS")
    sys.exit(1 if issues else 0)
