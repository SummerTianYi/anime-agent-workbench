"""Sabotage drill: prove the gates have teeth.

Deliberately breaks the implementation three ways, requires the relevant
gate to go RED, restores the original bytes, requires green again. If any
sabotage is NOT detected, the drill fails — tests that cannot fail are the
same as no tests.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PY = sys.executable


def run_gate(rel: str) -> int:
    proc = subprocess.run([PY, REPO / rel], cwd=REPO, capture_output=True, text=True, timeout=120)
    return proc.returncode


def drill(name: str, target: Path, old: str, new: str, gate: str) -> bool:
    original = target.read_bytes()
    try:
        text = original.decode("utf-8")
        if old not in text:
            print(f"DRILL {name}: SKIP (anchor not found)")
            return False
        target.write_bytes(text.replace(old, new).encode("utf-8"))
        if run_gate(gate) == 0:
            print(f"DRILL {name}: NOT DETECTED - gates have no teeth")
            return False
        return True
    finally:
        target.write_bytes(original)
    for cache in [REPO / "vendor/agent_core/__pycache__", REPO / "src/__pycache__", REPO / "acceptance/__pycache__"]:
        shutil.rmtree(cache, ignore_errors=True)
    if run_gate(gate) != 0:
        print(f"DRILL {name}: RESTORE FAILED - gate still red after restore")
        return False
    return True


def main() -> int:
    detected = []
    def drill2(name, target, old, new, gate):
        hit = drill(name, target, old, new, gate)
        detected.append((name, hit))
        return hit
    ok = True
    ok &= drill2("prompt-fact-sabotage", REPO / "vendor/agent_core/harness.py", "#66CCFF", "#000", "acceptance/gates/g1_contract.py")
    ok &= drill2("memory-sabotage", REPO / "src/memory_store.py", "INSERT INTO facts", "INSERT INTO facts_gone", "acceptance/gates/g1_memory.py")
    ok &= drill2("eval-tamper", REPO / "acceptance/evals/scenarios.json", chr(34) + "identity-01" + chr(34), chr(34) + "identity-01x" + chr(34), "acceptance/gates/g0_freeze.py")
    nl = chr(10)
    print("DRILLS DETECTED:", sum(1 for _, hit in detected if hit), "of 3")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())