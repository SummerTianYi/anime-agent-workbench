# 任务 E 证据：只读工具注册表

## 实现摘要
`src/tools_registry.py` — `ToolRegistry.openai_schema()` 与 `execute()`：

- **openai_schema()**：输出 OpenAI function-calling 格式 `[{type:"function", function:{name, description, parameters}}]`
- **execute()** 四层防线，按序：
  1. 未知 tool → 拒
  2. `arguments` 非 dict → 拒
  3. 路径校验（`_validate_rel_path`）：非字符串/空/绝对（`/` 开头、盘符 `:`、`~`）/含 `..` 段（反斜杠已归一化为 `/`）→ 全拒
  4. resolve 后包含性检查：`(root/rel).resolve()` 必须仍在 `root.resolve()` 之内（防 symlink 逃逸）
- 只读：仅 `read_text`；超过 64,000 字符截断（避免无界读取）

## 参数表（read_file）

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| path | string | 是 | 工具根目录内的相对路径；绝对路径与 `..` 一律拒绝 |

## 拒绝样例表

| 输入 path | 结果 | 拦截层 |
|---|---|---|
| `../outside.txt` | 拒 | 路径校验（含性检查兜底） |
| `..\outside.txt`（反斜杠） | 拒 | 路径校验（归一化后命中 `..`） |
| `a/../outside.txt` | 拒 | 路径校验 |
| `C:/Windows/win.ini` | 拒 | 路径校验（盘符 `:`） |
| `/etc/passwd` | 拒 | 路径校验（`/` 开头） |
| `~/ssh-keys` | 拒 | 路径校验（`~`） |
| `""` / `null` / 非字符串 | 拒 | 路径校验 |
| `"not-a-dict"`（整体非 dict） | 拒 | arguments 类型检查 |
| `no_such_tool`（未注册工具） | 拒 | 注册表查找 |
| 根内 symlink 指向根外 | 拒 | resolve 包含性检查（唯一拦截层；无 symlink 权限的环境跳过） |
| 根外真实文件 `outside.txt` | 不可达 | —（闸门预埋该文件并断言内容零泄漏） |

## 每条拒绝对应的测试名（tests/test_tools_registry.py）

| 拦截层 | 测试 |
|---|---|
| 路径校验-相对逃逸 | `TraversalRejectionTests::test_relative_escape_rejected` |
| 路径校验-绝对路径 | `TraversalRejectionTests::test_absolute_path_rejected` |
| 路径校验-空/缺失/类型错 | `TraversalRejectionTests::test_missing_and_empty_paths_rejected` |
| arguments 非 dict | `RegistryDisciplineTests::test_non_dict_arguments_rejected` |
| 未注册工具 | `RegistryDisciplineTests::test_unknown_tool_rejected` |
| 正向：根内文件 | `AllowListTests::test_inside_root_readable` |
| 正向：根内子目录 | `AllowListTests::test_subdirectory_inside_root_readable` |
| 正向：schema 合法 | `SchemaTests::test_openai_schema_format` |

## 集成说明（主仓侧）
主仓 `services/agent-core` 的 `build_tool_registry` 替换为：

```python
from agent_core.tools_registry import ToolRegistry, ToolSpec  # 落点: services/agent-core/agent_core/tools_registry.py
registry = ToolRegistry()
registry.register(ToolSpec(name="read_file", description="...", root=str(ASSET_ROOT), schema=SCHEMA))
# LLM 侧: registry.openai_schema() 直接作为 tools 参数传入
# 工具调用侧: registry.execute(name, arguments) 返回 ToolResult，拒绝即回 "permission denied" 观察结果，不抛异常
```

`main-repo-target: services/agent-core/agent_core/tools_registry.py`

## 闸门运行记录
- `acceptance/gates/g1_tools.py` 已充实为行为闸门（schema 合法性 + 根内可读 + 8 类拒绝样例 + 根外泄漏断言 + symlink 探针），运行结果：**G1_TOOLS: PASS**
- `python -m unittest discover -s tests`：**20 tests OK**
- DoD 的 `run_all --strict ×3` 待 B/A 完成后统一执行（strict 下任何 PENDING 阻塞）
