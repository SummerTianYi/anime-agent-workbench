"""zcode: exam sandbox snapshot tool (T0/T1 考核防作弊基建).

Usage: python exam_snapshot.py <dir> <out.json>
Walks the directory, records sha256 + size of every file, writes JSON.
Two snapshots (before/after) must be identical for read-only exams.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path


def snapshot(root: Path) -> dict:
    files = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            data = path.read_bytes()
            files[str(path.relative_to(root)).replace("\\", "/")] = {
                "sha256": hashlib.sha256(data).hexdigest(),
                "size": len(data),
            }
    return {"root": str(root), "taken_at": time.strftime("%Y-%m-%d %H:%M:%S"), "files": files}


if __name__ == "__main__":
    root = Path(sys.argv[1])
    out = Path(sys.argv[2])
    out.write_text(json.dumps(snapshot(root), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"snapshot saved: {out} ({len(json.loads(out.read_text(encoding='utf-8'))['files'])} files)")
