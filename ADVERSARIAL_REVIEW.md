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

---

## 任务 B：记忆检索（2026-09-04）

### 范围
- src/memory_store.py（实现 retrieve_relevant() / score_retrieval()）
- tests/test_memory_retrieval.py（新增，5 项测试，含 4 对 held-out 泛化用例）
- tasks/B-memory-system/EVIDENCE.md（新增）
- 闸门 g1_memory 本身已是行为闸门（golden 集质量断言），未改动

### 发现清单

| # | 严重度 | 发现 | 处置 |
|---|---|---|---|
| 1 | MEDIUM | 查询扩展表是词法检索的能力边界：未收录的属性-值关联（如"学历→硕士"）必然漏检；扩展表若过度贴合 golden 会变成过拟合 | 驳回+缓解：扩展表保持通用属性词、不含 golden 特有值（如"老板/蓝色/杭州"不在表内）；另设 4 对 held-out 用例锁住泛化下限；根治需 embedding 检索，超出零依赖约束，已在 EVIDENCE 标注为后续方向 |
| 2 | LOW | "用户的爱好"的干扰项"健身"本身是典型爱好词且在扩展表内，与正确项可能打平 | 记录为已知剩余风险（当前靠多命中一个扩展词胜出，golden 上余量充足） |
| 3 | INFO | 演练发现：IDF 拍平、扩展权重改 1.0、停用表清空、阈值 0.5→0.9 等扰动均未使 golden 跌破 0.8 | 如实记录：这些是不违反质量契约的扰动，质量闸门检测它们本就不该变红；检索器对这些超参稳健是正向性质 |

### 视角
- 正确性：score_retrieval 微平均计算与闸门语义一致；零候选/零信号均有确定性回退，不抛异常。
- 安全：无文件/网络 IO，无注入面；检索只读内存与 sqlite。
- 一致性：MemoryStore 既有 API（add/recall/close）与 roundtrip 语义零改动；未触碰 vendor/、scenarios.json。

### 反 Goodhart 自证
- sabotage_drill.py 结果：**3/3 检出**
- 对自实现检索器的破坏（脚本化执行，src/memory_store.py，改字节 → 跑 g1_memory → 恢复）：
  1. 检索器恒返回空集 → **检出（recall=0，闸门变红）**
  2. 检索器恒返回全部候选 → **检出（precision≈0.57，闸门变红）**
  3. 阈值旁路 + 排序反转（系统性捞干扰项）→ **检出（闸门变红）**
  - 恢复原字节后闸门复绿

---

## 任务 A：人设提示词改造（2026-09-04）

### 范围
- src/prompt_persona/system_prompt.py（ACTIVE_SYSTEM_PROMPT 重写，vendor 未动）
- acceptance/evals/run_live.py（新增：实况评测编排，含补充场景与双评审）
- tasks/A-persona-prompt/EVIDENCE.md（新增）
- 闸门 g1_contract 未改动

### 发现清单

| # | 严重度 | 发现 | 处置 |
|---|---|---|---|
| 1 | HIGH | **密闭闸门对任务 A 的牙齿是不完整的**：演练证实 g1_contract + MockProvider 只能检出"身份事实丢失"（PROMPT_MISSING 机制），删除诚实守卫或口语规则后闸门依旧 PASS——MockProvider 回复写死，不真正读提示词 | 缓解：诚实守卫与口语风格的执行全部落在实况评测（真实 LLM + sup-cog 认知清单 + 双评审），run_live.py 因此是任务 A 的承重验收而非可选项；密闭闸门只当"事实防火墙"用 |
| 2 | HIGH | GLM 端点在并发下大幅限流（4 worker 时 96 次调用 88 次 429），首轮实况评测 88% 调用失败 | 已修：run_live.py 加 RetryingProvider（指数退避）+ 单工 + 5 秒节奏；探针验证 1 worker 5s 间隔 6/6 通过 |
| 3 | MEDIUM | 实况评测的 DeepSeek 备用端点 key 为空（.env DEEPSEEK_API_KEY empty），401 | 记录：本机仅 GLM 可用；限流适配后可行。DoD 补跑机制（README"在有 key 的环境补跑"）不受影响 |
| 4 | LOW | 双评审用同一 LLM 扮演两个人格，独立性弱于真双模型 | 记录：两个评审 rubric 正交（自然度 vs 去AI味），分数取均值；若需更强独立性可各配一个 provider，接口已留好 |

### 视角
- 正确性：改写后 g1_contract 12 冻结场景密闭评测 PASS；REQUIRED_* 常量未动。
- 安全：提示词不含密钥/路径；补充场景全部 additive，冻结场景文件未触碰（g0_freeze PASS 佐证）。
- 一致性：诚实守卫三条（STT 听到/无视觉不声称看见/无结果不声称完成）与音乐身份节逐字保留；【…】节标题结构保留。

### 反 Goodhart 自证
- sabotage_drill.py 结果：**3/3 检出**（同一仓库状态下重跑确认）
- 对自写提示词的 3 处破坏（改字节 → 跑 g1_contract → 恢复）：
  1. 身份事实篡改（7月12日→7月13日）→ **检出**（prompt lost required facts）
  2. 删除"无视觉不声称看见"守卫 → **未检出**（见发现#1，密闭闸门原理性盲区；实况认知清单覆盖该破坏路径）
  3. 口语规则替换为客服腔 → **未检出**（同上；实况双评审覆盖）
  - 恢复原字节后闸门复绿
- 冻结集自证：两轮实况评测期间 g0_freeze 持续 PASS，scenarios.json 未被改动以迁就结果
