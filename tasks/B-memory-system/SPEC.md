# 任务 B：记忆系统

## 目标
memory_candidate 从"只写不读"变成真记忆：检索进 prompt、质量可度量、跨会话零泄漏。

## 工作文件
- src/memory_store.py：实现 score_retrieval()（golden 集 8 对，查准/查全 ≥0.8）
- 可新增 src/memory_ranker.py 等文件（纯标准库，带 main-repo-target 头）

## 验收闸门
- g1_memory 全绿（roundtrip 本来就绿；score_retrieval 实现后 PENDING 转 PASS）

## 证据要求
1. run_all --strict ×3
2. 检索失败案例说明（golden 集中哪些对最难、为何）
3. 集成说明：主仓侧如何把 recall() 接进 build_messages 的 extra_system
