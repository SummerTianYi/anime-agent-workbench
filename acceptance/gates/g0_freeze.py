"""Gate 0c: integrity freeze. sha256-locks vendor files and the frozen eval set.

Any edit to vendor/ or the scenario set without regenerating the manifest is a
gate failure — protocol and eval tampering are rejection conditions.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MANIFEST = REPO / "acceptance" / "MANIFEST.json"
FREEZE_TARGETS = [
    "vendor/agent_core/harness.py",
    "vendor/agent_core/song_catalog.py",
    "vendor/agent_core/voice_text.py",
    "vendor/agent_core/data/luotianyi_original_songs.json",
    "acceptance/evals/scenarios.json",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run():
    if not MANIFEST.is_file():
        return ["acceptance/MANIFEST.json missing - run: python -m acceptance.gates.g0_freeze --update"]
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    problems = []
    for rel in FREEZE_TARGETS:
        path = REPO / rel
        if not path.is_file():
            problems.append(f"{rel}: missing")
            continue
        expect = manifest.get(rel)
        if expect is None:
            problems.append(f"{rel}: not in manifest")
        elif expect != sha256(path):
            problems.append(f"{rel}: content drifted from frozen manifest")
    return problems


if __name__ == "__main__":
    if "--update" in sys.argv:
        manifest = {rel: sha256(REPO / rel) for rel in FREEZE_TARGETS if (REPO / rel).is_file()}
        MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print("MANIFEST updated:", len(manifest), "entries")
        sys.exit(0)
    issues = run()
    nl = chr(10)
    print(nl.join(issues) if issues else "G0_FREEZE: PASS")
    sys.exit(1 if issues else 0)
