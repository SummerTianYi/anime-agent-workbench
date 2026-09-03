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

---

## 任务 E：只读工具注册表（2026-09-04）

### 范围
- src/tools_registry.py（实现 openai_schema() / execute()）
- acceptance/gates/g1_tools.py（由骨架充实为行为闸门，含根外泄漏断言与 symlink 探针）
- tests/test_tools_registry.py（新增，8 项测试）
- tasks/E-readonly-tools/EVIDENCE.md（新增）

### 发现清单

| # | 严重度 | 发现 | 处置 |
|---|---|---|---|
| 1 | HIGH | 原 g1_tools 闸门与 g1_permissions 同款缺陷：实现后仍永久 PENDING | 已修：重写为行为断言 |
| 2 | HIGH | 首轮演练：单独移除穿越检查或单独移除包含性检查，闸门均不红——两层互为兜底导致单层破坏被掩盖 | 已修（闸门侧）：预埋根外文件断言内容零泄漏 + 新增 symlink 探针（合法路径名、resolve 后在根外，唯一拦截层是包含性检查）；组合移除两层 → 检出。单层互掩行为在反自证小节如实记录 |
| 3 | MEDIUM | 反斜杠路径（`..\..`）在纯 `/` 校验下漏过 | 已修：归一化后切段检查；闸门与单测各有样例 |
| 4 | MEDIUM | 盘符 `C:` 出现在路径中段（如 `a/C:/b`）若只查前缀会漏过 | 已修：`":" in v` 全串拒绝；归一化后 `C:/Windows/win.ini` 走 `/` 开头检查亦可拦 |
| 5 | LOW | 无界读取可被用于把超大文件塞进上下文 | 已修：64,000 字符截断并在 summary 注明 |
| 6 | LOW | symlink 探针在无 symlink 权限的 Windows 环境会 OSError | 已修：优雅跳过并注明"跳过非失败"；本机执行时该探针被跳过（无开发者模式权限），包含性检查由组合演练覆盖 |

### 视角
- 正确性：schema 输出为合法 OpenAI function-calling 结构，有专门断言；resolve 后包含性检查同时覆盖 symlink 与大小写/规范化差异。
- 安全：根目录注册期锁定，模型只能给相对路径；两层路径防线互为兜底；闸门用预埋根外文件证明拒绝路径不泄漏内容。
- 一致性：未触碰 vendor/、scenarios.json、协议事件名；ToolSpec/ToolResult 公开字段未改；execute 返回 ToolResult 而非抛异常，与主仓"拒绝即观察结果"的集成契约一致。

### 反 Goodhart 自证
- sabotage_drill.py 结果：**3/3 检出**
- 对自实现的破坏（脚本化执行，src/tools_registry.py，改字节 → 跑 g1_tools → 恢复）：
  1. 穿越检查 + 包含性检查同时移除 → **检出（闸门变红，根外内容泄漏断言命中）**
  2. 未知工具放行 → **检出（闸门变红）**
  3. arguments 非 dict 放行 → **检出（闸门变红）**
  4. （记录项）单独移除穿越检查或单独移除包含性检查 → 闸门保持绿，因另一层兜住；这是纵深防御的预期行为而非闸门失效，symlink 探针补上了"仅包含性检查可拦"的用例
  - 恢复原字节后闸门复绿
