# 任务 B（记忆系统）sabotage_drill 取证

本文件按 rebase 集成上游修复**之后**的最终状态整体重写，不是对上一版的补丁。
上一版（commit `9eade73` 时期，207 行）记载的「`g0_freeze` 本来就红」
「有效检出只有 2 路」「drill 会把 CRLF 文件整体归一化」三条结论在本轮已分别
**解除 / 改判 / 推翻**，逐条理由见第 5、6 节；历史观测如实保留，没有抹掉。

所有数字均由命令输出产生，无一处手抄。时间戳来自 `date '+%Y-%m-%d %H:%M:%S %z'`，
行数来自 `wc -l`，哈希来自 `shasum -a 256` / `git hash-object` / `git rev-parse`，
退出码来自 `===EXIT=$?===` 标记。

## 0. 定位锚点

> **本文件里的 commit hash 是 author 改写前的值。** push 前全部本地 commit 的
> author 会被改写，改写后所有 commit hash 全部失效。长期有效的稳定锚点是
> **tree 哈希、blob 哈希，以及 commit 的 subject + 序数**。author 改写不动
> tree 也不动 blob，下面这两类哈希在改写前后逐字不变。

| 锚点 | 值 | 取得方式 |
|---|---|---|
| commit（drill 前后未变） | `d6868c654a821abf7920d249683837db6068a87a`（短 `d6868c6`） | `git rev-parse HEAD` |
| **HEAD tree（稳定）** | `37d26de723f1571ec3c6aa0cced25f2794eece68` | `git rev-parse HEAD^{tree}` |
| `origin/main` tree | `0c9ce3a1a5fc70cf198a3d6e5bff978c80486dfd` | `git rev-parse origin/main^{tree}` |
| 领先 / 落后 `origin/main` | 39 / 0 | `git rev-list --count` 两向 |
| 解释器 | Python 3.14.7 | `./.venv/bin/python -VV` |
| drill 执行时刻 | 2026-09-04 16:12:44 → 16:12:45 +0100 | 日志 `START` / `END` 行 |
| 前置绿快照时刻 | 2026-09-04 11:05:02 +0100 | 快照日志 `wall-clock` 行 |
| 手工复验时刻 | 2026-09-04 16:28:43 → 16:28:52 +0100 | 复验日志各节时间戳 |

原始日志（行数由 `wc -l` 给出）：

| 文件 | 行数 | 内容 |
|---|---|---|
| `evidence/task_b_sabotage_drill.log` | 9 | drill 本体逐字输出 + 退出码 |
| `evidence/task_b_after_drill.log` | 243 | 手工复验回绿 A–E + `__pycache__` 污染实测 F + 判定 G + 四缺陷确认 H |
| `evidence/task_b_drill_attribution.log` | 105 | 三路归因的只读分析（不执行 drill） |

三份日志经机器指纹探针扫描，命中数均为 **0**。探针的具体字面样式串**不在本文件里
列举**，只用 ID 与语义指代：本机用户家目录前缀、Linux 家目录前缀、两种写法的
Windows 盘符、每用户临时目录前缀、系统临时目录前缀、本地登录名、仓库绝对路径
（对应扫描记录里的 P01–P08）。完整的逐文件×逐探针计数表在
`evidence/task_b_scan_report.log`。

> **为什么这里不列字面串——本文件真犯过这个错，而且是同一个错的第三次。**
> 本段原本为了说明「扫了哪些样式」，把三个路径类探针的字面样式串直接抄进了正文
> （一个 Linux 家目录前缀、一个每用户临时目录前缀、一个系统临时目录前缀，
> 即 P02 / P05 / P06）。于是本文件自己命中这三个探针各 1 处，共 3 处。
> 扫描记录第一次跑出来就是 `泄漏类合计命中 = 3`、判定 `False`、退出码 1，
> 全部三条都指向本文件那两行。同类自指泄漏本轮已犯三次
> （另两次：本文件早前的版本、以及 `task_b_final_selfcheck.md` 第 7.1 节），
> 教训是同一条：**任何要在文档里描述探针的地方，一律用 ID + 语义描述，绝不印字面串。**
>
> 本段自己也不能把「改前的原文」整句引下来——引下来就等于把三个样式串再抄一遍，
> 那就是同一个错的第四次。所以这里只说它们是什么类别、对应哪个 ID，不写它们长什么样。
> 现在这三处已改为语义指代，重跑扫描后本文件 P01–P17 全 0（计数见扫描记录）。

消毒规则：仓库根记作 `<repo>`，仓库外临时目录记作 `<scratch>`；实质数值逐字未改。

> 前置绿快照本身还有一份同格式的三轮基线快照，见 `evidence/task_b_gate_matrix.md`
> 第 2 节（48 格）与第 2.1 节（焦点闸门单独复跑）。

---

## 1. drill 本体输出原文

`evidence/task_b_sabotage_drill.log` 全文（9 行，逐字）：

```
=== START 2026-09-04 16:12:44 +0100 ===
cmd: ./.venv/bin/python acceptance/sabotage_drill.py
HEAD: d6868c654a821abf7920d249683837db6068a87a
HEAD tree: 37d26de723f1571ec3c6aa0cced25f2794eece68
----------------------------------------------------------------
DRILLS DETECTED: 3 of 3
----------------------------------------------------------------
===EXIT=0===
=== END 2026-09-04 16:12:45 +0100 ===
```

**`DRILLS DETECTED: 3 of 3`，退出码 0。** drill 自身的输出**只有中间那一行**——
三路各是什么、每路闸门红在哪一行、红的原因是不是预期的那条，日志里一个字节都没有。
这不是本轮漏了什么，是 `sabotage_drill.py` 第 19–21 行 `run_gate()` 只
`return proc.returncode`、把 stdout/stderr 全丢了，而 `drill()` 只在 SKIP /
NOT DETECTED / RESTORE FAILED 三种失败情形下才 print。见第 6 节缺陷③。

---

## 2. 破坏前 / 破坏后哈希对照

三个目标文件，drill 前后各测一次。**blob 哈希是稳定锚点**（author 改写不动它），
sha256 是给闸门判据用的（`g0_freeze` 比的就是 sha256）。

| 目标文件 | blob（`git hash-object`） | sha256 drill 前 | sha256 drill 后 | 一致 |
|---|---|---|---|---|
| `vendor/agent_core/harness.py` | `29dca70bcc740976910cd0f85d38f2ce9034795c` | `cb1ae928f80674952c4ac6e6385d260a7dbd5cf93ac5ab96889ff6bdb32b2807` | 同左 | 是 |
| `src/memory_store.py` | `49d273aa9286afdf4d6f649b915c56042c9354e1` | `3c81cd6b973a2b18a7be42b15d50744101ee6b1d0cec6137ee6471dd7efaa63a` | 同左 | 是 |
| `acceptance/evals/scenarios.json` | `53ab5c2bf54027f3e333e0f980259acbe0e72150` | `2c5dab3fc5e414680193c7b998bb62cf9fe3c6299f2f002682a75efa8179b00e` | 同左 | 是 |

3/3 逐字节还原。三者的 `git hash-object <path>` 与 `git rev-parse HEAD:<path>`
也逐个相等，说明索引、工作树、HEAD 三处字节一致，没有残留的 eol 转换。

与冻结锁的关系：`harness.py` 与 `scenarios.json` 的 sha256 与
`acceptance/MANIFEST.json` 的记载值**相等**（`g0_freeze` 判据成立）。drill 既没有
引入新的冻结件漂移，也没有"顺手修好"任何既有漂移——集成后本来就没有漂移了。

工作区核查（`evidence/task_b_after_drill.log` E 节末尾）：

```
git status --porcelain --untracked-files=no : ''
git diff --stat                             : ''
```

tracked 文件零变动。还原靠 `sabotage_drill.py` 第 25 行 `original = target.read_bytes()`
与第 37 行 `finally: target.write_bytes(original)`——字节级读、字节级写。

### 2.1 与上一版的哈希差异（集成 + 阶段三造成的，不是 drill 造成的）

| 文件 | 上一版记载的 sha256 | 本轮 sha256 | 变化原因 |
|---|---|---|---|
| `vendor/agent_core/harness.py` | `cb1ae928…b32b2807` | `cb1ae928…b32b2807` | **未变** |
| `src/memory_store.py` | `d5b1d782…2f5b7586` | `3c81cd6b…7efaa63a` | 阶段三代码侧重写（任务 B 自己的交付物） |
| `acceptance/evals/scenarios.json` | `01ed805a…32df42e67` | `2c5dab3f…efa8179b00e` | 上游 commit 重算 MANIFEST + `.gitattributes` 强制 LF |

`scenarios.json` 的形态变化最要紧：上一版它是 **2870 字节 / CRLF=118 / bare_LF=0**，
本轮是 **2752 字节 / CRLF=0 / bare_LF=118**，差值恰好 118 = 每行少一个 `\r`。
这是上游 `.gitattributes`（单行 `* text=auto eol=lf`）生效后工作树被重新归一化的
结果，MANIFEST 也按新字节重算了，所以 `g0_freeze` 现在是绿的。这条直接决定了
第 6 节缺陷④的判定翻转。

---

## 3. 三路破坏逐条分析

| # | drill 名 | 目标文件 | 锚点 → 替换 | 锚点出现次数 | 字节差 | 判据闸门 | drill 前该闸门 | 归因 |
|---|---|---|---|---|---|---|---|---|
| 1 | prompt-fact-sabotage | `vendor/agent_core/harness.py` | `#66CCFF` → `#000` | 1 | −3 | `g1_contract` | PASS / 0 | **成立** |
| 2 | memory-sabotage | `src/memory_store.py` | `INSERT INTO facts` → `INSERT INTO facts_gone` | 1 | +5 | `g1_memory` | PASS / 0 | **成立** |
| 3 | eval-tamper | `acceptance/evals/scenarios.json` | `"identity-01"` → `"identity-01x"` | 1 | +1 | `g0_freeze` | **PASS / 0** | **成立（本轮改判）** |

「锚点出现次数」与「字节差」由 `evidence/task_b_drill_attribution.log` 只读算出
（在内存里做 `decode → str.replace → encode`，不写盘、不执行 drill），三个锚点都
**唯一**，替换串在原文中都不存在，所以每路都是最小改动。

**第 1 路**：`src/prompt_persona/system_prompt.py` 的 `ACTIVE_SYSTEM_PROMPT` 直接来自
vendor harness，`REQUIRED_IDENTITY_FACTS` 含 `"#66CCFF"`；`g1_contract.py` 把它喂给
`MockProvider(required_facts=...)`，检出 `PROMPT_MISSING` → problems 非空 → 退出码 1。
附带效应：`harness.py` 本身是冻结件，破坏窗口内 `g0_freeze` 也会红
（实测破坏后 sha256 `aab38538a5ee93980c51171d95d9767fdeb1c210ada7377ccd67980a787920d2`
≠ MANIFEST 记载值），但本路的判据闸门是 `g1_contract`，不受影响。

**第 2 路**：`src/memory_store.py` 的 `INSERT INTO facts` 是 `MemoryStore.add()` 唯一的
写入语句，改成 `facts_gone` 后 sqlite 报 no such table；`g1_memory.py` 把 roundtrip 包在
try 里，异常被收成 `problems.append("roundtrip raised: ...")` → 退出码 1。**这一路直接
打在任务 B 的交付物上，是三路里对任务 B 最有意义的一路。** `memory_store.py` 不在
MANIFEST 的 5 个冻结件里，所以这一路不会连带触发 `g0_freeze`。

**第 3 路**：`g0_freeze.py` 第 41–42 行 `elif expect != sha256(path): problems.append(
f"{rel}: content drifted from frozen manifest")`。只读算出的破坏后 sha256 是
`6c49b964fe47a20ccda17a327f284cbcc40b20cb6b347f0bc62bcbd935890765`，与 MANIFEST 记载的
`2c5dab3f…efa8179b00e` 不等 → 必然产生一条且仅一条 drift 记录 → 退出码 1。

---

## 4. 前置绿断言（补 drill 缺失的那一步）

`evidence/task_b_sabotage_drill.log` 里没有这一节，因为 drill 自己不做。本轮在
**2026-09-04 11:05:02 +0100** 用仓库外脚本单独跑了完整 8 闸门快照：

| 闸门 | 退出码 | 状态 | stdout |
|---|---|---|---|
| `g0_environment` | 0 | PASS | `G0_ENVIRONMENT: PASS` |
| `g0_secrets` | 0 | PASS | `G0_SECRETS: PASS` |
| **`g0_freeze`** | **0** | **PASS** | `G0_FREEZE: PASS` |
| **`g1_contract`** | **0** | **PASS** | `G1_CONTRACT: PASS` |
| **`g1_memory`** | **0** | **PASS** | `G1_MEMORY: PASS` |
| `g1_permissions` | 2 | PENDING | `evaluate() not implemented (Task C)` |
| `g1_tools` | 2 | PENDING | `openai_schema/execute not implemented (Task E)` |
| `g3_simulate` | 0 | PASS | `G3_SIMULATE: PASS` |

合计 PASS=6 / FAIL=0 / PENDING=2。**三个 drill 相关闸门（`g1_contract`、`g1_memory`、
`g0_freeze`）在 drill 前逐个都是退出码 0**，8 个闸门的 stderr 全为空。

这份快照是第 5 节改判的唯一依据。没有它，`3 of 3` 里的任何一路都可以被质疑成
「闸门本来就红，drill 只是捡了个便宜」。

---

## 5. 有效检出的重新判定（第 3.3 步）

### 5.1 上一版的保留意见原文

上一版第 5 节写的是：

> **结论：第 3 路的"检出"在逻辑上无法归因于 `scenarios.json` 的篡改，`3 of 3` 里这一路是无效证据。**
> ……`g0_freeze` 在 drill 之前就因为 `vendor/agent_core/harness.py` 的上游哈希漂移而是红的（退出码 1）
> ……不粉饰成 3/3 全部有效：**有效的只有第 1、2 路**。

当时的依据是真实观测：`g0_freeze` 连续多轮 FAIL，唯一的 drift 项是 `harness.py`。
在那个状态下，第 3 路的「检出」确实是假阳性——`run_gate("acceptance/gates/g0_freeze.py") != 0`
在破坏发生**之前**就已经成立，哪怕 `scenarios.json` 一个字节都没改，这一路照样会被记为检出。

### 5.2 本轮判定：**保留意见已解除，有效检出改判为 3/3**

依据是四条实测，缺一不可：

1. **前置绿成立。** drill 前 `g0_freeze` 退出码 **0**、stdout `G0_FREEZE: PASS`、
   stderr 空（第 4 节，2026-09-04 11:05:02）。上一版那条「本来就红」的前提不存在了。
2. **drift 的唯一来源被消灭。** `harness.py` 的 sha256 与 MANIFEST 记载值相等
   （`cb1ae928…b32b2807`），5 个冻结件 5/5 MATCH。上游那个 commit 重算了 MANIFEST
   并新增 `.gitattributes`，漂移由**上游独立裁决并修复**，不是本仓自己动手让闸门变绿
   ——本仓全程没改过任何冻结件、没改过 MANIFEST、没跑过 `g0_freeze.py --update`，
   冻结区 diff（含 `.gitattributes`）实测为空。
3. **破坏 → 变红的因果链在只读层面闭合。** 第 3 节算出破坏后 sha256
   `6c49b964…35890765` ≠ MANIFEST 记载值，而 `g0_freeze.py` 第 41–42 行的判据就是
   `expect != sha256(path)`。锚点唯一、字节差 +1，所以窗口内 `g0_freeze` 变红的原因
   **只能是** `scenarios.json` 的这一处篡改，不存在第二个可疑来源。
4. **drill 后回到绿。** `g0_freeze` 退出码 0，且 stdout 只有 `G0_FREEZE: PASS` 一行，
   **没有** `acceptance/evals/scenarios.json: content drifted` 那一行（第 7 节 A 节）。
   若篡改字节残留，这里必然多出一行。

四条合起来：绿 → 破坏 → 红 → 还原 → 绿，链条完整且每一步都有独立证据。
**有效检出 = 3/3。**

### 5.3 这个改判没有把缺陷①一笔勾销

必须说清楚：改判成立靠的是**本轮外部补做了前置绿快照**，不是 drill 自己变严谨了。
`sabotage_drill.py` 第 24–35 行依然没有任何前置断言（第 6 节缺陷①）。也就是说：

- 在**这一轮的这个树**上，3/3 是有效的，因为外部证据补齐了因果链。
- 但 drill 这个**工具**依然无法自证。换一个 `g0_freeze` 本来就红的树（比如集成前的
  那几十个 commit），它会照样打印 `3 of 3` 而毫无区别。上一版在集成前的树上得出
  「只有 2 路有效」，本轮在集成后的树上得出「3 路有效」——**两次结论都对自己的树成立**，
  差别不在 drill，在树。

所以缺陷①仍然是缺陷，仍然记在闸门异议卷宗里（该卷宗由另一位工程师并行维护，
本轮未读取、未引用其内容）。

### 5.4 上一版的补强实验现在还需不需要

上一版因为真仓库里 `g0_freeze` 恒红，不得不在仓库外复制一份最小闭包（`g0_freeze.py`
+ `MANIFEST.json` + 5 个冻结件），改副本的 MANIFEST 后再用字节级替换验证
「`g0_freeze` 对 `scenarios.json` 单字节篡改确实有牙齿」，实测 A/B/C 三步
`0 → 1 → 0`。

本轮**不需要副本了**：真仓库的 `g0_freeze` 就是绿的，drill 直接在真树上跑通了这一路，
第 5.2 条 3 又在只读层面独立算出了破坏后的 sha256 与 MANIFEST 不等。副本实验的结论
被真树实验**覆盖并加强**——上一版只能说「闸门本身有牙齿，缺的是 drill 的前置断言」，
本轮能说「闸门有牙齿，而且这一次 drill 的检出确实是这副牙齿咬出来的」。
上一版那份副本实验只在仓库外的临时目录发生过，真仓库的 MANIFEST 从未被修改，
这一点上一版已自证（复算 sha256 与 `git show HEAD:acceptance/MANIFEST.json` 逐字相同、
`git diff HEAD -- acceptance/MANIFEST.json` 为空），本轮不再重复。

---

## 6. drill 自身四个代码缺陷：实测确认与集成后的状态变化

四个缺陷全部**依然存在**——集成上游修复动的是 MANIFEST 与 `.gitattributes`，
`sabotage_drill.py` 一个字节没改（它在冻结区外，但也没人碰它）。变的是**后果**。

### 缺陷①：没有「破坏前该 gate 必须是绿的」前置断言

代码事实：第 24–35 行 `drill()` 的全部逻辑是读原字节 → 找锚点 → 写破坏字节 →
跑 gate → `if run_gate(gate) == 0: 报 NOT DETECTED`。**没有任何一行在破坏之前先跑一次
gate 确认它是绿的。**

后果：只要目标 gate 因别的原因已经红，`run_gate(gate) != 0` 恒成立，`drill()` 恒返回
True，drill 恒报"检出"。典型的假阳性——闸门没牙齿时 drill 也会说它有牙齿。

集成后的状态变化：**这一轮没有踩到它**，因为第 4 节的外部快照证明了三个目标闸门
drill 前都是 0。但缺陷本身没修，见第 5.3 节。上一轮踩到了，代价是第 3 路证据作废。

### 缺陷②：「恢复后复跑 gate 验证回绿」是死代码

代码事实：第 26–37 行是 `try: … return True / finally: target.write_bytes(original)`，
第 38–43 行的 `shutil.rmtree(cache)` 与 `if run_gate(gate) != 0: print("RESTORE FAILED")`
写在 `try/finally` **之后**。Python 语义：`try` 块内的 `return` 先执行 `finally` 再直接把
值返回给调用方，函数已经结束，`finally` 之后的语句永不执行。第 30、34、35 行三条路径
全部 return，所以第 38–43 行在任何输入下都不可达。

后果两层：

1. docstring 第 4–5 行声称的 "restores the original bytes, requires green again"
   后半句从未执行过，`RESTORE FAILED` 这个分支不可能被打印。「恢复后回绿」必须由
   外部手工验证——第 7 节就是这份手工验证。
2. 第 38–39 行清理 `__pycache__` 的意图一并失效。**这一层的后果在本轮被实测推翻了
   上一版的乐观判断**：上一版写「实测这一路不影响结论：三路破坏都改变了文件字节数，
   不存在同秒同尺寸导致读到陈旧 .pyc 的窗口」。字节数确实都变了，但**毒字节码确实被
   写到了磁盘上**，只是恰好被 CPython 的 size 校验挡住。挡住的机制是巧合，不是设计。
   完整实测见 `evidence/task_b_after_drill.log` F 节与第 8 节。

### 缺陷③：`run_gate()` 丢弃闸门 stdout/stderr

代码事实：第 19–21 行 `capture_output=True` 拿到两个流后只 `return proc.returncode`。

实测确认：第 1 节日志里 drill 自身的输出**只有 `DRILLS DETECTED: 3 of 3` 一行**，
没有任何逐路明细。从这份日志看不出跑了哪三路、每路红在哪一行、红的原因是不是
预期的那条。取证必须靠外部逐闸门快照补齐——第 4 节与第 7 节就是补这个。

集成后的状态变化：无。这个缺陷让「3 of 3」在任何一棵树上都只是三个比特，
本轮的 3/3 判定完全建立在外部证据上。

### 缺陷④：「文本模式改写会把 CRLF 文件整体归一化」——**本条判定为不成立**

**这一条与任务书的描述不符，也与上一版取证文档的记载不符，实测判定为不成立，如实记录。**

上一版第 101–118 行的原话是「drill 内部实际用的是 `read_text()`/`write_bytes()` 组合」
「`read_text` 的通用换行会把 118 个 CRLF 折成 LF，再 encode 写回」「第 3 路破坏期间
`scenarios.json` 从 2870 字节变成 2753 字节（−118 行尾 +1 锚点字符 = −117），
118 处行尾全部被改写」。**这是对代码的误读**：

- `sabotage_drill.py` 里**没有 `read_text()`**。第 25 行是 `target.read_bytes()`，
  第 27 行 `original.decode("utf-8")`，第 31 行 `target.write_bytes(text.replace(old, new).encode("utf-8"))`。
- `bytes.decode("utf-8")` 与 `str.encode("utf-8")` 是**纯编解码**，不做任何换行转换
  （换行转换是 `open(..., newline=None)` 的文本层行为，这里根本没走文本层）。
  `\r\n` 会原样穿过 decode/encode 往返。
- 上一版那句「−118 行尾 +1 锚点字符 = −117」自身也算错了：2870 − 117 = 2753，
  但它同一份文档第 135 行的补强实验里又写「2870 → 2871 字节」，两处互相矛盾。
  2871 才是对的（只改锚点，+1 字节）。

本轮的实测支撑（`evidence/task_b_drill_attribution.log`）：

| 目标文件 | 行尾形态 (CRLF, bare_LF, bare_CR, BOM) 破坏前 | 破坏后 | 是否被改写 |
|---|---|---|---|
| `vendor/agent_core/harness.py` | (0, 257, 0, False) | (0, 257, 0, False) | **False** |
| `src/memory_store.py` | (0, 259, 0, False) | (0, 259, 0, False) | **False** |
| `acceptance/evals/scenarios.json` | (0, 118, 0, False) | (0, 118, 0, False) | **False** |

三路的行尾形态在破坏前后**逐个不变**，字节差分别是 −3 / +5 / +1，全部等于锚点与
替换串的长度差，没有一个多余的字节被动过。另一条独立支撑：drill 后三个文件的
sha256 与 drill 前**逐字节一致**（第 2 节），若发生过换行归一化，`scenarios.json`
的 sha256 不可能还原成原值。

集成后的双重变化：

1. 前提消失了——`scenarios.json` 现在是 **CRLF=0 / bare_LF=118**（第 2.1 节），
   5 个冻结件全部纯 LF、无 BOM。「对 CRLF 文件会整体归一化」这个担忧已经无的放矢。
2. 更重要的是：**它对这份代码从来就不成立**，跟 LF/CRLF 无关。上一版把一个不存在
   的机制写进了取证文档，本轮把它删掉并留下实测反证。

**但缺陷④想指的那类风险没有消失，只是换了形态**：真正的残留风险是**半破坏**——
如果进程在第 31 行写入之后、第 37 行还原之前被 SIGKILL（或还原写入被别的东西拦下），
文件会停在破坏态。本轮**亲眼见到一个同族实例**：第一次执行 drill 时沙箱以 EPERM
拦下第 31 行的写入，第 37 行的还原写入同样被拦下并抛异常，drill 退出码 1。所幸
**第一次写入就没成功**，文件从未被改；事后实测三个 sha256 与 drill 前一致、
`git status --porcelain -uno` 与 `git diff --stat` 均空、`ls -lO` 无 macOS immutable
标志、属主与权限位正常。若当时顺序反过来（破坏成功、还原被拦），冻结件就会真的
坏在盘上，而 `g0_freeze` 会红得莫名其妙。这条已写进 `task_b_after_drill.log` H 节。

---

## 7. 手工复验回绿（补 drill 缺陷②的死代码）

全过程在 `evidence/task_b_after_drill.log`（243 行），2026-09-04 16:28:43 → 16:28:52。
分 A–E 五节，每节都是实测，不引用 drill 的返回值。

### A. 三个 drill 相关闸门单独复跑

| 闸门 | 时刻 | 退出码 | stdout | stderr | 与 drill 前快照一致 |
|---|---|---|---|---|---|
| `g1_memory` | 16:28:43 | 0 | `G1_MEMORY: PASS` | 空 | 是（前 0） |
| `g1_contract` | 16:28:43 | 0 | `G1_CONTRACT: PASS` | 空 | 是（前 0） |
| `g0_freeze` | 16:28:43 | 0 | `G0_FREEZE: PASS` | 空 | 是（前 0） |

`g0_freeze` 的输出里**没有** `acceptance/evals/scenarios.json: content drifted` 那一行
——这是 eval-tamper 已确实还原的最强证据。上一版这一格是 `FAIL / 1` 且输出里有
`harness.py` 的 drift 行，本轮两者都变了，原因见第 5、6 节。

### B. 完整 8 闸门快照，与 drill 前基线逐格比对

| 闸门 | drill 后退出码 | drill 前退出码 | 判定 |
|---|---|---|---|
| `g0_environment` | 0 | 0 | same |
| `g0_secrets` | 0 | 0 | same |
| `g0_freeze` | 0 | 0 | same |
| `g1_contract` | 0 | 0 | same |
| `g1_memory` | 0 | 0 | same |
| `g1_permissions` | 2 | 2 | same |
| `g1_tools` | 2 | 2 | same |
| `g3_simulate` | 0 | 0 | same |

**8 格全部与 drill 前一致：True。** 两个 PENDING 也回到 PENDING，没有被"顺手修好"，
也没有变成 FAIL。

### C. `run_all.py` 双模式（两次之间 `sleep 3`）

| 模式 | 起 | 止 | verdict | 退出码 | 生成的 JSON |
|---|---|---|---|---|---|
| normal | 16:28:47 | 16:28:47 | `PENDING-OK` | 0 | `run_20260904_162847.json` |
| strict | 16:28:50 | 16:28:51 | `BLOCKED` | 1 | `run_20260904_162851.json` |

两次调用产出的 JSON 文件名互不相同，实测都在 `evidence/` 下。`sleep 3` 是必需的：
`run_all.py` 第 59 行用 `time.strftime('%Y%m%d_%H%M%S')` 命名，粒度只到秒，同秒会
静默互相覆盖。两模式各自的 8 行闸门明细与三轮基线 **48 格逐格一致：True**。

上一版这一格是 `VERDICT: FAIL`、退出码 1、JSON `run_20260902_174435.json`；本轮
normal 是 `PENDING-OK`/0、strict 是 `BLOCKED`/1。变化的唯一原因是 `g0_freeze` 由
FAIL 转 PASS（第 5 节），`BLOCKED` 的成因收敛为任务 C/E 两个未认领项的正当 PENDING，
详见 `evidence/task_b_gate_matrix.md` 第 4.3 节。

### D. `unittest discover`

`Ran 254 tests in 0.419s` / `OK` / 退出码 0（16:28:51 → 16:28:52）。
命令是 `./.venv/bin/python -m unittest discover -s tests -p "test_*.py" -t tests`；
`-t tests` 必需，用 `-t .` 会报 `ImportError: Start directory is not importable`。
上一版这一格是 `Ran 54 tests`，本轮 254——阶段二/三新增的测试（含
`tests/test_ranker_mutations.py` 的变异演练与 `tests/test_holdout_v2.py` 的盲测集）
把用例数从 54 抬到 254，这是交付面扩大，不是 drill 的影响。

### E. 三个目标文件 sha256 逐一比对

见第 2 节表格。三个文件全部逐字节还原：True。

---

## 8. `__pycache__` 污染：实测结论（第 3.6 步）

完整数据在 `evidence/task_b_after_drill.log` F 节（F.0–F.3）。这里只给判定。

机制：`run_all.py` 第 41 行为它的闸管子进程设了 `PYTHONDONTWRITEBYTECODE=1`，
`sabotage_drill.py` 第 20 行的 `run_gate` **没有设**，所以 drill 自己跑闸门时会写
字节码；而第 38–39 行本该清理的 `shutil.rmtree` 是死代码（缺陷②），从来不清理。

| # | 判定 | 实测依据 |
|---|---|---|
| 1 | drill 确实在磁盘上留下**用破坏态源码编译出来的** `.pyc`，且从不清理 | F.1：`memory_store.cpython-314.pyc` 含 `facts_gone`=True、`harness.cpython-314.pyc` 含 `#000`=True 且 `#66CCFF`=False；F.0：drill 后 `__pycache__` 目录 6 个、`.pyc` 32 个，与 drill 前**一个都没少** |
| 2 | 这些毒缓存在当前三个锚点下**不会被加载** | F.1：两个 `.pyc` 的 header size 都对不上（14262 vs 14257、10052 vs 10055）→ CPython 判定缓存无效；V1 在仓库外一次性模块上复现同构结果 |
| 3 | 挡住污染的是 **size 校验，不是 mtime 校验**，这层保护是**巧合性的** | F.1：两个 `.pyc` 的 header mtime 均 MATCH（1788534765），因为破坏与还原落在同一整秒内；单靠 mtime 校验会放行毒缓存 |
| 4 | 污染是**自愈**的 | F.2：A 节第一次跑闸门后，毒字面量消失、size MATCH、cache VALID——CPython 发现 size 不匹配就从已还原的源码重编译并覆盖了 `.pyc` |
| 5 | 残留风险有两类，都已实测复现 | **V2**：等长破坏 + 同秒还原 → mtime/size 双 MATCH → 新解释器读到破坏态字面量 `'bbbbbbb'` 而磁盘源码是干净的 `'aaaaaaa'` → **毒码被加载**。**V3**：等长破坏且与干净编译落在同一整秒 → 磁盘源码是破坏态、缓存里没有破坏态字面量 → 闸门跑干净字节码 → **假阴性**，drill 会误判 `NOT DETECTED`，看起来像闸门没牙齿 |
| 6 | 这类污染对操作者**完全不可见** | `__pycache__/`（`.gitignore` 第 2 行）与 `*.pyc`（第 3 行）被忽略，污染不出现在 `git status` 里 |

字节差被逐个对上，不是估算：`facts` → `facts_gone` 恰好 **+5**（14262 − 14257 = 5），
`#66CCFF` → `#000` 恰好 **−3**（10055 − 10052 = 3），与第 3 节只读算出的字节差一致。

V1/V2/V3 全部在 `<scratch>` 下的一次性模块上做，**没有碰任何仓库文件、没有碰任何
冻结件**，事后一次性目录已删除。对照实验的必要性：第一版把「写干净源码 / 破坏 /
还原」全压在同一秒内，破坏本身对缓存校验不可见，第 4 步根本没触发重编译，测出的
`POISONED LOADED=False` 是实验设计缺陷造成的假象。第二版用 `sleep 1.2` 把各步分到
不同整秒才测出真实行为。这次返工如实记在 `task_b_after_drill.log` 顶部的
REGENERATION NOTE 里，没有掩盖。

**对当前三个锚点的净结论**：本轮 drill 的 3/3 判定**不受缓存污染影响**——三路锚点
都改变文件长度，size 校验必然拒绝毒缓存，闸门跑的是从已还原源码重编译出来的字节码。
但这层保护是巧合：换一个等长的锚点，V2 或 V3 就会真的发生。

---

## 9. 结论

1. drill 打印 `DRILLS DETECTED: 3 of 3`、退出码 0；drill 自身输出只有这一行（缺陷③）。
2. 三个目标文件 sha256 与 blob 哈希 drill 前后逐个相等，tracked 文件零变动，
   `git status --porcelain -uno` 与 `git diff --stat` 均空。
3. **有效检出改判为 3/3。** 依据是 drill 前 `g0_freeze` 退出码 0（前置绿成立）、
   5 个冻结件对 MANIFEST 5/5 MATCH（drift 唯一来源已消灭）、只读算出的破坏后 sha256
   与 MANIFEST 不等（因果链闭合）、drill 后 `g0_freeze` 输出无 drift 行（确实还原）。
   上一版「第 3 路不可归因、有效检出 2/3」的保留意见**已解除**。
4. 改判**不等于**缺陷①已修：本轮的 3/3 靠外部前置绿快照撑着，drill 自己依然无法
   自证。在集成前那类 `g0_freeze` 恒红的树上，它照样会打印 `3 of 3`。
5. **缺陷④「文本模式改写会整体归一化 CRLF」判定为不成立**，上一版这一条是对代码的
   误读（`sabotage_drill.py` 里没有 `read_text()`，decode/encode 不做换行转换），
   本轮以三路的行尾形态逐个不变 + sha256 逐字节还原作为反证。真正残留的风险是
   SIGKILL/EPERM 造成的**半破坏**，与 LF/CRLF 无关，本轮见到一个同族实例。
6. 手工复验回绿：三个相关闸门全 0、8 格与 drill 前逐格一致、`run_all.py` 双模式
   `PENDING-OK`/0 与 `BLOCKED`/1 且 48 格与三轮基线一致、254 单测全绿。
   这是缺陷②那段死代码的**唯一替代证据**。
7. `__pycache__` 污染确实发生、确实从不清理、确实自愈；挡住它的是 size 校验而非
   mtime 校验，属巧合性保护；等长锚点下会退化成「毒码被加载」（V2）或「闸门假阴性」（V3）。
8. 任务 B 的目标闸门 `g1_memory` 在被定向破坏 `src/memory_store.py` 写入语句时确实变红
   （第 2 路），还原后回到 PASS/0——这是任务 B 交付物「闸门有牙齿」的直接证据，
   且本轮它的前置绿与后置绿都有独立快照，不依赖 drill 的返回值。
