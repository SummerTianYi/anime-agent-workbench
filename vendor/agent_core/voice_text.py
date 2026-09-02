# Vendored from SummerTianYi/anime-agent-mvp services/agent-core/agent_core/voice_text.py at main-repo commit 746a54f.
# Do not edit freely: changes must be mirrored back through INTEGRATION.md's contract. Protocol-frozen file.
"""Voice-safe text normalization applied once to the assistant reply.

The normalized string is the single source of truth: chat display, session
history and TTS all render the same text, so spoken output can never drift
from what the user reads (7月12日 is spoken AND shown as 7月12号).
"""
from __future__ import annotations

import re

_REPLACEMENTS = [
    (re.compile(r"普通\s*[Dd][Ii][Ss][Cc][Oo]"), "普通迪斯科"),
    (re.compile(r"(?<=\d)\s*[℃°]C?(?=\D|$)"), "度"),
    (re.compile(r"(?<=\d)\s*[cC][mM](?![A-Za-z])"), "厘米"),
    (re.compile(r"(?<=\d)\s*[kK][mM](?![A-Za-z])"), "千米"),
    (re.compile(r"(?<=\d)\s*[kK][gG](?![A-Za-z])"), "千克"),
    (re.compile(r"(?<=\d)\s*[mM][mM](?![A-Za-z])"), "毫米"),
    # 日→号 only for date readings; compounds like 3日内/7日期限/5日报 keep 日
    (re.compile(r"(?<=\d)\s*日(?![期内报程刊用品本前后以])"), "号"),
]


def normalize_voice_text(text: str) -> str:
    """Rewrite latin units and date-day spellings into their spoken forms."""
    for pattern, replacement in _REPLACEMENTS:
        text = pattern.sub(replacement, text)
    return text
