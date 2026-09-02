# evidence/

每次验收运行的证据目录（run_all.py 自动写入，带 commit hash 与逐闸门结果）。

规则：
1. `run_all.py --strict` 的证据必须留存（DoD 必需）
2. 演练（sabotage_drill.py）输出证据必须留存
3. 提交前删除过期运行记录，保留最后 10 条
