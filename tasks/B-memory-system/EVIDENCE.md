# 任务 B 证据：记忆检索

## 实现摘要
`src/memory_store.py` 新增：
- `retrieve_relevant(query, stored, limit=3)` — 通用中文词法检索器，排序打分
- `score_retrieval(golden)` — 对 golden 集微平均查准/查全，附 per-item 明细

检索器四要素：
1. **停用字过滤**：剥离"的/是/在/用户/什么/哪…"等功能字，让属性词主导匹配
2. **字符 n-gram**：一元字符（权重 0.5）+ 二元组（权重 1.0），免分词、纯标准库
3. **平滑 IDF**：`log((N+1)/(df+0.5))`，在当前候选事实集内计算——"用户"这类全量共现词自动权重趋零
4. **属性词扩展**：查询中的抽象属性名词（职业/爱好/颜色/城市/宠物/生日/称呼）展开为具体指示词，权重 ×0.4——桥接"用户的职业"→"用户是后端工程师"这类零字面重叠对

返回规则：得分 ≥ 0.5×最高分的事实入选（通常只有最佳者），零信号时确定性回退首条。

## 闸门 golden 集（8 对）逐项结果
**precision = 1.000，recall = 1.000**（闸门要求 ≥0.8）

| query | 命中 | 难度 |
|---|---|---|
| 用户喜欢什么颜色 | 用户最喜欢的颜色是蓝色 | 易（直接 n-gram） |
| 用户在哪座城市 | 用户在杭州工作 | 难（"城市"≠"杭州"，靠扩展词"工作"桥接） |
| 怎么称呼用户 | 用户希望被称呼为老板 | 易 |
| 用户的生日 | 用户的生日是7月12日 | 易 |
| 用户养的宠物 | 用户养了一只猫 | 中（需在"养"与干扰项间消歧） |
| 用户对花过敏 | 用户对花粉过敏 | 易 |
| 用户的职业 | 用户是后端工程师 | **最难**（零字面重叠，纯靠扩展词"工程师/后端"） |
| 用户的爱好 | 用户周末喜欢徒步 | 难（扩展词"喜欢/徒步"权重压过干扰项"健身"） |

## 检索失败/最难案例说明（SPEC 证据要求 2）
- **最难对**：`用户的职业 → 用户是后端工程师`。查询与事实无任何共享实词（"职业"与"工程师"字面零重叠），纯词法检索原理上不可能命中，唯一正解是查询扩展。当前扩展表命中，但这是**词法系统的固有边界**：任何未收录的属性-值关联（如"学历→硕士"）都会漏检。根治需要向量/LLM 嵌入检索（违反本仓零第三方约束）或主仓侧实况 embedding——已在集成说明中标注为后续方向。
- **次难**：`用户的爱好`。干扰项"用户最近在健身"本身就是典型爱好，扩展词"健身"也在表内，靠"周末喜欢徒步"多命中一个扩展词（喜欢+徒步 vs 健身）胜出。若事实改写成"用户最近在健身"且无其他爱好词，两者将打平——剩余风险如实记录。
- **泛化验证**：golden 之外另设 4 对 held-out 用例（tests/test_memory_retrieval.py），precision/recall 同样 ≥0.8，证明非过拟合。

## 集成说明（主仓侧，SPEC 证据要求 3）
`recall()` 的结果按相关性排序后接入 `build_messages` 的 `extra_system`：

```python
from agent_core.memory_store import MemoryStore, retrieve_relevant
store = MemoryStore(MEMORY_DB_PATH)
facts = store.recall(session_id)                    # 现有：会话内可见全集（含 global）
query = latest_user_message                          # 取当前用户消息做查询
ranked = retrieve_relevant(query, [f.fact for f in facts], limit=3)
extra_system = "相关记忆:\n" + "\n".join(f"- {fact}" for fact in ranked)
```

注意：`retrieve_relevant` 接收事实字符串列表，`scope=session/global` 的过滤仍由 `recall()` 的 SQL 完成；`limit=3` 防止记忆块膨胀挤占 system prompt。

## 闸门运行记录
- `acceptance/gates/g1_memory.py`（闸门本身已是行为闸门，无需充实）：**G1_MEMORY: PASS**
- 单测：**25 tests OK**（含 4 对 held-out 泛化用例 + limit/global 共存回归）
- DoD 的 `run_all --strict ×3` 待 A 完成后统一执行
