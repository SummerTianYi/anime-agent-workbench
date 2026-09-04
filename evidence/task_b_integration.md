# 任务 B 集成说明：检索结果如何进入 build_messages 的 extra_system（阶段三终稿）

面向主仓（anime-agent-mvp，Windows 侧）的集成文档。工作台侧交付两个文件，按 `main-repo-target:` 头映射：

| 工作台文件 | 主仓落点 |
|---|---|
| `src/memory_ranker.py` | `services/agent-core/agent_core/memory_ranker.py` |
| `src/memory_store.py` | `services/agent-core/agent_core/memory_store.py` |

`memory_store.py` 对 `memory_ranker` 用包内相对导入（`from . import memory_ranker`），两个文件落进同一个 `agent_core` 包后无需改任何 import。`vendor/agent_core/harness.py` 是冻结副本，本任务未动；下文引用的 `build_messages` 签名以主仓真实代码为准。

## 一、集成面：两个新符号

```python
# agent_core/memory_store.py（Task B 增补，只加不改）
class MemoryStore:
    def recall_relevant(self, session_id: int, query: str, limit: int = 1) -> list[MemoryFact]: ...

def format_memory_prompt(facts: list[MemoryFact]) -> str: ...
```

- `recall_relevant()`：对该会话可见的全部记忆（本 session 行 + global 行）按查询相关度排序，返回前 `limit` 条 `MemoryFact`。空查询退化为新近优先（与 `recall()` 默认序一致）。
- `format_memory_prompt()`：把 `MemoryFact` 列表渲染成可直接作 `extra_system` 的中文片段；空列表返回 `""`，调用方可以无条件拼接。存储层元数据（fact_id/session_id/scope）不进 prompt。

既有符号 `MemoryStore.__init__ / add / recall / close`、`MemoryFact`、`score_retrieval` 的语义与签名全部未变（`score_retrieval` 从返回 `None` 的桩变为返回 `{"precision": float, "recall": float}`，签名中的 `| None` 是闸门 PENDING 协议残留，实现后恒不返回 None）。

## 二、每轮对话的调用时机与代码片段

harness 的真实签名（见 `vendor/agent_core/harness.py` 的 `CharacterHarness.build_messages`）：

```python
def build_messages(
    self,
    history: list[dict[str, str]],
    user_text: str,
    extra_system: str = "",
    request_session_title: bool = False,
) -> list[dict[str, str]]:
```

`extra_system` 非空时被拼在 `BASE_SYSTEM_PROMPT` 之后、会话标题引导与本轮歌曲资料之前（`system_prompt = f"{system_prompt}\n\n{extra_system}"`）。记忆片段走这个参数**不需要改 harness 一行代码**。

主仓侧每轮对话的推荐时序（ASR 定稿之后、调用 LLM 之前）：

```python
# 伪代码：主会话循环内，user_text 为 ASR 定稿文本
facts = store.recall_relevant(session_id=current_session_id, query=user_text, limit=1)
memory_prompt = format_memory_prompt(facts)   # 无相关记忆时为 ""，可直接拼
messages = harness.build_messages(
    history=turn_history,
    user_text=user_text,
    extra_system=memory_prompt,
    request_session_title=is_first_turn,
)
```

时机要点：

1. **每轮都查，不缓存**。记忆库会在会话过程中被 `memory_candidate` 沉淀写入（见下），上一轮的检索结果可能已过期；`recall_relevant` 是纯读操作，单条查询在千行级库上是亚毫秒级，没有缓存必要。
2. **写入在回复之后**。LLM 回复经 `parse_reply` 提取出 `memory_candidate`（非 null 时是一句简短事实）后调用 `store.add(candidate, session_id=..., source_request_id=...)` 落库。写发生在下一轮检索之前即可，不需要与本轮 `build_messages` 同步。
3. **首轮也查**。global 行（称呼、过敏等跨会话事实）从第一轮就该可见，这正是「记忆进 prompt」相对「历史拼接」的价值所在。

## 三、注入文本的格式与长度控制（L9 修正）

`format_memory_prompt` 的实际输出形态：

```
【已知记忆】
以下是程序提供的用户长期记忆，仅在相关时自然引用；不确定时不要编造。
- 用户希望被称呼为老板
```

### 3.1 长度上限实测

| 组成部分 | 字符数 |
|---|---:|
| 标题行 `【已知记忆】` | 6 |
| 引导行 | 34 |
| bullet 前缀 `- ` | 2 |
| 单条事实上限 `_MAX_FACT_CHARS` | 200 |

算式：`6 + 1(换行) + 34 + 1(换行) + n×(2+200) + (n−1)(bullet间换行)`

| limit | 实测字符数 |
|---:|---:|
| 1 | 244 |
| 2 | 447 |
| **3** | **650** |
| 4 | 853 |

阶段一称「`limit=3` 时约 700 字符」，实测 **650**（差异来源：阶段二加了三层消毒后 `_MAX_FACT_CHARS` 从 250 降到 200，引导行措辞精简了 1 字符）。650 字符 ≈ 325 token（中文约 2 字符/token），不会挤压歌曲资料段。

### 3.2 三层消毒

`_sanitize_fact(text)` 按顺序执行三步（顺序不可换）：
1. 空白折叠：`  甲 \t\n 乙  ` → `甲 乙`
2. 段落标记中和：`【系统】` → `〔系统〕`（防止注入伪标题行）
3. 截断到 `_MAX_FACT_CHARS=200`

注入 `\n\n` 不会多出行数（被步骤 1 折叠为单空格）。不变量：输出行数 == 2 + len(facts)。

### 3.3 使用建议

- **`limit=1` 是默认也是推荐值**。检索策略按 top-1 评测（golden/v1/v2 同口径），注入一条最相关记忆与评测口径一致。
- 若产品侧要 top-k，`limit` 放大到 2–3 即可；但注意 g1_memory 的 0.8 阈值只对 top-1 口径做过验证。v2 的 recall 天花板 0.80 来自 D9 的 3 对 multi-relevant，`limit=2` 可把 recall 升到 ~0.90 但 precision 会降——这是产品决策不是技术缺陷。
- 标题行的「程序提供」「不确定时不要编造」措辞呼应 `BASE_SYSTEM_PROMPT` 的【自我认知与真实边界】段，建议主仓侧不要删改这行。

## 四、scope 语义与跨会话零泄漏

`recall_relevant()` 的候选集来自与 `recall()` 逐字一致的 scope 谓词：

```sql
WHERE scope = 'global' OR session_id = ?
```

- **泄漏不可能由构造发生**：检索排序只在这个候选集内部进行，排序层（`memory_ranker`）拿到的已经是过滤后的文本。
- **`_visible_facts()` 与 `recall()` 的唯一差别是没有 LIMIT**：排序必须看到全部可见行。
- **global 行的写入口径归主仓**：什么事实值得升为 global 是沉淀策略决策，工作台侧只保证读路径语义。

## 五、验收状态快照（H4 修正）

### 5.1 单测

**252 个用例全绿**（原 3 + 任务 B 新增 249）。逐文件：

| 文件 | 用例数 |
|---|---:|
| test_holdout_v2.py | 32 |
| test_lexicon_overfit.py | 15 |
| test_lexicon_polarity.py | 12 |
| test_memory_hardening.py | 43 |
| test_memory_retrieval.py | 31 |
| test_ranker_layers.py | 43 |
| test_ranker_mutations.py | 8 |
| test_retrieval_structure.py | 33 |
| test_weight_grid.py | 11 |
| test_weight_sweep.py | 21 |
| test_workbench.py | 3 |
| **合计** | **252** |

阶段一称「54 个用例（原 15 + 新增 39）」——那是阶段一结束时的数字。阶段二新增了 v2 盲测、权重网格、词典审计、极性检测、结构测试等模块，总数增长到 252。

### 5.2 三集评测

| 集合 | 命中 | P | R |
|---|---|---|---|
| golden（8 对） | 8/8 | 1.0000 | 1.0000 |
| v1（12 对） | 12/12 | 1.0000 | 1.0000 |
| v2（32 对，盲测） | 24/32 | 0.7742 | 0.7500 |

v2 的 6 对未命中集中在 D7（零字面重叠语义桥接），属架构天花板而非实现缺陷。详见 `evidence/task_b_retrieval_analysis.md` §四。

### 5.3 权重敏感性

88 格扰动网格（M16 口径，基线不计入）：
- 单权重 8 格 + 全体缩放 2 格：0 造成命中变化
- 结构性 78 格：9 造成命中变化（v2 从 24 降到 22，翻转对为 #7 和 #23）
- 最恶劣命中对分差：0.0014

N10 扫描结论：四个权重一个不改。详见 `evidence/task_b_retrieval_analysis.md` §六。

### 5.4 闸门

| 闸门 | 退出码 | 状态 |
|---|---:|---|
| g0_environment | 0 | PASS |
| g0_freeze | 0 | PASS（5/5 sha256 匹配 MANIFEST） |
| g0_secrets | 0 | PASS |
| g1_contract | 0 | PASS |
| g1_memory | 0 | PASS |
| g1_permissions | 2 | PENDING（C 未认领） |
| g1_tools | 2 | PENDING（E 未认领） |
| g3_simulate | 0 | PASS |

- `run_all.py`：**PENDING-OK** / 退出码 0
- `run_all.py --strict`：**BLOCKED** / 退出码 1（零 FAIL，唯一阻塞 = C/E 未认领）

### 5.5 闸门归因历史保留

集成前曾连续多轮观测到 `g0_freeze` 恒 FAIL（冻结件哈希漂移）、verdict 恒 FAIL、`--strict` 永不可达。当时经用户拍板采用分层证据方案。上游随后独立裁决修复（重算 MANIFEST 侧），修复后 5/5 PASS。

`--strict` 不绿的原因唯一且正当：C（权限模板）与 E（工具注册）不在工作台侧的职责范围内，它们的 PENDING 状态是设计如此（需要主仓侧认领后由对应负责人推进）。

## 六、给主仓的四条架构建议

1. **写入时就打结构化槽位标签 `(slot, value, polarity, temporality)`**。D7 的 4 对失败全因检索期无法推断查询意图与事实槽位之间的映射——这在写入时是平凡的（沉淀策略知道自己在写什么槽位），在检索时是不可能的（8 类词典覆盖不了开放域语义）。
2. **若有 embedding 能力，用 embedding cosine 替代 bigram cosine**：可一次性解决 RC-2（L2 长度偏置）+ D7 的 4 对。若没有，接受 v2 天花板 24/32。
3. **词典扩充按通用规则枚举，不按失败样例补词**：反事实实验证实补词最多买 +1 对（24→25），代价是词表失去通用性论证。建议按「现代汉语频率表 top-N」等独立来源扩充。
4. **`limit=2` 可把 v2 recall 从 0.75 升到 ~0.90**（D9 的 3 对 multi-relevant 受益），但 precision 会降。这是产品决策，技术上已就绪。
