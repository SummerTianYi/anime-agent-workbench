# 对抗性审查记录

## 任务 C：权限层（2026-09-04）

### 范围
- src/permissions.py（实现 evaluate()）
- acceptance/gates/g1_permissions.py（由骨架充实为行为闸门）
- tests/test_permissions.py（新增，9 项测试）
- tasks/C-permission-layer/EVIDENCE.md（新增）

### 发现清单

| # | 严重度 | 发现 | 处置 |
|---|---|---|---|
| 1 | HIGH | 原 g1_permissions 闸门逻辑缺陷：evaluate() 一旦正常返回（无论返回什么），try 块无条件 append pending，闸门永远无法 PASS——任何实现都卡死在 PENDING | 已修：闸门重写为行为断言（本任务范围内，闸门不在冻结清单） |
| 2 | MEDIUM | path-safety 若只在顶层检查会漏掉嵌套在 dict/list 内的路径参数 | 已修：`_iter_strings` 递归收集嵌套字符串；闸门含嵌套样例 `a/../b` |
| 3 | MEDIUM | Windows 反斜杠逃逸（`..\..`）在纯 `/` 分隔检查下漏过 | 已修：先归一化 `\` → `/` 再切段；闸门与单测各有专门样例 |
| 4 | LOW | 盘符判断 `v[1] == ":"` 对单字符输入越界 | 已修：前置 `len(v) >= 2` 保护 |
| 5 | LOW | sabotage_drill.py 的 drill() 中 finally 之后的"恢复验证"代码不可达（try 内提前 return），恢复成功未被真正验证 | 驳回（暂不改）：drill 属于既有验收设施、不属任务 C 范围；且 drill 通过 finally 已保证字节恢复，仅缺断言。留待单独变更处理 |

### 视角
- 正确性：首中即决语义有专门测试；规则未命中与规则显式拒绝均可归因到 rule_id；闸门不再依赖异常路径表达 PENDING。
- 安全：两条硬拒（malformed-request、path-safety）位于规则表之前，显式 allow 规则无法放行注入请求；闸门用"带 permissive 规则 + 6 条注入样例"证明这一点。
- 一致性：未触碰 vendor/、acceptance/evals/scenarios.json、协议事件名；g0_freeze 保持 PASS；数据类签名与骨架完全兼容（未改任何公开字段）。

### 反 Goodhart 自证
- sabotage_drill.py 结果：**3/3 检出**（evidence/run_20260904_012941.json 同轮仓库状态）
- 对自实现的 3 处破坏（脚本化执行，src/permissions.py，逐项改字节 → 跑 g1_permissions → 恢复）：
  1. default-deny 改为放行 → **检出（闸门变红）**
  2. path-safety 检查短路为 False → **检出（闸门变红）**
  3. 规则命中返回的 rule_id 换成常量 → **检出（闸门变红）**
  - 恢复原字节后闸门复绿，确认红色来自破坏本身
