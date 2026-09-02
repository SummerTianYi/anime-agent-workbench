# 集成契约（主仓 ↔ 工作台）

## 分工

- **主仓**（anime-agent-mvp）：产品真身。协议、Godot、语音、真机验收归主仓侧（本机 Windows + RTX 5060 + 已训练声线）。
- **工作台**（本仓库）：异地 agent 的任务包 + 验收闸门 + 证据制度。远端 agent 只在这里开发，不接触主仓设备。

## 交付与并回流程

1. 远端 agent 完成任务包 → `run_all.py --strict` 全绿 → 演练 3/3 → ADVERSARIAL_REVIEW.md 完整 → evidence/ 有 --strict 证据 + 演练证据 → push 到本仓库（默认分支）。
2. 主仓侧（本机）拉取工作台仓库，**复跑同一套闸门**（run_all --strict + 每轮 3 次）+ 主仓 112 项单测 + 真机 E2E，全过才并回主仓。
3. 并回时按 `main-repo-target:` 头映射文件：src/prompt_persona/system_prompt.py → services/adopted...
