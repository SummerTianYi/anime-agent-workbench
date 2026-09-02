# 任务 E：只读工具注册表

## 目标
每个工具有硬 allow-list 根目录（注册期设定，模型不可指定），模型给的路径参数必须校验：
相对路径不得逃逸根目录；绝对路径一律拒绝。

## 工作文件
- src/tools_registry.py：实现 openai_schema() 与 execute()

## 验收闸门
- g1_tools 全绿：schema 合法（type/name/parameters 齐全）、根内文件可读、逃逸与绝对路径全拒

## 证据要求
1. run_all --strict ×3
2. 每个工具的参数表与拒绝样例表
3. 集成说明：主仓侧 build_tool_registry 如何替换为该注册表
