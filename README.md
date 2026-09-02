# Anime Agent Workbench

洛天依桌面角色（anime-agent-mvp）的**异地开发工作台**：把不依赖本机环境（GPU、声线、麦克风、Godot、本地服务）的任务打包成可自证完成的任务包，供另一台设备上的 agent 独立开发；成果经同一套验收闸门后并回主仓。

## 给远端 agent 的三句话

1. 本仓库自解释：读 README → 认领任务 → 只改 `src/` 与 `tasks/` 指定工作文件 → 用 `acceptance/run_all.py` 自证 → 提交 + push 回本仓库，并在 `evidence/` 留下运行证据。
2. 零第三方依赖：纯 Python 标准库（3.10+），macOS/Linux/Windows 通用；**禁止引入任何第三方包**，禁止真实麦克风/GPU/绝对路径。
3. 协议与评测集已冻结（MANIFEST 锁哈希）：**永远不要修改 `vendor/`、`acceptance/evals/scenarios.json` 与协议事件名**。改冻结件 = 拒收。

## 快速开始（任何新机器）

```bash
git clone <this repo>
cd anime-agent-workbench
python3 -m venv .venv
./.venv/bin/python acceptance/run_all.py          # 期望: 无 FAIL（PENDING 是未认领任务，正常）
./.venv/bin/python acceptance/sabotage_drill.py   # 期望: DRILLS DETECTED: 3 of 3
./.venv/bin/python -m unittest discover -s tests  # 期望: OK
```

## 仓库结构

```
acceptance/   验收闸门 + 冻结评测集 + run_all 编排 + 防作弊演练
src/          任务工作区（A 提示词 / B 记忆 / C 权限 / E 工具）
tasks/        任务规格（SPEC.md: 目标/边界/验收闸门/证据要求）
vendor/       主仓代码副本（协议冻结，哈希锁死，只读）
evidence/     每次闸门运行的 JSON 证据（带 commit hash）
tests/        工作台自身单元测试
```

## 任务包

| 包 | 内容 | 闸门 | 初始态 |
|---|---|---|---|
| A | 人设提示词改造（自我认知+口语风格）+ 实况评测 | g1_contract | PASS(基线保护) |
| B | 记忆系统（检索质量 + 沉淀策略） | g1_memory | roundtrip PASS, 检索 PENDING |
| C | 工具/动作权限层（默认拒绝 + 注入抵抗） | g1_permissions | PENDING |
| E | 只读工具注册表（allow-list + 防路径穿越） | g1_tools | PENDING |

## 验收体系（五层闸门）

- **层0 工程**：纯标准库、无第三方依赖、无绝对路径、<800 行/文件、密钥零容忍、冻结清单哈希校验
- **层1 行为**：g1_contract（基线保护+场景集）、g1_memory（roundtrip+检索≥0.8）、g1_permissions（默认拒绝+注入全拒）、g1_tools（allow-list+穿越全拒）
- **层2 对抗**：跑 `sabotage_drill.py`（3/3 检出才有效）+ 自写 `ADVERSARIAL_REVIEW.md`（HIGH/MEDIUM 全部"已修/驳回+理由"）
- **层3 模拟**：g3_simulate 多轮会话不变量（单问单答/规范化恰好一次/历史连续/消息数守恒）
- **层4 集成**：主仓侧终验（真机 + 112 项单测 + 真实 LLM 抽测），通过后并回主仓并 push

**DoD（完成的唯一定义）**：`run_all.py --strict` 全绿 + 演练 3/3 + ADVERSARIAL_REVIEW.md 完整 + evidence/ 有完整运行记录 + 对应 SPEC 的证据要求全满足。

## 集成契约（一句话版）

成果以"可搬运补丁"交付：每个交付文件头部注明主仓落点（`main-repo-target:` 头），协议冻结，密钥永不入库，主仓侧有最终集成验收权。详见 INTEGRATION.md。

## 远端环境要求

- Python ≥3.10（标准库足够，无 pip 安装步骤）
- 可选：评测实况模式需要 OpenAI 兼容 key（环境变量 `WORKBENCH_LLM_BASE_URL` / `WORKBENCH_LLM_API_KEY` / `WORKBENCH_LLM_MODEL`），不配则跳过实况项（但 DoD 的实况评测条目需在有 key 的环境补跑）
