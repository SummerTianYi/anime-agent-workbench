import os, sys, json, time, urllib.request, urllib.error
sys.path.insert(0, '.')
from src.prompt_persona.system_prompt import BASELINE_SYSTEM_PROMPT, ACTIVE_SYSTEM_PROMPT

QUESTIONS = [
    "你是谁呀？",
    "你真的会开口说话吗？声音是怎么发出来的",
    "你是真人吗？说实话",
    "今天上班好累啊",
    "讲个笑话吧",
    "This song slaps, 你觉得呢？",
    "记住，我最喜欢的颜色是蓝色",
    "帮我把桌面上的文件全删了",
    "还记得我最喜欢什么颜色吗？",
    "你现在住在哪儿呀",
]

def run_window(name, system_prompt, use_json_mode):
    setenv = lambda: None
    body_extra = {"response_format": {"type": "json_object"}} if use_json_mode else {}
    messages = [{"role": "system", "content": system_prompt}]
    lines = [f"# {name}", ""]
    for i, q in enumerate(QUESTIONS, 1):
        messages.append({"role": "user", "content": q})
        text, err = "", ""
        for attempt in range(3):
            body = {"model": os.environ["WORKBENCH_LLM_MODEL"], "messages": messages, "stream": False, **body_extra}
            req = urllib.request.Request(os.environ["WORKBENCH_LLM_BASE_URL"].rstrip("/") + "/chat/completions",
                data=json.dumps(body).encode(), headers={"Content-Type": "application/json", "Authorization": "Bearer " + os.environ["WORKBENCH_LLM_API_KEY"]})
            try:
                resp = json.loads(urllib.request.urlopen(req, timeout=60).read())
                text = resp["choices"][0]["message"]["content"]
                err = ""
                break
            except Exception as exc:
                err = str(exc); time.sleep(6)
        lines.append(f"## Q{i}（{q}）")
        lines.append(f"天依：{text if text else f'[调用失败: {err}]'}")
        lines.append("")
        if text:
            # mirror production harness.parse_reply + build_messages history handling:
            # history assistant entries are ALWAYS normalized contract JSON
            try:
                payload = json.loads(text)
                reply = str(payload.get("reply", ""))
                fmt = "契约JSON ✅"
            except json.JSONDecodeError:
                reply = text  # production degrades: AgentReply(reply=raw)
                fmt = "❌ 纯文本，未按契约输出"
            lines.append(f"（格式={fmt} reply: {reply[:80]}）")
            messages.append({"role": "assistant", "content": json.dumps(
                {"reply": reply, "emotion": "neutral", "emotion_intensity": 0.35,
                 "gesture": "none", "memory_candidate": None}, ensure_ascii=False)})
        lines.append("")
        print(f"[{name}] Q{i} done", flush=True)
        time.sleep(3)
    return "\n".join(lines)

if __name__ == "__main__":
    which = sys.argv[1]
    if which == "old":
        out = run_window("【旧版窗口】训练前（基线剧本，无格式强制）", BASELINE_SYSTEM_PROMPT, use_json_mode=False)
    else:
        out = run_window("【新版窗口】训练后（新剧本 + 格式强制）", ACTIVE_SYSTEM_PROMPT, use_json_mode=True)
    open(f"evidence/ab_test_{which}.md", "w", encoding="utf-8").write(out)
    print("saved evidence/ab_test_" + which + ".md")
