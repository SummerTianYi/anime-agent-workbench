# 任务 C 证据：权限层

## 实现摘要
`src/permissions.py` — `PermissionEngine.evaluate()`，决策顺序：

1. **malformed-request**（硬拒）：`arguments` 非 dict，任何规则都不可放行
2. **path-safety**（硬拒）：任一字符串参数（含嵌套 dict/list）呈绝对路径（盘符、`/` 开头、`~`）或含 `..` 段（反斜杠已归一化），任何规则都不可放行
3. **规则表**：按序首中即决，返回该规则的 `rule_id`；规则可带 `no_absolute_path` / `no_traversal` 约束
4. **default-deny**（硬拒）：无规则命中 → `rule_id="default-deny"`

## 策略矩阵（tool × origin → decision）

规则集为空（`rules=None`）时：

| tool | origin | arguments | decision | rule_id |
|---|---|---|---|---|
| * | user/agent/schedule | 合法 | **DENY** | `default-deny` |

带规则集 `[allow-read-agent: read_file × * → ALLOW]` 时：

| tool | origin | arguments | decision | rule_id |
|---|---|---|---|---|
| read_file | agent | `{"path": "notes.txt"}` | ALLOW | `allow-read-agent` |
| read_file | agent | `{"path": "../secrets.env"}` | **DENY** | `path-safety` |
| read_file | agent | `{"path": "..\\..\\secrets.env"}` | **DENY** | `path-safety` |
| read_file | agent | `{"path": "C:/Windows/win.ini"}` | **DENY** | `path-safety` |
| read_file | agent | `{"path": "/etc/passwd"}` | **DENY** | `path-safety` |
| read_file | agent | `{"path": "~/ssh-keys"}` | **DENY** | `path-safety` |
| read_file | agent | `{"nested": {"p": "a/../b"}}` | **DENY** | `path-safety` |
| read_file | agent | `"not-a-dict"`（非 dict） | **DENY** | `malformed-request` |
| delete_file | * | 任意 | **DENY** | `default-deny` |

带序表 `[deny-delete: delete_file × * → DENY, allow-all: * × * → ALLOW]` 时：

| tool | origin | decision | rule_id | 说明 |
|---|---|---|---|---|
| delete_file | user | DENY | `deny-delete` | 首中即决，具体规则优先 |
| speak | user | ALLOW | `allow-all` | 通配兜底 |

## 每条拒绝规则对应的测试名（tests/test_permissions.py）

| rule_id / 行为 | 测试 |
|---|---|
| `default-deny` | `DefaultDenyTests::test_no_rules_denies_with_default_deny_id` |
| `default-deny`（规则集未覆盖的 tool） | `DefaultDenyTests::test_unknown_tool_denied_even_with_rule_for_other_tool` |
| `path-safety`（相对逃逸） | `InjectionResistanceTests::test_relative_escape_denied_despite_permissive_rule` |
| `path-safety`（绝对路径 ×3 形态） | `InjectionResistanceTests::test_absolute_path_denied_despite_permissive_rule` |
| `path-safety`（反斜杠归一化） | `InjectionResistanceTests::test_windows_backslash_traversal_denied` |
| `path-safety`（嵌套参数） | `InjectionResistanceTests::test_traversal_hidden_in_nested_arguments_denied` |
| `malformed-request` | `MalformedRequestTests::test_non_dict_arguments_denied` |
| 规则命中返回 rule_id | `RuleHitTests::test_matching_rule_returns_its_rule_id` |
| 首中即决 | `RuleHitTests::test_first_match_wins_over_later_wildcard` |

## 闸门运行记录
- `acceptance/gates/g1_permissions.py` 已由本任务充实为行为闸门（6 条注入样例 + 默认拒绝证明 + rule_id 归因 + 首中即决 + 畸形参数），运行结果：**G1_PERMISSIONS: PASS**
- `python acceptance/run_all.py`：**VERDICT: PENDING-OK**（无 FAIL；剩余 PENDING 为未认领的 B/E/A，符合预期）
- `python -m unittest discover -s tests`：**12 tests OK**
- 注：`evidence/run_*.json` 被 .gitignore 排除，不随仓库分发；DoD 的 `run_all --strict ×3` 在 B/E/A 全部认领完成后统一执行（strict 模式下任何 PENDING 都会阻塞，单任务阶段无法满足，此处如实记录）
