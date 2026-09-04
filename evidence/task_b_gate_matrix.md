# 任务 B 闸门矩阵：三轮 × 双模式 × 八闸门（48 格）

本文件是 rebase 集成上游修复**之后**的最终取证，按最终状态整体重写，不是对上一版的补丁。
上一版记载的「`g0_freeze` 恒 FAIL」「`run_all.py` verdict 恒 FAIL」「`--strict` 永不可达」
三条归因在本轮已全部失效，失效原因见第 5 节；历史观测如实保留在第 6 节，没有抹掉。

所有数字均由命令输出产生，无一处手抄。时间戳来自 `date '+%Y-%m-%d %H:%M:%S %z'`，
行数来自 `wc -l`，退出码来自 `===EXIT=$?===` 标记。

---

## 1. 取证环境

| 项 | 值 | 取得方式 |
|---|---|---|
| commit（三轮全程未变） | `d6868c654a821abf7920d249683837db6068a87a` | `git rev-parse HEAD` |
| 领先 `origin/main` | 39 | `git rev-list --count origin/main..HEAD` |
| 落后 `origin/main` | 0 | `git rev-list --count HEAD..origin/main` |
| 解释器 | Python 3.14.7 | `./.venv/bin/python -VV` |
| 日期 | 2026-09-04，时区 +0100 | 各日志 `start` / `end` 行 |
| 三轮之间有无变动 | 无 | 每轮末实测 `git status --porcelain --untracked-files=no` 与 `git diff --stat` 均为空 |

原始日志（本轮产出，行数由 `wc -l` 给出）：

| 文件 | 行数 |
|---|---|
| `evidence/task_b_round1_normal.log` | 52 |
| `evidence/task_b_round1_strict.log` | 32 |
| `evidence/task_b_round1_unittest.log` | 14 |
| `evidence/task_b_round2_normal.log` | 52 |
| `evidence/task_b_round2_strict.log` | 32 |
| `evidence/task_b_round2_unittest.log` | 14 |
| `evidence/task_b_round3_normal.log` | 52 |
| `evidence/task_b_round3_strict.log` | 32 |
| `evidence/task_b_round3_unittest.log` | 14 |
| 合计 | 294 |

`normal` 日志比 `strict` 多 20 行，差值来自本轮追加在 normal 日志尾部的一段：
单独复跑 `g1_memory`（目标闸门）与 `g0_freeze`（集成前曾经的缺陷闸门）各一次，
含命令、时间戳、stdout、stderr、退出码。这是第 2 步第 4 项要求的独立复核，
不依赖 `run_all.py` 的子进程结果。

---

## 2. 48 格明细

行是闸门，列是「轮次 × 模式」。格内是 `run_all.py` 打印的状态词，括号内是等价退出码
（0=PASS，1=FAIL，2=PENDING）。

| 闸门 | R1 normal | R1 strict | R2 normal | R2 strict | R3 normal | R3 strict |
|---|---|---|---|---|---|---|
| `g0_environment`  | PASS (0) | PASS (0) | PASS (0) | PASS (0) | PASS (0) | PASS (0) |
| `g0_secrets`      | PASS (0) | PASS (0) | PASS (0) | PASS (0) | PASS (0) | PASS (0) |
| `g0_freeze`       | PASS (0) | PASS (0) | PASS (0) | PASS (0) | PASS (0) | PASS (0) |
| `g1_contract`     | PASS (0) | PASS (0) | PASS (0) | PASS (0) | PASS (0) | PASS (0) |
| `g1_memory`       | PASS (0) | PASS (0) | PASS (0) | PASS (0) | PASS (0) | PASS (0) |
| `g1_permissions`  | PENDING (2) | PENDING (2) | PENDING (2) | PENDING (2) | PENDING (2) | PENDING (2) |
| `g1_tools`        | PENDING (2) | PENDING (2) | PENDING (2) | PENDING (2) | PENDING (2) | PENDING (2) |
| `g3_simulate`     | PASS (0) | PASS (0) | PASS (0) | PASS (0) | PASS (0) | PASS (0) |

**格数核算**：8 闸门 × 3 轮 × 2 模式 = 48 格。其中 PASS 36 格、PENDING 12 格、
**FAIL 0 格**。12 格 PENDING 全部落在 `g1_permissions` 与 `g1_tools` 两行（各 6 格）。

闸门状态本身与模式无关（`run_all.py` 对两种模式跑的是同一批闸门、同一套退出码判定），
模式只改变第 49 行的 verdict 归并与第 63 行的进程退出码——这一点在第 3 节展开。

### 2.1 焦点闸门的单独复跑（不经 `run_all.py`）

| 轮次 | `g1_memory` 退出码 | `g1_memory` 时间戳 | `g0_freeze` 退出码 | `g0_freeze` 时间戳 |
|---|---|---|---|---|
| R1 | 0 | 2026-09-04 11:02:17 +0100 | 0 | 2026-09-04 11:02:17 +0100 |
| R2 | 0 | 2026-09-04 11:02:24 +0100 | 0 | 2026-09-04 11:02:24 +0100 |
| R3 | 0 | 2026-09-04 11:02:31 +0100 | 0 | 2026-09-04 11:02:31 +0100 |

两者 stdout 分别为单行 `G1_MEMORY: PASS` 与 `G0_FREEZE: PASS`，stderr 均为空。
`g1_memory` 是本任务的交付闸门；`g0_freeze` 是集成前连续多轮 FAIL 的那一个，
这里逐轮单独复跑，是为了让「它现在真的是绿的」这件事有一份不经编排器的独立证据。

---

## 3. 每轮 verdict / 退出码 / evidence JSON / 时间戳

| 轮次 | 模式 | verdict | `run_all.py` 退出码 | 起 | 止 | 生成的 JSON |
|---|---|---|---|---|---|---|
| R1 | normal | `PENDING-OK` | 0 | 11:02:13 | 11:02:13 | `run_20260904_110213.json` |
| R1 | strict | `BLOCKED` | 1 | 11:02:16 | 11:02:17 | `run_20260904_110217.json` |
| R2 | normal | `PENDING-OK` | 0 | 11:02:20 | 11:02:20 | `run_20260904_110220.json` |
| R2 | strict | `BLOCKED` | 1 | 11:02:23 | 11:02:24 | `run_20260904_110224.json` |
| R3 | normal | `PENDING-OK` | 0 | 11:02:27 | 11:02:27 | `run_20260904_110227.json` |
| R3 | strict | `BLOCKED` | 1 | 11:02:30 | 11:02:31 | `run_20260904_110231.json` |

时间均为 2026-09-04，+0100。六次调用产出六个互不相同的 JSON 文件名，实测
`ls -1 evidence/run_*.json` 中六个都在。

**关于同秒覆盖**：`run_all.py` 第 59 行用 `time.strftime('%Y%m%d_%H%M%S')` 命名 evidence
文件，粒度只到秒。两次调用若落在同一秒，后一次会静默覆盖前一次，且不会报错——上一轮
就是这样丢了 R1 normal 的 JSON。本轮在**每次** `run_all.py` 调用前 `sleep 3`，六次调用的
起始秒分别为 :13 / :16 / :20 / :23 / :27 / :30，两两相差 3 或 4 秒，无一同秒。
上一轮记录的这条偏离本轮**未再发生**。

单测三轮：

| 轮次 | 命令 | 用例数 | 结果 | 退出码 | 耗时 |
|---|---|---|---|---|---|
| R1 | `unittest discover -s tests -p "test_*.py" -t tests` | 254 | OK | 0 | 0.163s |
| R2 | 同上 | 254 | OK | 0 | 0.159s |
| R3 | 同上 | 254 | OK | 0 | 0.162s |

`-t tests` 是必需的：用 `-t .` 会报 `ImportError: Start directory is not importable`，
因为 `tests/` 下没有 `__init__.py`，顶层目录不能当作包的起点。

---

## 4. 每个非 PASS 格的逐条归因

48 格里没有任何 FAIL，需要归因的是 12 格 PENDING 与 3 次 `BLOCKED` verdict。

### 4.1 `g1_permissions` PENDING（6 格：R1/R2/R3 × normal/strict）

闸门 stdout 原文：

```
evaluate() not implemented (Task C)
G1_PERMISSIONS: PENDING
```

归因：`src/permissions.py` 的 `evaluate()` 属**任务 C** 的交付面，任务 C 至今未被认领，
该函数仍是初始态。闸门按既定协议返回 2（PENDING）而不是 1（FAIL），表达的正是
「这一格还没有人交付，不是交付了但不合格」。任务 B 既不拥有也不修改这个文件
（它在第 1 步第 3 项的冻结区 diff 清单里，实测 `origin/main..HEAD` 对该路径零改动）。

### 4.2 `g1_tools` PENDING（6 格：R1/R2/R3 × normal/strict）

闸门 stdout 原文：

```
openai_schema/execute not implemented (Task E)
G1_TOOLS: PENDING
```

归因同上，属**任务 E** 未认领。`src/tools_registry.py` 同样在冻结区清单内，
任务 B 对它零改动。

### 4.3 `--strict` 三次 verdict = `BLOCKED`、退出码 1

归因落在 `run_all.py` 第 49 行的 verdict 归并逻辑，原文：

```python
verdict = "FAIL" if any(r["status"] == "FAIL" for r in results) else ("PENDING-OK" if not strict else ("PASS" if all(r["status"] == "PASS" for r in results) else "BLOCKED"))
```

拆开读：

1. 先看有没有任何闸门 FAIL。本轮 48 格零 FAIL，所以**不走** `FAIL` 分支。
2. 非 strict 模式到这里就返回 `PENDING-OK`——普通模式容忍 PENDING，退出码 0
   （第 63 行 `return 1 if verdict == "FAIL" or (strict and verdict == "BLOCKED") else 0`）。
3. strict 模式再问一句「是不是 8 个闸门全 PASS」。因为 `g1_permissions` 与 `g1_tools`
   是 PENDING，答案是否，于是落到 `BLOCKED`，退出码 1。

所以 `BLOCKED` 的成因**唯一**：两个未认领任务的正当 PENDING。它不是缺陷信号，
也不含任何 FAIL 成分。这正是 strict 模式被设计出来的用途——DoD 口径下
「还没人交付」与「交付合格」必须区分开，不能因为普通模式绿了就算完。

反过来说，`--strict` 要变绿，充要条件是任务 C 与任务 E 各自交付并让对应闸门返回 0。
任务 B 无法、也不应该通过任何手段让它变绿：改闸门、改冻结件、给未实现的函数塞一个
假的返回值，都是把「未完成」伪装成「已完成」。

### 4.4 普通模式 `PENDING-OK` 与 strict 模式 `BLOCKED` 同时成立是否矛盾

不矛盾，两者是同一份闸门结果在两种验收口径下的归并。同一轮里 normal 与 strict 跑出的
8 个闸门状态逐格相同（见第 2 节），差别只在编排器怎么归并。把两种模式都留档，
是为了让读者能自己验证这一点，而不是只看到一个结论。

---

## 5. 集成后归因的改写：`g0_freeze` 为什么从 FAIL 变成 PASS

上一版取证文档里，`g0_freeze` 是持续 FAIL 的，唯一漂移项是 `vendor/agent_core/harness.py`
的 sha256 与 `acceptance/MANIFEST.json` 记载不符；当时定案为上游真缺陷，走「闸门异议」流程，
并且明确不许在本仓改冻结件、不许改 MANIFEST、不许跑 `g0_freeze.py --update`。

本轮起点已包含 rebase 集成进来的上游那 1 个 commit（`origin/main` =
`10c05d1`，subject：`fix: regenerate frozen MANIFEST (CRLF bootstrap drift) + force LF via .gitattributes`）。
它做了两件事：按当前字节重算 `acceptance/MANIFEST.json`，以及新增 `.gitattributes`
（单行 `* text=auto eol=lf`）从源头消除 CRLF 引导漂移。

实测结果：

- `g0_freeze` 退出码 0，stdout 单行 `G0_FREEZE: PASS`（三轮 × 双模式共 6 格全 PASS，
  外加第 2.1 节 3 次单独复跑全 0）。
- 5 个冻结件 sha256 对新 MANIFEST **5/5 匹配**，其中 `vendor/agent_core/harness.py`
  的记载值已是 `cb1ae928f80674952c4ac6e6385d260a7dbd5cf93ac5ab96889ff6bdb32b2807`
  （集成前记载的是 `219691162b9f09b8e544acaff6a39ac613ba2027d5b2ba9b2713875934ea8da5`）。
  其余 4 个冻结件的记载值未变。
- `acceptance/evals/scenarios.json` 的 eol 残留探针全绿：`git ls-files --eol` 报
  `i/lf w/lf attr/text=auto eol=lf`；工作树 CR 计数 0、LF 计数 118、字节数 2752、
  sha256 `2c5dab3fc5e414680193c7b998bb62cf9fe3c6299f2f002682a75efa8179b00e`；
  `git hash-object`、`git hash-object --no-filters`、`git rev-parse HEAD:<path>`
  三者同为 `53ab5c2bf54027f3e333e0f980259acbe0e72150`，证明索引、工作树、HEAD
  三处字节一致且没有残留的 eol 转换。
- 本地 `.git/info/attributes` 里那条临时的 CRLF 规则已撤销——该文件现在**不存在**。

所以「`g0_freeze` 恒 FAIL」「verdict 恒 FAIL」「harness.py 漂移待裁决」这三条旧归因
本轮一律不成立：漂移已由**上游独立裁决并修复**，不是本仓自己动手让闸门变绿。
这一点很关键——本仓全程没有改过任何冻结件，没有改过 MANIFEST，没有跑过
`g0_freeze.py --update`；第 1 步第 3 项的冻结区 diff（含 `.gitattributes`）实测为空。

连带地，「`--strict` 永不可达」这条旧说法也要改写：strict 现在**可达**，
只差任务 C 与任务 E 两个未认领项；它不绿的原因从「一个真缺陷 + 两个未完成」
收敛成「只有两个未完成」，见第 4.3 节。

---

## 6. 历史如实保留

集成前，本仓曾连续多轮观测到 `g0_freeze` FAIL、`run_all.py` 普通模式 verdict FAIL、
退出码 1。当时经用户拍板，采用「**双份证据 + 逐闸门明细**」的方案来交付 DoD a 项：
既留编排器的整体 verdict，也留每个闸门的单独退出码与完整输出，让读者能自己判断
FAIL 究竟来自哪一格，而不是被一个汇总词挡住。

集成之后该方案**仍然保留**，但保留的理由变了，而且变得更强：

- 集成前它的作用是**自证清白**——把唯一的 FAIL 精确定位到 `g0_freeze` 的一格，
  并说明那是上游缺陷而非任务 B 的交付问题。
- 集成后它的作用是**证明一件更强的事**：`--strict` 不绿的原因**唯一且正当**。
  有了 48 格明细，读者可以直接数出 FAIL 为 0、PENDING 为 12 且全部落在两行，
  从而确认 `BLOCKED` 完全由任务 C/E 未认领造成，没有任何被汇总词掩盖的缺陷。
  这是单看一个 verdict 得不到的结论。

两份历史与本轮结果并不冲突，也不需要为了「看起来一直没问题」而抹掉前者——
抹掉会与 `evidence/task_b_gate_objections.md` 的闸门异议卷宗对不上。

> 本轮排除说明：`evidence/task_b_gate_objections.md` 由另一位工程师并行修改中，
> 本文件未读取、未引用其行数与内容，也未把它纳入任何扫描或统计。
> 该文件由最终 push 前检查单独扫。

---

## 7. 结论

1. **`g1_memory` 三轮全 PASS**（6 格 PASS，另有 3 次不经编排器的单独复跑全为退出码 0）。
2. **`g0_freeze` 三轮全 PASS**（6 格 PASS，另有 3 次单独复跑全为退出码 0），
   5 个冻结件 sha256 对新版 MANIFEST 5/5 匹配。
3. **48 格零 FAIL**：PASS 36 格、PENDING 12 格，PENDING 全部归因于任务 C/E 未认领。
4. 普通模式三轮 verdict 均为 `PENDING-OK`、退出码 0；strict 模式三轮均为 `BLOCKED`、
   退出码 1，成因唯一（`run_all.py` 第 49 行对 PENDING 的既定处理）。
5. 单测三轮均为 254 用例全绿、退出码 0。
6. 三轮之间工作区无任何变动：每轮末 `git status --porcelain --untracked-files=no`
   与 `git diff --stat` 均为空，commit 全程钉在 `d6868c6`。
7. 上一轮的「同秒覆盖丢 JSON」偏离本轮靠 `sleep 3` 未再发生，六份 JSON 齐全。
