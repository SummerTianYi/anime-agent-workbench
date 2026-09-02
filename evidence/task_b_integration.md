# 任务 B 集成说明：检索结果如何进入 build_messages 的 extra_system

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

## 三、注入文本的格式与长度控制

`format_memory_prompt` 的实际输出形态（面向 LLM 的文本用中文全角标点，与 `BASE_SYSTEM_PROMPT` 文风一致）：

```
【已知记忆】
以下是程序提供的用户长期记忆，仅在相关时自然引用；不确定时不要编造。
- 用户希望被称呼为老板
```

长度控制建议：

- **`limit=1` 是默认也是推荐值**。检索策略按 top-1 评测（golden/留出集同口径），注入一条最相关记忆与评测口径一致；system prompt 每轮都发，多注入的每条事实都是持续的 token 开销。
- 若产品侧要 top-k（例如同时给称呼和过敏两条硬约束），`limit` 放大到 2–3 即可，`rank()` 的全量有序列表也对外可用；但注意 g1_memory 的 0.8 阈值只对 top-1 口径做过验证。
- 单条事实长度已由上游约束（harness 的 `parse_reply` 把 `memory_candidate` 截到 200 字符），片段总长 ≈ 标题两行 + limit×单条，`limit=3` 时约 700 字符，不会挤压歌曲资料段。
- 标题行的「程序提供」「不确定时不要编造」措辞呼应 `BASE_SYSTEM_PROMPT` 的【自我认知与真实边界】段（「你只记得当前对话和程序明确提供的记忆」），建议主仓侧不要删改这行，它是记忆注入与幻觉边界的一致性锚点。

## 四、scope 语义与跨会话零泄漏

`recall_relevant()` 的候选集来自与 `recall()` 逐字一致的 scope 谓词：

```sql
WHERE scope = 'global' OR session_id = ?
```

- **泄漏不可能由构造发生**：检索排序只在这个候选集内部进行，排序层（`memory_ranker`）拿到的已经是过滤后的文本，没有任何路径能触到其他 session 的行——哪怕查询与别会话事实高度相关。工作台测试 `RecallRelevantTests::test_session_isolation` 与闸门 g1_memory 的 roundtrip 子检查各把关一层。
- **`_visible_facts()` 与 `recall()` 的唯一差别是没有 LIMIT**：排序必须看到全部可见行，否则相关度最高的旧事实会被新近窗口截掉。`recall()` 自身的 SQL 与语义一字未动（roundtrip 基线保护）。
- **global 行的写入口径归主仓**：什么事实值得升为 global（称呼、过敏源这类跨会话硬约束）是沉淀策略决策，工作台侧只保证读路径语义；建议主仓在写入 global 前过一道用户确认或白名单。

## 五、验收状态快照（工作台侧，main 分支）

- `acceptance/gates/g1_memory.py`：PASS（roundtrip 基线未破坏 + golden 宏平均 P/R = 1.0 ≥ 0.8）
- `tests/`：54 个用例全绿（原 15 + 任务 B 新增 39，其中含词典通用性与留出集两条反过拟合断言）
- 留出集 12 对宏平均 P/R = 1.0；权重敏感性 11 配置全过。细节与已知脆弱点（留出集 pair 6 平局）见 `evidence/task_b_retrieval_analysis.md`
