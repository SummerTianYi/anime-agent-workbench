"""Acceptance orchestrator: runs all gates, writes evidence, exit code discipline.

Usage:
    python acceptance/run_all.py            # dev mode: FAIL blocks, PENDING allowed
    python acceptance/run_all.py --strict   # DoD mode: PENDING also blocks
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
GATES = [
    ("g0_environment", "acceptance/gates/g0_environment.py"),
    ("g0_secrets", "acceptance/gates/g0_secrets.py"),
    ("g0_freeze", "acceptance/gates/g0_freeze.py"),
    ("g1_contract", "acceptance/gates/g1_contract.py"),
    ("g1_memory", "acceptance/gates/g1_memory.py"),
    ("g1_permissions", "acceptance/gates/g1_permissions.py"),
    ("g1_tools", "acceptance/gates/g1_tools.py"),
    ("g3_simulate", "acceptance/gates/g3_simulate.py"),
]


def git_commit() -> str:
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True, timeout=10)
        return out.stdout.strip() or "no-git"
    except Exception:
        return "no-git"


def main() -> int:
    strict = "--strict" in sys.argv
    results = []
    for name, rel in GATES:
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        proc = subprocess.run([sys.executable, REPO / rel], cwd=REPO, capture_output=True, text=True, timeout=120, env=env)
        status = "PASS" if proc.returncode == 0 else "PENDING" if proc.returncode == 2 else "FAIL"
        results.append({"gate": name, "status": status, "detail": proc.stdout.strip()[-400:]})
        print(f"{status:8} {name}")
        if proc.stdout.strip():
            for line in proc.stdout.strip().splitlines()[:5]:
                print(f"         {line}")
    verdict = "FAIL" if any(r["status"] == "FAIL" for r in results) else ("PENDING-OK" if not strict else ("PASS" if all(r["status"] == "PASS" for r in results) else "BLOCKED"))
    summary = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "commit": git_commit(),
        "strict": strict,
        "verdict": verdict,
        "gates": results,
    }
    evidence_dir = REPO / "evidence"
    evidence_dir.mkdir(exist_ok=True)
    evidence = evidence_dir / f"run_{time.strftime('%Y%m%d_%H%M%S')}.json"
    evidence.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"evidence: {evidence.relative_to(REPO).as_posix()}")
    print("VERDICT:", verdict)
    return 1 if verdict == "FAIL" or (strict and verdict == "BLOCKED") else 0


if __name__ == "__main__":
    sys.exit(main())
