"""Task A working file: the active persona system prompt.

The baseline below is the current main-repo prompt (vendor copy). Task A
rewrites THIS file. Gates in acceptance/gates/g1_contract.py enforce the
invariants that must survive any rewrite:

- identity facts (洛天依 / #66CCFF / 7月12日 / 156cm / 音之精灵 天钿)
- a self-cognition block that keeps the "only hear after STT / cannot claim
  to see / cannot claim actions done" honesty rules
- the exact JSON output contract with the five documented fields

Prose may be reorganized freely; keep the section headings 【…】 so the
structure check can find them.
"""
from vendor.agent_core.harness import BASE_SYSTEM_PROMPT

ACTIVE_SYSTEM_PROMPT = BASE_SYSTEM_PROMPT

REQUIRED_SECTIONS = ("身份", "自我认知", "表达方式", "输出契约")
REQUIRED_IDENTITY_FACTS = ("洛天依", "#66CCFF", "7月12日", "156cm", "天钿")
REQUIRED_CONTRACT_FIELDS = ("reply", "emotion", "emotion_intensity", "gesture", "memory_candidate")
