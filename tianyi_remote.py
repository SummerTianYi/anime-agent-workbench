"""Remote control for the live Tianyi (websocket ui client).

Usage (run with main repo venv python):
  python tianyi_remote.py new-session          # open a new window, print conversationId
  python tianyi_remote.py ask <convId> <text>  # send one question into that window
Prints every event received; caller verifies chat.response + avatar.speak.
"""
from __future__ import annotations

import asyncio
import json
import sys

import websockets

URI = "ws://127.0.0.1:8765/ws"


async def main() -> None:
    mode = sys.argv[1]
    async with websockets.connect(URI, max_size=None) as ws:
        await ws.send(json.dumps({"type": "client.hello", "role": "ui"}))

        async def recv_until(match, timeout=120, quiet=45):
            """Collect events until one matching dict predicate arrives."""
            collected = []
            async def pump():
                try:
                    while True:
                        raw = await asyncio.wait_for(ws.recv(), timeout=quiet)
                        ev = json.loads(raw)
                        collected.append(ev)
                        if match(ev):
                            return
                except (asyncio.TimeoutError, websockets.ConnectionClosed):
                    return
            await asyncio.wait_for(pump(), timeout=timeout)
            return collected

        if mode == "new-session":
            await ws.send(json.dumps({"type": "session.new"}))
            events = await recv_until(lambda e: e.get("type") == "session.switched")
            for e in events:
                print(json.dumps(e, ensure_ascii=False))
            conv = next((e["conversationId"] for e in events if e.get("type") == "session.switched"), None)
            print(json.dumps({"conversationId": conv}, ensure_ascii=False))
            return

        if mode == "quiz":
            conv = int(sys.argv[2])
            questions = json.loads(sys.argv[3])
            failures = []
            for i, q in enumerate(questions, 1):
                rid = f"ui-quiz-{int(asyncio.get_event_loop().time()*1000)%10**9}-{i}"
                # drain stale buffered events from the previous answer first
                try:
                    while True:
                        await asyncio.wait_for(ws.recv(), timeout=0.5)
                except (asyncio.TimeoutError, websockets.ConnectionClosed):
                    pass
                await ws.send(json.dumps({"type": "chat.message", "text": q,
                                          "messageId": rid,
                                          "conversationId": conv}))
                events = await recv_until(
                    lambda e: e.get("type") == "avatar.speak" and e.get("request_id") == rid,
                    timeout=150)
                resp = next((e for e in events if e.get("type") == "chat.response"
                             and e.get("request_id") == rid), None)
                speaks = [e for e in events if e.get("type") == "avatar.speak"]
                if resp is None:
                    failures.append({"q": i, "reason": "no chat.response within 90s"})
                    print(json.dumps({"q": i, "FAIL": "no response"}, ensure_ascii=False), flush=True)
                    break
                reply = str(resp.get("text", ""))
                ok_text = len(reply) > 0 and reply.rstrip().endswith(("。", "！", "？", "～", "呀", "哦", "啦", "呢", "吧", "！", "~", "?", "…"))
                if not ok_text:
                    failures.append({"q": i, "reason": f"reply looks truncated: {reply[-40:]!r}"})
                if not speaks:
                    failures.append({"q": i, "reason": "no avatar.speak (TTS not dispatched)"})
                print(json.dumps({"q": i, "ok": resp is not None and ok_text and bool(speaks),
                                  "reply": reply[:60], "speak_events": len(speaks),
                                  "truncated": not ok_text}, ensure_ascii=False), flush=True)
                if failures:
                    break
                await asyncio.sleep(12)  # let her finish speaking before the next line
            print(json.dumps({"done": True, "failures": failures}, ensure_ascii=False))
            return

        if mode == "ask":
            conv = int(sys.argv[2])
            text = sys.argv[3]
            await ws.send(json.dumps({"type": "chat.message", "text": text,
                                      "messageId": f"ui-{int(asyncio.get_event_loop().time()*1000)%10**9}",
                                      "conversationId": conv}))
            events = await recv_until(
                lambda e: e.get("type") == "chat.response", timeout=90)
            for e in events:
                print(json.dumps(e, ensure_ascii=False))
            return


if __name__ == "__main__":
    asyncio.run(main())
