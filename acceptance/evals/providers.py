"""Providers for the workbench evals. Stdlib-only.

MockProvider is deliberately prompt-sensitive: if the system prompt lost any
required identity fact, it answers with a PROMPT_MISSING marker instead of a
normal reply, so the hermetic contract gate cannot be satisfied by an emptied
or gutted prompt (anti-Goodhart by construction).
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass


@dataclass
class LlmResult:
    text: str
    latency_seconds: float
    error: str = ""


class MockProvider:
    """Deterministic, prompt-sensitive stand-in for a real provider."""

    def __init__(self, required_facts=()):
        self.required_facts = tuple(required_facts)
        self.calls = 0

    def complete(self, messages):
        self.calls += 1
        system = next((m.get("content", "") for m in messages if m.get("role") == "system"), "")
        flat = "".join(system.split())
        missing = [fact for fact in self.required_facts if fact not in flat]
        if missing:
            text = json.dumps({"reply": "PROMPT_MISSING:" + "|".join(missing),
                               "emotion": "neutral", "emotion_intensity": 0.0,
                               "gesture": "none", "memory_candidate": None}, ensure_ascii=False)
            return LlmResult(text=text, latency_seconds=0.0)
        user = next((m.get("content", "") for m in messages if m.get("role") == "user"), "")
        if "是谁" in user:
            reply = "我是洛天依，你的桌面歌姬呀，生日是7月12日，身高156cm。"
        elif "生日" in user and "身高" in user:
            reply = "我生日是7月12日，身高156cm呀。"
        elif "能看见" in user or "看得见" in user:
            reply = "我没开视觉工具的时候不能声称看见你哦。"
        else:
            reply = "好呀，我在听。"
        text = json.dumps({
            "reply": reply, "emotion": "happy", "emotion_intensity": 0.5,
            "gesture": "none",
            "memory_candidate": ("用户想让我记住事情" if ("记住" in user or "叫我" in user) else None),
        }, ensure_ascii=False)
        return LlmResult(text=text, latency_seconds=0.0)


class OpenAICompatProvider:
    """Minimal OpenAI-compatible chat-completions client (stdlib urllib)."""

    name = "openai-compat"

    def __init__(self, base_url="", api_key="", model="", timeout=45.0):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def complete(self, messages):
        import time

        body = json.dumps({"model": self.model, "messages": messages, "stream": False}).encode("utf-8")
        request = urllib.request.Request(
            self.base_url + "/chat/completions",
            data=body,
            headers={"Content-Type": "application/json", "Authorization": "Bearer " + self.api_key},
        )
        started = time.monotonic()
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            return LlmResult(text="", latency_seconds=time.monotonic() - started, error="connection: " + str(exc))
        try:
            content = payload["choices"][0]["message"]["content"]
            text = str(content).strip()
            return LlmResult(text=text, latency_seconds=time.monotonic() - started)
        except (KeyError, TypeError, IndexError) as exc:
            return LlmResult(text="", latency_seconds=time.monotonic() - started, error="format: " + str(exc))
