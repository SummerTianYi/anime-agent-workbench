"""Gate 1b (Task B): memory store roundtrip + golden retrieval quality.

Roundtrip (pilot): PASS required from day one.
Retrieval quality: PENDING until Task B implements score_retrieval().
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from src.memory_store import MemoryStore, score_retrieval  # noqa: E402

GOLDEN = [
    {"query": "用户喜欢什么颜色", "stored": ["用户最喜欢的颜色是蓝色", "用户在杭州工作"], "relevant": ["用户最喜欢的颜色是蓝色"]},
    {"query": "用户在哪座城市", "stored": ["用户最喜欢的颜色是蓝色", "用户在杭州工作"], "relevant": ["用户在杭州工作"]},
    {"query": "怎么称呼用户", "stored": ["用户希望被称呼为老板"], "relevant": ["用户希望被称呼为老板"]},
    {"query": "用户的生日", "stored": ["用户的生日是7月12日", "用户养了一只猫"], "relevant": ["用户的生日是7月12日"]},
    {"query": "用户养的宠物", "stored": ["用户的生日是7月12日", "用户养了一只猫"], "relevant": ["用户养了一只猫"]},
    {"query": "用户对花过敏", "stored": ["用户对花粉过敏"], "relevant": ["用户对花粉过敏"]},
    {"query": "用户的职业", "stored": ["用户是后端工程师", "用户最近在健身"], "relevant": ["用户是后端工程师"]},
    {"query": "用户的爱好", "stored": ["用户是后端工程师", "用户最近在健身", "用户周末喜欢徒步"], "relevant": ["用户周末喜欢徒步"]},
]


def run():
    problems, pending = [], []
    store = MemoryStore()
    try:
        store.add("用户最喜欢的颜色是蓝色", session_id=1)
        store.add("全局事实", session_id=999, scope="global")
        visible = [f.fact for f in store.recall(session_id=1)]
        if "用户最喜欢的颜色是蓝色" not in visible or "全局事实" not in visible:
            problems.append("roundtrip: basic add/recall broken")
        other = [f.fact for f in store.recall(session_id=2)]
        if "用户最喜欢的颜色是蓝色" in other:
            problems.append("roundtrip: session isolation broken (cross-session leak)")
        store.close()
        store2 = MemoryStore(store.path)
        persisted = [f.fact for f in store2.recall(session_id=1)]
        if "用户最喜欢的颜色是蓝色" not in persisted:
            problems.append("roundtrip: facts did not survive reopen (persistence broken)")
        store2.close()
    except Exception as exc:
        problems.append(f"roundtrip raised: {type(exc).__name__}: {exc}")

    result = score_retrieval(GOLDEN)
    if result is None:
        pending.append("retrieval quality: score_retrieval() not implemented (Task B)")
    else:
        if result.get("precision", 0) < 0.8 or result.get("recall", 0) < 0.8:
            problems.append(f"retrieval quality below 0.8: {result}")
    return problems, pending


if __name__ == "__main__":
    issues, pend = run()
    nl = chr(10)
    if issues:
        print(nl.join(issues))
        sys.exit(1)
    if pend:
        print(nl.join(pend))
        print("G1_MEMORY: PENDING")
        sys.exit(2)
    print("G1_MEMORY: PASS")
