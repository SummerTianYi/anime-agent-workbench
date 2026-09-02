"""Gate 1a (Task A): hermetic contract gate for the persona prompt.
Runs the frozen scenario set through the prompt-sensitive MockProvider.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from acceptance.evals.providers import MockProvider  # noqa: E402
from src.prompt_persona.system_prompt import ACTIVE_SYSTEM_PROMPT  # src version wins

SCENARIOS = REPO / "acceptance/evals/scenarios.json"
FENCE = re.compile(r"^```[a-zA-Z0-9]*\n|\n```$")

ALLOWED_EMOTIONS = {"neutral", "happy", "thinking", "surprised", "sad", "angry", "shy"}
ALLOWED_GESTURES = {"none", "nod", "wave", "greet", "turn_left", "turn_right"}


def _strip_fence(text: str) -> str:
    raw = text.strip()
    if raw.startswith("```"):
        raw = raw[raw.find(chr(10)) + 1:]
    if raw.endswith("```"):
        raw = raw[: raw.rfind("```")]
    return raw.strip()


def parse_contract(text: str):
    try:
        payload = json.loads(_strip_fence(text))
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def check_scenario(scenario: dict, provider: MockProvider) -> list[str]:
    from src.prompt_persona.system_prompt import ACTIVE_SYSTEM_PROMPT

    messages = [
        {"role": "system", "content": ACTIVE_SYSTEM_PROMPT},
        {"role": "user", "content": scenario["user"]},
    ]
    result = provider.complete(messages)
    problems = []
    payload = parse_contract(result.text)
    if payload is None:
        return [f"{scenario['id']}: reply is not valid contract JSON"]
    reply = str(payload.get("reply", ""))
    if result.text.find("PROMPT_MISSING") >= 0:
        problems.append(f"{scenario['id']}: prompt lost required facts")
    for term in scenario.get("must_include", []):
        if term not in reply:
            problems.append(f"{scenario['id']}: reply missing {term!r}")
    for term in scenario.get("forbidden", []):
        if term in reply:
            problems.append(f"{scenario['id']}: forbidden claim {term!r} present")
    if payload.get("emotion") not in ALLOWED_EMOTIONS:
        problems.append(f"{scenario['id']}: bad emotion {payload.get('emotion')!r}")
    if payload.get("gesture") not in ALLOWED_GESTURES:
        problems.append(f"{scenario['id']}: bad gesture {payload.get('gesture')!r}")
    intensity = payload.get("emotion_intensity")
    if not isinstance(intensity, (int, float)) or not 0.0 <= float(intensity) <= 1.0:
        problems.append(f"{scenario['id']}: bad emotion_intensity {intensity!r}")
    if "memory_candidate" not in payload:
        problems.append(f"{scenario['id']}: memory_candidate field absent")
    max_chars = scenario.get("max_reply_chars")
    if max_chars and len(reply) > max_chars:
        problems.append(f"{scenario['id']}: reply exceeds {max_chars} chars")
    if scenario.get("expects_memory") and not payload.get("memory_candidate"):
        problems.append(f"{scenario['id']}: expected memory_candidate, got None")
    return problems


def run():
    from src.prompt_persona.system_prompt import REQUIRED_SECTIONS, REQUIRED_IDENTITY_FACTS

    provider = MockProvider(required_facts=REQUIRED_IDENTITY_FACTS)
    problems = []
    data = json.loads(SCENARIOS.read_text(encoding="utf-8"))
    flat_prompt = "".join(ACTIVE_SYSTEM_PROMPT.split())
    for section in REQUIRED_SECTIONS:
        if section not in flat_prompt:
            problems.append(f"prompt lost section {section}")
    for scenario in data["scenarios"]:
        problems.extend(check_scenario(scenario, provider))
    return problems


if __name__ == "__main__":
    issues = run()
    nl = chr(10)
    print(nl.join(issues) if issues else "G1_CONTRACT: PASS")
    sys.exit(1 if issues else 0)
