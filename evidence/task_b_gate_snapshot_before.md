# 任务 B（记忆系统）闸门快照：本轮前置绿 + 上一轮开工前历史留档

本文件按 rebase 集成上游修复**之后**的最终状态整体重写，不是对上一版的补丁。
它分两半，两半都是必要的：

- **第一半（第 1–4 节）是本轮的前置快照**，即最终验收轮在 `d6868c6` 这棵树上、
  做任何破坏性演练**之前**的绿基线。drill 的「前置绿」断言只能由外部快照撑着
  （`acceptance/sabotage_drill.py` 自己不做前置断言，这是它的缺陷①），
  第 2 节就是那根撑杆。
- **第二半（第 5–6 节）是上一轮开工前快照的历史留档**，逐条标注哪些归因已被
  集成推翻、哪些仍然成立。留着它不是为了好看：Sarah 的闸门异议卷宗
  （`evidence/task_b_gate_objections.md`）记录的是**集成前**的观测，
  如果把历史抹掉装作一直没问题，两边会对不上。

所有数字均由命令输出产生，无一处手抄：时间戳来自 `date '+%Y-%m-%d %H:%M:%S %z'`
或快照脚本内嵌的 `time.strftime`，行数来自 `wc -l`，哈希来自 `git hash-object` /
`hashlib.sha256`，退出码来自子进程 `returncode`。

## 0. 定位锚点

> **【关于 commit hash 的显式标注】本文件里出现的 commit hash 是 author 改写前的值。**
> push 前全部本地 commit 的 author 会被改写为与上游那个 commit 一致的身份，
> 改写后**所有 commit hash 全部失效**。长期有效的稳定锚点是 **blob 哈希与 tree 哈希**，
> 以及 commit 的 **subject + 序数**：author 改写不动 tree 也不动 blob，
> 这两类哈希在改写前后逐字不变。复核时请勿拿本文件里的 commit hash 去 `git show`，
> 那会打不到东西、并误判成证据造假。
>
> **这不是假想风险，第 5.1 节里就有一个已经发生过的实例**：上一版本文件记录的
> 7 个 commit hash 里有 6 个已经因为 rebase 换基而失效了。

| 锚点 | 值 | 取得方式 |
|---|---|---|
| commit（本轮全程未变） | `d6868c654a821abf7920d249683837db6068a87a`（短 `d6868c6`，第 **39** 条） | `git rev-parse HEAD` |
| **HEAD tree（稳定锚点）** | `37d26de723f1571ec3c6aa0cced25f2794eece68` | `git rev-parse HEAD^{tree}` |
| 基底 = `origin/main` | `10c05d116e58886f3a9366c99cbdc214e9bdfae4`，author `SummerTianYi` | `git log -1 origin/main` |
| 基底 subject | `fix: regenerate frozen MANIFEST (CRLF bootstrap drift) + force LF via .gitattributes` | 同上 |
| ahead / behind | **39 / 0** | `git rev-list --left-right --count origin/main...HEAD` |

上游身份的完整写法（含 email）不抄进本文件，需要时用 `git log -1 origin/main` 现取——
它本来就在那棵树的 git 历史里，不是需要靠证据文档保存的信息。

原始快照文件（本轮生成，落在仓库外的临时目录，所以内容整份嵌在下面各节里，
不靠外部引用）：`<scratch>/snap_step1_baseline.txt`（93 行）、
`<scratch>/snap_step3_predrill.txt`（93 行），行数由 `wc -l` 取。
消毒规则：仓库根记作 `<repo>`，仓库外临时目录记作 `<scratch>`，
用户家目录前缀记作 `<home>`；实质数值逐字未改。

## 1. 本轮前置快照：step 1.6 baseline（2026-09-04 10:55:16 +0100）

8 个闸门**逐个单独跑**，不经 `run_all.py`。为什么必须单独跑：`run_all.py` 只取
子进程 stdout 末尾 400 字符并丢弃 stderr（第 42–44 行 `capture_output=True`、
第 44 行 `proc.stdout.strip()[-400:]`），编排器输出里看不到 traceback。

### 1.1 逐格结果

| 闸门 | 命令 | verdict | 退出码 | 本轮期望 | 一致 |
|---|---|---|---|---|---|
| g0_environment | `./.venv/bin/python acceptance/gates/g0_environment.py` | PASS | 0 | PASS/0 | 是 |
| g0_secrets | `./.venv/bin/python acceptance/gates/g0_secrets.py` | PASS | 0 | PASS/0 | 是 |
| **g0_freeze** | `./.venv/bin/python acceptance/gates/g0_freeze.py` | **PASS** | **0** | **PASS/0** | 是 |
| g1_contract | `./.venv/bin/python acceptance/gates/g1_contract.py` | PASS | 0 | PASS/0 | 是 |
| g1_memory | `./.venv/bin/python acceptance/gates/g1_memory.py` | PASS | 0 | PASS/0 | 是 |
| g1_permissions | `./.venv/bin/python acceptance/gates/g1_permissions.py` | PENDING | 2 | PENDING/2 | 是 |
| g1_tools | `./.venv/bin/python acceptance/gates/g1_tools.py` | PENDING | 2 | PENDING/2 | 是 |
| g3_simulate | `./.venv/bin/python acceptance/gates/g3_simulate.py` | PASS | 0 | PASS/0 | 是 |

`TOTAL: PASS=6 FAIL=0 PENDING=2 (of 8)`，退出码序列 **0/0/0/0/0/2/2/0**，
与本轮期望矩阵逐格一致，零偏离。**FAIL 数为 0**——这是与上一轮最要紧的差别
（上一轮这里是 `0/0/1/0/0/2/2/0`，`g0_freeze` 恒 FAIL）。

### 1.2 完整原始输出（快照脚本全文，stderr 已合并）

```
========================================================================
GATE SNAPSHOT  label=step1.6-baseline
wall-clock start = 2026-09-04 10:55:16 +0100
HEAD             = d6868c654a821abf7920d249683837db6068a87a
========================================================================

------------------------------------------------------------------------
GATE g0_environment   exit=0 (PASS)   elapsed=0.04s
  cmd: ./.venv/bin/python acceptance/gates/g0_environment.py
------------------------------------------------------------------------
--- stdout ---
G0_ENVIRONMENT: PASS
--- stderr ---
(empty)

------------------------------------------------------------------------
GATE g0_secrets   exit=0 (PASS)   elapsed=0.03s
  cmd: ./.venv/bin/python acceptance/gates/g0_secrets.py
------------------------------------------------------------------------
--- stdout ---
G0_SECRETS: PASS
--- stderr ---
(empty)

------------------------------------------------------------------------
GATE g0_freeze   exit=0 (PASS)   elapsed=0.02s
  cmd: ./.venv/bin/python acceptance/gates/g0_freeze.py
------------------------------------------------------------------------
--- stdout ---
G0_FREEZE: PASS
--- stderr ---
(empty)

------------------------------------------------------------------------
GATE g1_contract   exit=0 (PASS)   elapsed=0.07s
  cmd: ./.venv/bin/python acceptance/gates/g1_contract.py
------------------------------------------------------------------------
--- stdout ---
G1_CONTRACT: PASS
--- stderr ---
(empty)

------------------------------------------------------------------------
GATE g1_memory   exit=0 (PASS)   elapsed=0.04s
  cmd: ./.venv/bin/python acceptance/gates/g1_memory.py
------------------------------------------------------------------------
--- stdout ---
G1_MEMORY: PASS
--- stderr ---
(empty)

------------------------------------------------------------------------
GATE g1_permissions   exit=2 (PENDING)   elapsed=0.03s
  cmd: ./.venv/bin/python acceptance/gates/g1_permissions.py
------------------------------------------------------------------------
--- stdout ---
evaluate() not implemented (Task C)
G1_PERMISSIONS: PENDING
--- stderr ---
(empty)

------------------------------------------------------------------------
GATE g1_tools   exit=2 (PENDING)   elapsed=0.03s
  cmd: ./.venv/bin/python acceptance/gates/g1_tools.py
------------------------------------------------------------------------
--- stdout ---
openai_schema/execute not implemented (Task E)
G1_TOOLS: PENDING
--- stderr ---
(empty)

------------------------------------------------------------------------
GATE g3_simulate   exit=0 (PASS)   elapsed=0.06s
  cmd: ./.venv/bin/python acceptance/gates/g3_simulate.py
------------------------------------------------------------------------
--- stdout ---
G3_SIMULATE: PASS
--- stderr ---
(empty)

========================================================================
SUMMARY  gate -> exit code
========================================================================
  g0_environment   0  PASS
  g0_secrets       0  PASS
  g0_freeze        0  PASS
  g1_contract      0  PASS
  g1_memory        0  PASS
  g1_permissions   2  PENDING
  g1_tools         2  PENDING
  g3_simulate      0  PASS
  TOTAL: PASS=6 FAIL=0 PENDING=2  (of 8)
wall-clock end   = 2026-09-04 10:55:16 +0100
```

注意 `g0_freeze` 的 stdout 只有一行 `G0_FREEZE: PASS`，**没有任何
`content drifted from frozen manifest` 行**。上一轮这里输出的是
`vendor/agent_core/harness.py: content drifted from frozen manifest`。

## 2. 本轮 drill 前绿快照：step 3.1（2026-09-04 11:05:02 +0100）

这份快照的存在理由是 drill 的缺陷①：`acceptance/sabotage_drill.py` 全程
**不做任何前置绿断言**，它只在破坏之后看闸门红不红。所以「破坏前是绿的」
这句话必须由外部快照来证，否则 drill 的检出结论是悬空的。

与第 1 节的 baseline 做 `diff`，差异**只有 5 处**，且全部是标签与耗时：

```
2,3c2,3
< GATE SNAPSHOT  label=step1.6-baseline
< wall-clock start = 2026-09-04 10:55:16 +0100
---
> GATE SNAPSHOT  label=step3.1-pre-drill-green
> wall-clock start = 2026-09-04 11:05:02 +0100
26c26
< GATE g0_freeze   exit=0 (PASS)   elapsed=0.02s
---
> GATE g0_freeze   exit=0 (PASS)   elapsed=0.03s
35c35
< GATE g1_contract   exit=0 (PASS)   elapsed=0.07s
---
> GATE g1_contract   exit=0 (PASS)   elapsed=0.05s
73c73
< GATE g3_simulate   exit=0 (PASS)   elapsed=0.06s
---
> GATE g3_simulate   exit=0 (PASS)   elapsed=0.05s
93c93
< wall-clock end   = 2026-09-04 10:55:16 +0100
---
> wall-clock end   = 2026-09-04 11:05:02 +0100
```

读法：两份 93 行的快照，**8 个退出码逐格相同、8 段 stdout 逐字相同、
8 段 stderr 逐字相同**，只有 label、两处 wall-clock、以及 `g0_freeze` /
`g1_contract` / `g3_simulate` 三个闸门的 elapsed（0.02→0.03、0.07→0.05、
0.06→0.05，都是百分之一秒量级的调度抖动）不一样。

这说明第 1 步到第 3 步之间（10:55:16 → 11:05:02，间隔约 10 分钟，
中间跑了三轮 `run_all.py` 双模式与 254 个单测）**什么都没漂**：
没有任何一次取证动作改动过被闸门看的东西。这条比「drill 前是绿的」更强，
因为它同时排除了「取证过程自己把树弄脏了」这种可能。

## 3. 冻结件 sha256 与 EOL 残留探针（本轮实测）

复算方式：读 `acceptance/MANIFEST.json`，逐个
`hashlib.sha256(path.read_bytes()).hexdigest()` 与期望值比对。
下表取自 `evidence/task_b_final_check.log` 的 B 节（2026-09-04 17:04:03，
即本轮收尾复算），与第 1 节前置快照同树同值——中间隔着 drill 的破坏与还原，
5 件全部回到原值，这一点在 `evidence/task_b_sabotage_drill.md` 第 4 节有逐件比对。

| 冻结件 | MANIFEST 期望 | 实际复算 | 结论 |
|---|---|---|---|
| vendor/agent_core/harness.py | `cb1ae928f80674952c4ac6e6385d260a7dbd5cf93ac5ab96889ff6bdb32b2807` | 同左 | MATCH |
| vendor/agent_core/song_catalog.py | `57d257d1084a67271a78a3b79393839c1442d37499c8a25862d80071a411e49e` | 同左 | MATCH |
| vendor/agent_core/voice_text.py | `c652a1b868029a5f1d46b23e1720af44363081ce441c1ff008bcc86f913e4da8` | 同左 | MATCH |
| vendor/agent_core/data/luotianyi_original_songs.json | `22552757d32c86e1bf9d52217c3c3ff588bd35a86ba1ceada6707198f2710f8d` | 同左 | MATCH |
| acceptance/evals/scenarios.json | `2c5dab3fc5e414680193c7b998bb62cf9fe3c6299f2f002682a75efa8179b00e` | 同左 | MATCH |

`RESULT: 5/5 match`。

EOL 残留探针（`acceptance/evals/scenarios.json`，即上一轮出问题的 CRLF 那一件）：

```
  .git/info/attributes does NOT exist
  git ls-files --eol acceptance/evals/scenarios.json  (exit=0)
      i/lf    w/lf    attr/text=auto eol=lf     acceptance/evals/scenarios.json
  git check-attr -a acceptance/evals/scenarios.json  (exit=0)
      acceptance/evals/scenarios.json: text: auto
      acceptance/evals/scenarios.json: eol: lf
  worktree bytes      = 2752
  worktree CR count   = 0
  worktree LF count   = 118
  worktree sha256     = 2c5dab3fc5e414680193c7b998bb62cf9fe3c6299f2f002682a75efa8179b00e
  git hash-object              = 53ab5c2bf54027f3e333e0f980259acbe0e72150
  git hash-object --no-filters = 53ab5c2bf54027f3e333e0f980259acbe0e72150
  git rev-parse HEAD:acceptance/evals/scenarios.json    = 53ab5c2bf54027f3e333e0f980259acbe0e72150
  all three equal              = True
  bytes == 2752                = True  (actual 2752)
  sha256 == expected           = True
  CR count == 0                = True
```

四个要点：

1. `.git/info/attributes` **不存在**——上一轮为了排查 CRLF 而临时加的本地规则已撤销，
   现在唯一生效的 EOL 规则来自 tracked 的 `.gitattributes`（`* text=auto eol=lf`），
   它对每个 clone 都一致，不是本机私有配置。
2. `i/lf w/lf`：index 与工作区都是 LF，**没有残留转换**。
3. `git hash-object` == `--no-filters` == `git rev-parse HEAD:<path>`，三者相等。
   这是「过滤器链在这件上不做任何事」的充要证据：带过滤与不带过滤算出同一个 blob，
   且与 HEAD 里存的那个 blob 相同。
4. `CR count = 0`、`bytes = 2752`。上一轮这件是 `CR count = 118`、`bytes = 2870`，
   差值恰好 118 = 每行少一个 `\r`。

## 4. 归因改写：`g0_freeze` 为什么从 FAIL 变成 PASS

这是本轮相对上一轮唯一一处**闸门状态**变化，必须讲清楚是怎么变的，
否则读起来像是有人把闸门调绿了。

### 4.1 上游做了什么

基底 commit `10c05d1`（author `SummerTianYi`）的 subject 自己就说明了：
`fix: regenerate frozen MANIFEST (CRLF bootstrap drift) + force LF via .gitattributes`。
它做了两件事，都不在本地 39 条 commit 里：

1. **重算 `acceptance/MANIFEST.json`**
2. **新增 `.gitattributes`**，内容单行 `* text=auto eol=lf`

本地这一侧没有跑过 `g0_freeze.py --update`（铁律禁止），也没有手改过 MANIFEST。
下面这张逐件对照表就是证明：只有 2 件的期望值变了，另外 3 件逐字未动。

### 4.2 逐件对照：旧 MANIFEST 期望 vs 新 MANIFEST 期望 vs 实际内容

「旧」列取自本文件第 5 节留档的上一轮开工前快照（2026-09-02，`9eade73` 树）。

| 冻结件 | 旧期望 | 新期望 | 旧实际 | 新实际 | 内容变了吗 | 期望变了吗 |
|---|---|---|---|---|---|---|
| harness.py | `219691162b9f09b8…` | `cb1ae928f8067495…` | `cb1ae928f8067495…` | `cb1ae928f8067495…` | **没变** | **变了** |
| song_catalog.py | `57d257d1084a6727…` | `57d257d1084a6727…` | 同期望 | 同期望 | 没变 | 没变 |
| voice_text.py | `c652a1b868029a5f…` | `c652a1b868029a5f…` | 同期望 | 同期望 | 没变 | 没变 |
| luotianyi_original_songs.json | `22552757d32c86e1…` | `22552757d32c86e1…` | 同期望 | 同期望 | 没变 | 没变 |
| scenarios.json | `01ed805ae688e431…` | `2c5dab3fc5e41468…` | `01ed805ae688e431…` | `2c5dab3fc5e41468…` | **变了** | **变了** |

（完整 64 位值见第 3 节与第 5.2 节，此处截前 16 位只为对齐排版。）

### 4.3 这张表说明的两件事

**`harness.py`：内容一个字节没动，是 MANIFEST 的期望值被改成了实际内容。**
旧期望 `219691162b9f…` 与实际 `cb1ae928f806…` 不符 → 旧闸门 FAIL；
新期望直接取 `cb1ae928f806…` → 新闸门 PASS。也就是说上游认定
「bootstrap 时期记进 MANIFEST 的那个哈希是 Windows 环境下算出来的、本身就不对」，
修法不是把 harness.py 改回去，而是把 MANIFEST 重算成仓库里真实的内容。
这一点与 `g0_freeze.py` 第 41–42 行的判据完全对得上：

```
elif expect != sha256(path):
    problems.append(f"{rel}: content drifted from frozen manifest")
```

判据只比较「MANIFEST 期望」与「文件实际 sha256」，所以修哪一边都能让它绿。
上游选择修期望那一边，并且把理由写进了 commit subject（`CRLF bootstrap drift`）。

**`scenarios.json`：内容与期望同时变了，而且变化量精确可解释。**
旧 `01ed805a…` / 2870 字节 / `CR count = 118`；新 `2c5dab3f…` / 2752 字节 /
`CR count = 0`。差值 **2870 − 2752 = 118**，恰好等于消失的 CR 个数。
即 `.gitattributes` 的 `* text=auto eol=lf` 生效后，这件在工作区里被重新归一化成
纯 LF，MANIFEST 随之重算。118 也正是它的行数（`LF count = 118`），
一行一个 `\r`，一个不多一个不少。

### 4.4 因此，下面这些旧归因全部作废

| 旧说法 | 现在的实情 |
|---|---|
| 「`g0_freeze` 恒 FAIL」 | 已 PASS，退出码 0。可数证据：本轮 evidence 日志里 `G0_FREEZE: PASS` 共出现 **13 次**（`task_b_final_check.log` 3、`task_b_after_drill.log` 1、三轮的 `*_normal.log` 各 2 共 6、三轮的 `*_strict.log` 各 1 共 3），加上嵌在本文件第 1、2 节的两份快照各 1 次 = **15 次**；`run_all.py` 编排器输出的 `PASS     g0_freeze` 行共 **10 次**（三轮双模式 6 + drill 后复验 2 + 收尾 2）。而 `content drifted from frozen manifest` 这行在**全部 evidence 文件里只出现 1 次**，且那 1 次在 `task_b_drill_attribution.log` 里、是引用 `g0_freeze.py` 第 42 行的**源码原文**，不是任何一次真实报告 |
| 「verdict 恒 FAIL」 | 普通模式 `PENDING-OK`（exit 0），strict 模式 `BLOCKED`（exit 1），**两者都零 FAIL** |
| 「`--strict` 永不可达」 | `--strict` 现在**可达且必然给出 `BLOCKED`**，原因唯一且正当：`g1_permissions`（Task C 未做）与 `g1_tools`（Task E 未做）仍是 PENDING，而 `run_all.py` 第 49 行要求 strict 下 8 个全 PASS 才不 BLOCKED。这与任务 B 无关，是后续任务的范围 |
| 「harness.py 漂移待裁决」 | 已由上游裁决并修复，走的是「重算 MANIFEST」而不是「回滚文件」 |

「`--strict` 不绿」这件事现在能证明一个**更强**的结论：不绿的原因只剩一个，
而且是正当的（别的任务还没做）。上一轮不绿的原因里混着一条真缺陷
（冻结件哈希不符），那条已经没了。这就是本轮保留双份证据
（普通模式 + strict 模式）与逐闸门明细的价值——它能把「不绿」拆到只剩一条可归因项。

## 5. 历史留档：上一轮开工前快照（2026-09-02，`9eade73` 树）

以下是上一版本文件的实质内容，**原样留档**，只在每条旁边标注现在的状态。
留档的理由见文件开头：Sarah 的闸门异议卷宗记录的是集成前的观测。

### 5.1 版本与提交状态（原文）

```
$ git rev-parse HEAD
9eade730569bf4140f81fb93b857a8c818992e7e

$ git branch --show-current
main

$ git log --oneline
9eade73 docs(memory): 补检索难度分析、留出集结果与主仓集成说明
7faaa7a feat(memory): MemoryStore 增补按查询排序的召回与 prompt 片段格式化
21dd8a0 feat(memory): score_retrieval 落地宏平均查准查全评测
85a4186 feat(memory): 补偏好断言加权与临时状态降权
a3b521d feat(memory): 补概念词典桥接，让无字面重叠的查询能命中
a736da2 feat(memory): 补检索文本归一化与字符 bigram 相似度
a0240e1 feat: workbench bootstrap - task packs, acceptance gates, evidence system

$ git status --porcelain
（空）
```

> **【标注：这 7 个 hash 里 6 个已经失效，现在就失效，不用等 author 改写】**
> rebase 换基（基底从 `a0240e1` 变成 `10c05d1`）已经把这 6 条 commit 全部重写了。
> 同一个 subject 现在的 hash 是：
>
> | 旧 hash（已失效） | 现 hash（author 改写前） | 序数 | subject |
> |---|---|---|---|
> | `a736da2` | `f60e946` | 1 | feat(memory): 补检索文本归一化与字符 bigram 相似度 |
> | `a3b521d` | `a70a1ab` | 2 | feat(memory): 补概念词典桥接，让无字面重叠的查询能命中 |
> | `85a4186` | `80d794a` | 3 | feat(memory): 补偏好断言加权与临时状态降权 |
> | `21dd8a0` | `ed4528f` | 4 | feat(memory): score_retrieval 落地宏平均查准查全评测 |
> | `7faaa7a` | `4e18ffa` | 5 | feat(memory): MemoryStore 增补按查询排序的召回与 prompt 片段格式化 |
> | `9eade73` | `9ab6b8e` | 6 | docs(memory): 补检索难度分析、留出集结果与主仓集成说明 |
> | `a0240e1` | `a0240e1` | — | feat: workbench bootstrap …（**未变**，它是基底的父） |
>
> 唯一没变的是 `a0240e1`，因为它在基底之下、没被 rebase 触碰。
> 这就是第 0 节那段标注的现实依据：**subject + 序数是唯一跨改写稳定的 commit 定位方式**，
> hash 不是。author 改写会发生完全一样的事，只是范围从 6 条变成全部 39 条。

### 5.2 8 闸门与冻结件（原文摘录 + 标注）

原文的闸门表里，`g0_freeze` 那一行是 `FAIL / 1 / 期望 FAIL/1 / 一致 是`，
原始输出是：

```
######## GATE g0_freeze ########
--- cmd: ./.venv/bin/python acceptance/gates/g0_freeze.py
--- start_utc: 2026-09-02T16:39:03Z
vendor/agent_core/harness.py: content drifted from frozen manifest
--- exit_code=1
--- end_utc: 2026-09-02T16:39:03Z
```

原文的冻结件表里，harness.py 那一行是：

```
| vendor/agent_core/harness.py | 219691162b9f09b8e544acaff6a39ac613ba2027d5b2ba9b2713875934ea8da5 |
                                 cb1ae928f80674952c4ac6e6385d260a7dbd5cf93ac5ab96889ff6bdb32b2807 | 漂移 |
```

原文的结论是：「5 个冻结件里 4 匹配、1 漂移，漂移项唯一且为
`vendor/agent_core/harness.py`，与 g0_freeze 的 FAIL 输出完全对应。
该漂移已定案为上游真缺陷（主仓侧 Windows 环境造成），走闸门异议流程上报主仓裁决。」

> **【标注 1：这条观测在当时是准确的，现在已失效】**
> 「上游真缺陷 / 主仓侧 Windows 环境造成 / 上报主仓裁决」这三句判断都被上游自己确认了——
> 基底 commit 的 subject 里 `CRLF bootstrap drift` 就是同一件事的另一种说法。
> 裁决结果是重算 MANIFEST，见第 4 节。现在 `g0_freeze` = PASS/0，5/5 MATCH。
>
> **【标注 2：旧表里那个「实际」值现在成了「期望」值】**
> `cb1ae928f80674952c4ac6e6385d260a7dbd5cf93ac5ab96889ff6bdb32b2807`
> 在旧表里是 harness.py 的**实际** sha256（被判为漂移），
> 在新表里它是 MANIFEST 的**期望** sha256（判为 MATCH）。
> 文件本身从头到尾没变过——这一点在本轮 drill 里又被独立验证了一次：
> drill 前后 harness.py 的 blob 哈希都是 `29dca70bcc740976910cd0f85d38f2ce9034795c`。
>
> **【标注 3：`scenarios.json` 的旧值两处都过期了】**
> 旧期望与旧实际都是 `01ed805ae688e431a8f09bf64d21d445cdf26e85843c6fd9d08b58332df42e67`，
> 现在两处都是 `2c5dab3fc5e414680193c7b998bb62cf9fe3c6299f2f002682a75efa8179b00e`，
> 归因见第 4.3 节（`.gitattributes` 归一化，−118 字节）。
> 另外 3 件（song_catalog / voice_text / luotianyi）旧新两版逐字相同，**没有过期**。

原文还给了 drill 目标的前置基准哈希，其中 harness.py 记的是
`cb1ae928f8067495…`（标「是（已漂移）」）、scenarios.json 记的是
`01ed805ae688e431…`（标「是（匹配）」）。

> **【标注 4：这两条基准现在一新一旧】**
> harness.py 的 `cb1ae928…` **仍然有效**（文件没变），只是「已漂移」这个标签作废。
> scenarios.json 的 `01ed805a…` **已作废**，本轮 drill 用的是 `2c5dab3f…`。
> 本轮 drill 三个目标的实际前置基准（blob 哈希，稳定锚点）是：
> harness.py `29dca70bcc740976910cd0f85d38f2ce9034795c`、
> src/memory_store.py `49d273aa9286afdf4d6f649b915c56042c9354e1`、
> acceptance/evals/scenarios.json `53ab5c2bf54027f3e333e0f980259acbe0e72150`，
> 三者都满足 `git hash-object` == `git rev-parse HEAD:<path>`。

### 5.3 单元测试（原文 + 标注）

```
$ ./.venv/bin/python -m unittest discover -s tests
......................................................
----------------------------------------------------------------------
Ran 54 tests in 0.027s

OK
```

原文的说明是：「退出码 0，54 个用例全绿（`tests/test_memory_retrieval.py` 51 个 +
`tests/test_workbench.py` 3 个）。」

> **【标注：54 这个数字已过期，本轮是 254；命令也少了两个参数】**
> 现在是 `Ran 254 tests`，退出码 0，全绿（见第 6.1 节）。
> 增长来自两条：一是任务 B 后续阶段新增的测试，二是第 31 条 commit
> （subject `test(memory): N4 拆分 test_memory_retrieval.py 为三文件（纯搬移，219 项不变）`）
> 把原来那一个大文件拆成了三个。原文那条命令 `discover -s tests` 没带 `-t`，
> 本轮统一用 `-t tests`——用 `-t .` 会报
> `ImportError: Start directory is not importable`，这个坑本轮踩过并记进了任务口径。

### 5.4 检索质量基线（原文 + 标注）

```
GOLDEN         precision=1.000000 recall=1.000000   top1 命中 8/8
HOLDOUT_GOLDEN precision=1.000000 recall=1.000000   top1 命中 12/12
```

以及逐条 top-1 分数表（GOLDEN 8 条：0.540349 / 0.422183 / 0.461625 / 0.580293 /
0.476211 / 0.541272 / 0.331695 / 0.428877；HOLDOUT 12 条：0.513415 / 0.372892 /
0.315089 / 0.382019 / 0.450754 / **0.050000** / 0.321291 / 0.426955 / 0.368474 /
0.325000 / 0.397183 / 0.447775），原文的结论是：

「留出集第 6 条（「用户吃不了什么」→「用户对海鲜过敏」）基线分只有 0.05，
是全 20 条里最薄的一条：查询与事实无字面重叠、无共同概念类命中
（「吃不了」不在过敏类 member 里），只能靠对手项「用户是一名厨师」更低的分取胜。
这条样例对任何降权/加权改动都最脆弱，第 3 步破坏实验要重点看它。」

> **【标注 1：两个 1.000000 仍然成立】**
> 本轮实测 golden 8/8 P=R=1.0000、v1 12/12 P=R=1.0000，与原文一致。
>
> **【标注 2：「全 20 条」已过期，现在是 52 对】**
> 原文那时只有 golden(8) + v1(12) = 20 对。v2 语料（32 对）是后来第 16、22 条 commit
> 才接进来并纳入版本控制的，所以现在三集合计 8 + 12 + 32 = **52 对**。
> v2 上本轮实测 P=0.7742、R=0.7500、命中 24/32。
>
> **【标注 3：「第 6 条最薄」这条判断仍然成立，但要说清是哪种薄】**
> 原文给的 0.050000 是那一对的 **top-1 分数**。本轮独立测的是 **min_margin**
> （命中对里最小的 top1−top2 分差），v1 上是 **0.0500 @#5**（0 基，即 1 基的第 6 对）——
> 两个 0.05 指的是同一对，但量纲不同，别混读。
> 本轮还测出这条余量**全部由 L4（偏好层）提供**：把 `W_PREFERENCE` 置 0 后，
> v1 的 min_margin 从 0.0500 压到 **0.0000**（即变成 0 分差命中，指标却仍然满分）。
> 这推翻了旧 `task_b_self_sabotage.md` 里「基线 min_margin 已经是 0」的说法，
> 详见该文件第 9.3 节 F4' 条。
>
> **【标注 4：上一版 `self_sabotage.md` 声称「golden 在同一路变异下读作 0.875」，已过期】**
> 那个 0.875 出自 `9eade73` 这棵树（旧日志原文 `GOLDEN precision=0.875000
> recall=0.875000`、`top1 命中 7/8`）。在最终树上同一路变异（清空词典全部 member）
> 实测 golden = **1.0000**、v1 = **0.6667**。三个读数对应三棵不同的树，
> 而 v1 = 0.6667 在三棵树上**完全未变**——退化总量没变，只是从闸门看得见的集
> 搬到了闸门看不见的集。完整对照见 `evidence/task_b_self_sabotage.md` 第 9.4 节。
>
> 引文来源说明（不留悬空引用）：上面引的 `0.875000` 与 `top1 命中 7/8` 取自上一版
> `task_b_self_sabotage.log`（634 行），引文是在本轮**覆盖它之前**用 `grep -n` 拓下来的原文，
> 当时同时记下了行号（116、128）。那份日志已被本轮整份覆盖，而且它是 untracked、
> 从未进过 commit，所以也不在 git 历史里；读者无法再 `sed` 到那两行，这一点如实说明，
> 不假装可验。

### 5.5 evidence/ 目录状态（原文 + 标注）

原文：「`evidence/run_*.json` 已有 8 个（`.gitignore` 忽略，不入库）」，
列的是 `run_20260902_153821.json` 到 `run_20260902_173423.json` 共 8 个；
已跟踪的 evidence 文档是 `README.md`、`task_b_integration.md`、
`task_b_retrieval_analysis.md`。

原文最后一段：「`evidence/README.md` 规则 3 写的是「提交前删除过期运行记录，
保留最后 10 条」，但 `run_all.py` 自身没有任何裁剪逻辑（第 57–60 行只写不删），
且开工前已累积 8 个。本次取证 3 轮 ×2 模式再加 drill 后复跑，总数会超过 10 条。
取证者不删除他人留下的运行记录，只把这条口径冲突记进发现清单。」

> **【标注：这条口径冲突仍然成立，而且缺口更大了】**
> 本轮收尾时 `evidence/run_*.json` 共 **60 个**（`ls evidence/run_*.json | wc -l`），
> 规则写的上限是 10 条，超出 50 条。tracked 的 evidence 文档仍然是那 3 份
> （`README.md` 8 行、`task_b_integration.md`、`task_b_retrieval_analysis.md`，
> 后两份是 Lee 的已定稿交付物，本轮只读不改）。
> 「取证者不删除他人留下的运行记录」这个处置本轮沿用：60 个 JSON 一个没删，
> 也一个没 `git add`（它们被 `.gitignore` 忽略，任务书明确要求不强制 add）。

## 6. 本轮前置状态的其余口径

### 6.1 单元测试

`./.venv/bin/python -m unittest discover -s tests -p "test_*.py" -t tests`
→ `Ran 254 tests in 0.165s` / `OK` / 退出码 **0**（2026-09-04 17:04:03）。
三轮取证里分别是 0.163s / 0.159s / 0.162s，都是 254 全绿
（见 `evidence/task_b_gate_matrix.md` 第 3 节）。

### 6.2 `run_all.py` 双模式

| 模式 | verdict | 退出码 | FAIL 数 | PENDING 数 | evidence JSON |
|---|---|---|---|---|---|
| 普通 | `PENDING-OK` | 0 | 0 | 2 | `run_20260904_170407.json` |
| `--strict` | `BLOCKED` | 1 | 0 | 2 | `run_20260904_170410.json` |

两次调用之间 `sleep 3`（`run_all.py` 第 59 行用
`time.strftime('%Y%m%d_%H%M%S')` 命名 JSON，只到秒级，同秒会静默互相覆盖，
上一轮因此丢过一份）。两次各新建 1 个 JSON，计数 58 → 59 → 60，无覆盖。

### 6.3 工作区状态

`git status --porcelain --untracked-files=no` 为空，tracked 树干净。
untracked 20 个，其中 1 个是 Sarah 并行修改中的
`evidence/task_b_gate_objections.md`（**本轮禁读禁写禁 add，不纳入任何统计，
由最终 push 前检查单独扫**），本轮我拥有 19 个。

## 7. 结论

1. 本轮前置绿基线成立：8 闸门 **0/0/0/0/0/2/2/0**，FAIL 数 0，
   254 单测全绿，普通模式 `PENDING-OK`/0、strict 模式 `BLOCKED`/1，两者都零 FAIL。
2. drill 前置绿由第 2 节的外部快照提供，且这份快照与第 1 节 baseline 的差异
   **只有 label、两处 wall-clock、三处 elapsed**，8 个退出码与 16 段输出逐字相同——
   第 1 步到第 3 步之间什么都没漂。
3. `g0_freeze` 从 FAIL 变 PASS 的原因可逐件归因、可复算：2 件的 MANIFEST 期望变了
   （harness.py 期望改成实际内容、scenarios.json 随 `.gitattributes` 归一化后重算），
   3 件逐字未动；被冻结的**文件内容**只有 scenarios.json 变过，
   变化量精确等于消失的 118 个 `\r`。本地没有跑过 `--update`，没有手改过 MANIFEST。
4. 上一轮的观测如实留档，没有抹掉。其中 4 类归因已作废（第 4.4 节表），
   6 个 commit hash 已经失效（第 5.1 节表），54 → 254、20 对 → 52 对、
   8 → 60 个 JSON 三处计数已过期；仍然成立的有：两个 1.000000、
   「v1 第 6 对最薄」、「`evidence/README.md` 规则 3 与 `run_all.py` 不裁剪的口径冲突」。
5. 本文件里的 commit hash 全部会在 author 改写后失效，稳定锚点是第 0 节的
   tree 哈希、第 3 节的 sha256、以及各处的 blob 哈希与 subject + 序数。
