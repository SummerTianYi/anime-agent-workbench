# 任务 A：人设提示词改造（自我认知 + 口语风格）

## 目标
1. 自我认知：知道自己会开口说话、正在用 3D 模型陪伴用户，不冒充真人/通用 AI
2. 口语风格：自然、简洁、有温度，无客服腔、无排比堆砌、无 AI 套话
3. 中英措辞引导（语言路由本身由 TTS 引擎处理，提示词只管措辞）

## 工作文件
- src/prompt_persona/system_prompt.py（重写 ACTIVE_SYSTEM_PROMPT，基座在 vendor 里，勿改 vendor）

## 验收闸门
- g1_contract 必须保持全绿（基线保护：事实/契约/诚实守卫/记忆字段一项都不能丢）
- 评测集 checksum 冻结，改场景 = 拒收
- g0_freeze 绿（vendor 未被动过）

## 证据要求（写进 evidence/ 与 ADVERSARIAL_REVIEW.md）
1. run_all --strict 全绿证据 ×3 轮
2. 演练 3/3
3. 新旧提示词对比 + 改动理由逐条说明
4. 实况评测：配好 key 后跑 acceptance/evals/run_live.py（脚本待补：Task A 需先写），≥30 场景 ×3 轮，JSON 契约解析率 100%（硬门槛），自我认知清单 ≥95%，口语风格双评审 ≥90
