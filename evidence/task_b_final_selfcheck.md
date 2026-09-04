# 任务 B（记忆系统）取证收尾自证

本文件按 rebase 集成上游修复**之后**的最终状态整体重写，不是对上一版的补丁。
上一版（146 行，记录的是 `9eade73` 那棵树）里有 H7 同族的时间戳跨日、H8 同族的
行数与计数失真、M18 的悬空引用，以及 15 条发现清单里至少 5 条已被集成推翻的归因，
本轮逐条改写，修正前后对照见第 9、10 节。历史观测如实保留，没有抹掉。

所有数字均由命令输出产生，无一处手抄：时间戳来自 `date '+%Y-%m-%d %H:%M:%S %z'`，
行数来自 `wc -l`，哈希来自 `git hash-object` / `shasum -a 256`，退出码来自子进程
`returncode`，commit 清单来自 `git log --format`。

## 0. 定位锚点，以及「为什么这份文件只有 7a」

> **【关于 commit hash 的显式标注】本文件里出现的 commit hash 是 author 改写前的值。**
> push 前全部本地 commit 的 author 会被改写为与上游那个 commit 一致的身份，
> 改写后**所有 commit hash 全部失效**。长期有效的稳定锚点是 **blob 哈希与 tree 哈希**，
> 以及 commit 的 **subject + 序数**：author 改写不动 tree 也不动 blob，
> 这两类哈希在改写前后逐字不变。复核时请勿拿本文件里的 commit hash 去 `git show`，
> 那会打不到东西、并误判成证据造假。

| 锚点 | 值 | 取得方式 |
|---|---|---|
| commit（第 1–5 步全程未变；第 6 步起本轮自己新增 4 条 evidence commit，终态见 §11 第 2 项与 7b） | `d6868c654a821abf7920d249683837db6068a87a`（短 `d6868c6`，第 **39** 条） | `git rev-parse HEAD` |
| **HEAD tree（稳定锚点）** | `37d26de723f1571ec3c6aa0cced25f2794eece68` | `git rev-parse HEAD^{tree}` |
| 基底 = `origin/main` | `10c05d116e58886f3a9366c99cbdc214e9bdfae4`，author `SummerTianYi` | `git log -1 origin/main` |
| ahead / behind | **39 / 0**（快进关系成立，无分叉） | `git rev-list --left-right --count origin/main...HEAD` |
| 解释器 | `./.venv/bin/python`（Python 3.14.7） | — |

**为什么只有 7a。** 任务书第 7 步要求的三项——「git status 空」、「最终 commit 数」、
「逐文件行数与 blob 哈希清单」——都是**提交之后**才存在的状态，而本文件自己要在
第 6 步被提交，它无法记录自己被提交之后的世界。这是自指的必然结果，不是遗漏。
处置方式是把第 7 步劈成两半：

- **7a（本文件 + `evidence/task_b_final_check.log`）**：所有**提交前**就能测、
  且必须在提交前测的项目。它的独立价值在于它**先于**提交——它证明「往仓库里加
  evidence 文件」这件事本身不会扰动任何一个闸门。
- **7b（`evidence/task_b_blob_manifest.md`，最后提交）**：提交后的 git status、
  最终 commit 数、冻结区 diff 复核、8 闸门复跑、以及**全部 tracked 文件的
  `wc -l` + `git hash-object` 清单**（含本文件自身的行数与 blob 哈希）。
  7b 与 7a 两份 8 闸门结果逐格比对，就能证明提交动作没有改变任何被闸门看的东西。

消毒规则：仓库根记作 `<repo>`，仓库外临时目录记作 `<scratch>`，
用户家目录前缀记作 `<home>`；实质数值逐字未改。

## 1. 提交历史未变

本轮取证**没有产生任何 commit**（第 6 步之前），HEAD 从起点到 7a 收尾始终是
`d6868c654a821abf7920d249683837db6068a87a`，tree 始终是
`37d26de723f1571ec3c6aa0cced25f2794eece68`。这两条在
`evidence/task_b_final_check.log` 的 G 节里是**实测相等**而不是声明：
`HEAD 全程未变 : True`、`HEAD tree 全程未变 : True`。

`git rev-list --left-right --count origin/main...HEAD` → `0	39`：
behind 0、ahead 39。behind 为 0 说明上游那个 commit 已经在本地历史里，
快进（fast-forward）关系成立，push 时不需要 force。

39 条 commit 的完整清单（序数 + author 改写前的短 hash + subject）见
`evidence/task_b_blob_manifest.md`。**序数与 subject 是稳定锚点，短 hash 不是**：
`evidence/task_b_gate_snapshot_before.md` 第 5.1 节里有一个已经发生过的实例——
上一版文档记的 7 个 hash 里有 6 个已经因为 rebase 换基而失效了，
author 改写会对全部 39 条做同一件事。

## 2. tracked 文件零变动，以及冻结区从未被本地 commit 触碰的决定性证明

7a 收尾实测（`evidence/task_b_final_check.log` A、G 节）：

```
  tracked 工作区状态（-uno）  = ''
  HEAD 全程未变              : True
  HEAD tree 全程未变         : True
  tracked 工作区仍然干净     : True  ('')
```

untracked 全集是 20 个 `evidence/task_b_*` 文件，其中 **1 个是 Sarah 并行修改中的
`evidence/task_b_gate_objections.md`**——本轮对它禁读、禁写、禁 `git add`、
不纳入任何统计，由最终 push 前检查单独扫。本轮我拥有的是 **19 个**（清单见第 7 节）。
`evidence/run_*.json` 被 `.gitignore` 忽略，不出现在 status 里，也没有被强制 add。

### 2.1 冻结区从未被本地任何一条 commit 触碰

上一版文档是靠「收尾哈希 == 开工前哈希」来间接说明没动过冻结区。本轮换成一个
**更强、且与哈希无关**的证明：直接查每条 commit 的 name-only 清单。

命令与结果：

```
$ git log --format='%h' origin/main..HEAD | while read h; do
      git show --name-only --format='' $h \
        | grep -E '^acceptance/MANIFEST.json$|^\.gitattributes$|^vendor/agent_core/|^acceptance/evals/scenarios.json$'
  done
（39 条全部无输出）
```

即：**本地 39 条 commit 里，没有任何一条改动过 `acceptance/MANIFEST.json`、
`.gitattributes`、`vendor/agent_core/` 下的任何文件、或 `acceptance/evals/scenarios.json`。**

> 这里的 39 条是 **7a 时点**的计数。第 6 步之后本地变成 43 条（本轮自己新增的 4 条
> evidence commit），7b 用同一条命令对全部 43 条重测了一遍，触碰数同样是 **0**
> （`task_b_blob_manifest.md` 第 3 节）。也就是说这条结论没有被本轮自己的提交削弱，
> 反而被加强了：新增的 4 条只碰 `evidence/`。

再看这两个关键文件自己的历史：

```
$ git log --format='%h %an %s' -- acceptance/MANIFEST.json
10c05d1 SummerTianYi fix: regenerate frozen MANIFEST (CRLF bootstrap drift) + force LF via .gitattributes
a0240e1 SummerTianYi feat: workbench bootstrap - task packs, acceptance gates, evidence system

$ git log --format='%h %an %s' -- .gitattributes
10c05d1 SummerTianYi fix: regenerate frozen MANIFEST (CRLF bootstrap drift) + force LF via .gitattributes
```

`MANIFEST.json` 只被两条 commit 碰过：bootstrap（`a0240e1`）与上游修复（`10c05d1`），
两条的 author 都是 `SummerTianYi`，两条都不在本地 39 条里。`.gitattributes`
只被 `10c05d1` 碰过，同样不在本地 39 条里。

**这条证明的意义**：它排除了「取证者跑过 `g0_freeze.py --update`」和
「取证者手改过 MANIFEST 让闸门变绿」这两种可能——不是靠声明，而是靠
git 自己的提交记录。`MANIFEST.json` 期望值的变化 100% 来自上游那个 commit，
其 subject 自己就写明了原因（`CRLF bootstrap drift`）。逐件对照见
`evidence/task_b_gate_snapshot_before.md` 第 4.2 节。

## 3. 冻结区 diff 复核

逐件 `git diff --stat -- <path>` 与 `git diff --stat HEAD -- <path>`，5 件全空：

```
    CLEAN  vendor/agent_core/harness.py
    CLEAN  vendor/agent_core/song_catalog.py
    CLEAN  vendor/agent_core/voice_text.py
    CLEAN  vendor/agent_core/data/luotianyi_original_songs.json
    CLEAN  acceptance/evals/scenarios.json
  => 冻结区 5 件全部无改动 : True
```

（原文见 `evidence/task_b_final_check.log` A 节，2026-09-04 17:04:02。）

追加的 blob 三方相等性检查：5 件的 `git hash-object <path>` 与
`git rev-parse HEAD:<path>` 逐个相等，5/5 `equal = True`。
这比 diff 为空更强一点——它同时说明工作区、index、HEAD 三处的这一件是同一个 blob，
且过滤器链在它上面不做任何转换。

`acceptance/evals/scenarios.json` 另有专项 EOL 探针（`i/lf w/lf`、
`attr/text=auto eol=lf`、`git hash-object` == `--no-filters` == `HEAD:`、
`CR count = 0`、`bytes = 2752`），全文见 `evidence/task_b_final_check.log` B 节，
判读见 `evidence/task_b_gate_snapshot_before.md` 第 3 节。
`.git/info/attributes` **不存在**，上一轮为排查 CRLF 而加的本地临时规则已撤销。

## 4. 5 个冻结件 sha256 复算，与上一轮开工前快照逐一对照

7a 收尾复算（2026-09-04 17:04:03），`RESULT: 5/5 match`：

| 冻结件 | 上一轮期望 | 本轮期望 = 本轮实际 | 一致 | 变化归因 |
|---|---|---|---|---|
| vendor/agent_core/harness.py | `219691162b9f09b8…34ea8da5` | `cb1ae928f80674952c4ac6e6385d260a7dbd5cf93ac5ab96889ff6bdb32b2807` | **否** | 文件内容**没变**，MANIFEST 期望被上游重算成实际内容 |
| vendor/agent_core/song_catalog.py | `57d257d1084a6727…a411e49e` | `57d257d1084a67271a78a3b79393839c1442d37499c8a25862d80071a411e49e` | 是 | 未变 |
| vendor/agent_core/voice_text.py | `c652a1b868029a5f…8e4da8` | `c652a1b868029a5f1d46b23e1720af44363081ce441c1ff008bcc86f913e4da8` | 是 | 未变 |
| vendor/agent_core/data/luotianyi_original_songs.json | `22552757d32c86e1…f2710f8d` | `22552757d32c86e1bf9d52217c3c3ff588bd35a86ba1ceada6707198f2710f8d` | 是 | 未变 |
| acceptance/evals/scenarios.json | `01ed805ae688e431…32df42e67` | `2c5dab3fc5e414680193c7b998bb62cf9fe3c6299f2f002682a75efa8179b00e` | **否** | `.gitattributes` 生效后工作区归一化为纯 LF（2870→2752 字节，差 118 = 消失的 CR 数），MANIFEST 随之重算 |

两处「否」都发生在**上游那一侧**，不是本地改动，第 2.1 节已给出 git 记录级的证明。

**关键一点**：harness.py 这一行，上一轮记的「实际」值 `cb1ae928f8067495…`
正好等于本轮的「期望」值。也就是说这个文件的字节从头到尾没有变过，
变的只是 MANIFEST 里对它的期望。本轮 drill 里它又被独立验证了一次：
drill 破坏与还原前后，harness.py 的 blob 哈希都是
`29dca70bcc740976910cd0f85d38f2ce9034795c`。

上一版文档在这里的结论是「没有"顺手修好" harness.py 的既有漂移
（它仍是 `cb1ae928…`，仍与 MANIFEST 不符，g0_freeze 仍 FAIL）」——
**这条已作废**：现在它与 MANIFEST 相符，`g0_freeze` = PASS/0。
但「取证者没有顺手修好它」这半句仍然成立，而且现在有了更强的证据形式：
不是「哈希还是那个漂移值」，而是「本地 39 条 commit 一次都没碰过它」。

## 5. 任务 B 交付物的收尾哈希

sha256 由 `shasum -a 256` 生成，blob 由 `git hash-object` 生成。
**blob 哈希是稳定锚点**（author 改写前后逐字不变），sha256 是对照用的第二口径。

| 文件 | sha256 | blob |
|---|---|---|
| `src/memory_ranker.py` | `e204b36022b071df32a4dd52bd65f0e869c3a27d6878e5c0e0ea4c84fb5406f0` | `2a125cae23544790a7e7f188b11f32c5e4070b55` |
| `src/memory_lexicon.py` | `777c3a5835633589dd3ba40d37a5ddaa74401c818e0b5cb791ba0f1b3df4e27f` | `bfba659bc411a981b7d9df8913a70793d6d63c6e` |
| `src/memory_store.py` | `3c81cd6b973a2b18a7be42b15d50744101ee6b1d0cec6137ee6471dd7efaa63a` | `49d273aa9286afdf4d6f649b915c56042c9354e1` |
| `tests/test_memory_retrieval.py` | `df5b47d1af97cdd7c990a945de7ddb73b7e8c142e1fff41051933bed3c6fe291` | `0c982e6afa8984d90e940fd05100766cbc098f8c` |
| `tests/test_holdout_v2.py` | `7daa6188881fb8939f6ea33e2543fa652970d358000fd23f7a104cca14f2f80e` | `ec8fea1f586a4797a6f35502320bfc9880966421` |
| `tests/test_ranker_mutations.py` | `c1d21ecaa950a42d68ff8c1d8daad5bcf6d9e3aea9c56b51dfbb70c558284c00` | `3aa7a7d4bb4816bcbb75fd296faf263edd68e792` |
| `tests/holdout_v2.py` | `95266b3dc670d5d9fbb914bbbc9793fb9b3f65d8e2b9514834fc58e16986ee7a` | `fcf727ff1a27cc5658c8023bbbb0ea72d9793f11` |
| `tests/report_retrieval.py` | `2627d3aa7679b3c4cfec71efa7703776e0b4fc2700e2ca6303a60f6b595166d5` | `e98054edbe2774dd76ac3866f4d790ee95ca826d` |
| `acceptance/gates/g1_memory.py` | `21cacd162b4eb3c05c7ee38b184ac73097f62e39791565b9addfdd1d941fca60` | `7bca7b83221865fd23c36243229653c91a8c81b9` |
| `acceptance/MANIFEST.json` | `274f6e491045832c873c2e9cdcaab0c409423e04a4a6b3969ebdba0660770b32` | `b93dbab76542e93eedd98a365f1f089f9ab4c934` |
| `.gitattributes`（上游新增，禁改） | `d60f352d0db1404c70afb4bb8b2ca3fd1c610572aa40720e8a0b7baa7885418c` | `6313b56c57848efce05faa7aa7e901ccfc2886ea` |

与上一版文档记的收尾哈希对照：

| 文件 | 上一版记的 sha256 | 本轮 sha256 | 变了 | 归因 |
|---|---|---|---|---|
| `src/memory_ranker.py` | `0408b075543da354…6c62f0b4` | `e204b36022b071df…84fb5406f0` | 是 | 上一版之后任务 B 又推进了 33 条 commit（M/L/RC/N 各系列修复与词典拆分） |
| `src/memory_store.py` | `d5b1d782b700062f…2f5b7586` | `3c81cd6b973a2b18…7efaa63a` | 是 | 同上（含 `recall_relevant` 排序修复、`format_memory_prompt` 三层消毒） |
| `tests/test_memory_retrieval.py` | `87f26a1c295eced9…609bb383` | `df5b47d1af97cdd7…3c6fe291` | 是 | 同上，且第 31 条 commit 把它拆成三个文件 |
| `acceptance/MANIFEST.json` | `1e6a1000187a2059…77c7a8e3` | `274f6e491045832c…660770b32` | 是 | **上游 `10c05d1` 重算**，不是本地改动（第 2.1 节已证） |

四个都变了，但**没有一个是因为本轮取证**：本轮取证对这些文件零写入。
可逆性的实测证据在 `evidence/task_b_self_sabotage.log` E 节——8 个被盯的
blob 在整份九路变异日志跑完之后逐个相等，`git status -uno` 与 `git diff --stat`
均为空，HEAD 与 HEAD tree 均未变；那九路变异**一次都没有写盘**，
全部在进程内用 `mock.patch.object` 施加。

## 6. 收尾完整复跑（7a）

原始输出全文在 `evidence/task_b_final_check.log`（**393 行**，`wc -l`），
本节只摘录判定行。执行时刻 2026-09-04 17:04:02 → 17:04:12 +0100，
**全部落在同一天，没有跨日**。

### 6.1 8 闸门逐个单独跑，与起点逐格比对

| 闸门 | 起点（10:55:16） | 收尾（17:04:03） | 一致 | verdict |
|---|---|---|---|---|
| g0_environment | 0 | 0 | True | PASS |
| g0_secrets | 0 | 0 | True | PASS |
| g0_freeze | 0 | 0 | True | PASS |
| g1_contract | 0 | 0 | True | PASS |
| g1_memory | 0 | 0 | True | PASS |
| g1_permissions | 2 | 2 | True | PENDING |
| g1_tools | 2 | 2 | True | PENDING |
| g3_simulate | 0 | 0 | True | PASS |

```
  TOTAL: PASS=6 FAIL=0 PENDING=2  (of 8)
  => 8 格全部与起点一致 : True
  => 与期望矩阵 0/0/0/0/0/2/2/0 一致 : True
```

与上一版的差别：上一版这里是 `0 / 0 / 1 / 0 / 0 / 2 / 2 / 0`（`g0_freeze` FAIL），
本轮 `g0_freeze` = 0。**FAIL 数从 1 降到 0**，其余 7 格逐字未变。

### 6.2 单元测试

```
Ran 254 tests in 0.165s

OK
===EXIT=0===
```

上一版这里是 `Ran 54 tests in 0.027s`。254 = 三轮取证里每轮都复跑过的同一个数
（`evidence/task_b_gate_matrix.md` 第 3 节：R1/R2/R3 均 254 全绿、退出码 0，
耗时 0.163s / 0.159s / 0.162s），收尾这次是第 4 次。

### 6.3 `run_all.py` 双模式

| 模式 | verdict | 退出码 | FAIL 数 | PENDING 数 | 新建 evidence JSON |
|---|---|---|---|---|---|
| 普通 | `PENDING-OK` | **0** | 0 | 2 | `run_20260904_170407.json` |
| `--strict` | `BLOCKED` | **1** | 0 | 2 | `run_20260904_170410.json` |

与派单期望逐字一致：普通模式 `PENDING-OK` / exit 0 / 零 FAIL，
strict 模式 `BLOCKED` / exit 1 / 零 FAIL。

两次调用之间 `sleep 3`。这是必需的：`run_all.py` 第 59 行用
`time.strftime('%Y%m%d_%H%M%S')` 给 JSON 命名，只到秒级，同秒两次调用会**静默互相覆盖**。
上一轮就因此丢过一份（派单预期 6 个 JSON、实际落盘 5 个）。本轮每次调用前后都对
`evidence/run_*.json` 做快照，实测计数 58 → 59 → 60，各新建 1 个，**无覆盖**。
（这个计数只增不减：7a 与 7b 又各跑了两次 `run_all.py`，到 7b 时点是 **66** 个，
见第 8 节。58 → 59 → 60 是三轮取证当时的实测值，作为历史记录保留不改。）

> **收尾跑了两次，如实记录。** 第一次生成的 `final_check.log` 是 387 行，
> 内容全部合格（8 闸门逐格一致、254 单测 OK、双模式 verdict 与退出码都对），
> 但**表头漏了 leader 要求的那句「author 改写后 commit hash 全部失效」的显式标注**。
> 我把这句补进驱动脚本的表头后重跑了一次，得到现在这份 393 行的日志。
> 两次运行的**实测结果逐字相同**，差别只有表头多出的 6 行说明、以及随之变化的
> 时间戳与 elapsed。这不是「因为结果不好看而重跑到好看」——两次的结果本来就全绿、
> 而且完全一样；重跑的唯一目的是补一句必需的图例。之所以仍然重跑而不是手改日志，
> 是为了让这份日志保持 100% 由命令生成、不掺手写的正文。
>
> 两次运行各产生 2 个 JSON，共 4 个，都还在盘上（被 `.gitignore` 忽略，不入库）：
> 第一次 `run_20260904_170228.json`（普通）/ `run_20260904_170232.json`（strict），
> 第二次 `run_20260904_170407.json`（普通）/ `run_20260904_170410.json`（strict）。
> 上表引的是**第二次**那两个，因为 393 行的日志是第二次生成的，引第一次的
> 文件名会对不上。第一次那份日志已被覆盖，这一点如实说明，不假装可验。

上一版文档在这里记的是「`VERDICT: FAIL`，退出码 1」——**已作废**，
成因归因的改写见 `evidence/task_b_gate_matrix.md` 第 4.3、4.4 节。

### 6.4 `report_retrieval.py`

任务书起点要求的是「四模式」。**起点那四次的逐模式输出没有落盘**
（只有 8 闸门快照存了下来），所以收尾跑了**全部六种模式**，是四模式的超集，
不会因为选错子集而漏掉起点跑过的那几个。这一点如实记录，
不假称做过逐模式 diff。

| 模式 | 退出码 | stdout 行数 | stderr 行数 | 耗时 |
|---|---|---|---|---|
| v2 | 0 | 85 | 0 | 0.10s |
| diagnose | 0 | 83 | 0 | 0.08s |
| ablation | 0 | 38 | 0 | 0.13s |
| sensitivity | 0 | 167 | 0 | 0.97s |
| lexicon | 0 | 52 | 0 | 0.12s |
| l2 | 0 | 45 | 0 | 0.15s |

六种模式全部退出码 0、stderr 全空。

比对基准改用可独立复核的东西——三集指标。`v2` 模式第三次算出
`宏平均 precision = 0.7742 (n=31)`、`宏平均 recall = 0.7500 (n=30)`、
`可判定对（relevant 非空）= 30，命中 = 24，未命中 = 6`。前两次分别是：
`evidence/task_b_self_sabotage.log` 里我的**独立重写口径**、以及官方
`score_holdout_v2`，两者互验 `AGREE (<1e-12)`。三个实现算出同一个数。

### 6.5 三集指标收尾值

| 集 | 对数 | 命中 | precision | recall | 谁在看它 |
|---|---|---|---|---|---|
| `golden` | 8 | 8/8 | 1.0000 | 1.0000 | **闸门 `g1_memory`（唯一进闸门判定路径的集）** |
| `v1`（`HOLDOUT_GOLDEN`） | 12 | 12/12 | 1.0000 | 1.0000 | 只有 `tests/`（sha256 锁 `561f17ba423dfa024ba9a940632e5d6a8399ea5638ec5b56119e72c6c9b72619`） |
| `v2`（`HOLDOUT_V2`） | 32 | 24/32 | 0.7742 | 0.7500 | 只有 `tests/`（文件字节锁 + 语料哈希锁） |

与派单期望逐字一致。v2 的三条棘轮余量：precision 0.7742 − 0.77 = **0.0042**、
recall 0.7500 − 0.75 = **0.0000**、hits 24 − 24 = **0**。
**recall 与 hits 两条余量为零**，即 v2 现在正好压在棘轮线上，
任何一对从命中翻成未命中都会让 `tests/test_holdout_v2.py` 变红。这记进第 10 节。

## 7. 本轮 evidence 文件清单

19 个（我拥有的），全部在 `evidence/` 下。行数由 `wc -l` 生成。
**本文件自身不计入下表以避免自指**，它的行数与 blob 哈希在
`evidence/task_b_blob_manifest.md`（7b）里给出。

| 文件 | 行数 | 用途 |
|---|---|---|
| `task_b_gate_snapshot_before.md` | 570 | 本轮前置绿快照（step 1.6 baseline + step 3.1 drill 前）+ 上一轮开工前快照的历史留档与逐条标注 + `g0_freeze` 转 PASS 的逐件归因 |
| `task_b_gate_matrix.md` | 250 | DoD a 项主证据：8 闸门 × 3 轮 × 2 模式 = 48 格明细、焦点闸门单独复跑、每轮 verdict/退出码/JSON 名/时间戳/commit、每个非 PASS 格的逐条归因、集成后归因改写、历史如实保留 |
| `task_b_round1_normal.log` | 52 | R1 普通模式原始输出 + 退出码 + 时间戳 + `g1_memory`/`g0_freeze` 单独复跑 |
| `task_b_round1_strict.log` | 32 | R1 strict 模式，同上 |
| `task_b_round1_unittest.log` | 14 | R1 单测原始输出（254 / OK / 0） |
| `task_b_round2_normal.log` | 52 | R2 普通模式 |
| `task_b_round2_strict.log` | 32 | R2 strict 模式 |
| `task_b_round2_unittest.log` | 14 | R2 单测 |
| `task_b_round3_normal.log` | 52 | R3 普通模式 |
| `task_b_round3_strict.log` | 32 | R3 strict 模式 |
| `task_b_round3_unittest.log` | 14 | R3 单测 |
| `task_b_sabotage_drill.log` | 9 | `sabotage_drill.py` 原始 stdout（`DRILLS DETECTED: 3 of 3`）+ 退出码 0 + 时间戳。drill 自己不写 evidence JSON，这份 tee 是它唯一的输出留存 |
| `task_b_sabotage_drill.md` | 470 | DoD b 项前半：drill 前后哈希对照、与上一版差异的归因、三路逐条分析、前置绿断言、**有效检出改判 3/3 的四条依据**、四个代码缺陷的实测确认（其中缺陷④判定为不成立）、手工复验回绿、`__pycache__` 污染实测 |
| `task_b_drill_attribution.log` | 105 | 只读归因脚本的原始输出：5 个冻结件的字节/行尾形态/sha256、三路锚点出现次数与字节差、破坏态 sha256、还原路径能否逐字节还原。**本轮新增**，用于支撑「缺陷④不成立」与「eval-tamper 因果链闭合」 |
| `task_b_after_drill.log` | 243 | drill 后手工复验回绿的原始输出（A–H 节）：三个相关闸门单独复跑、完整 8 闸门快照、`run_all.py` 双模式、`unittest discover`、三目标 sha256 逐一比对 |
| `task_b_self_sabotage.log` | 362 | DoD b 项后半原始日志：变异测试清单（`-v` 全文 + 回滚机制 grep）、九路独立复跑 × 三集、Sarah 数字复核、**真闸门 `g1_memory.run()` 进程内实测**、可逆性收尾复核 |
| `task_b_self_sabotage.md` | 495 | 反 Goodhart 自证汇总：九路实测分数表、有牙齿/无牙齿分类、`kill_l5` 无牙齿的根因、Goodhart 敞口的直接实测与对派单问题的明确回答、可逆性、H7/H8 修正前后对照、Sarah 数字三棵树对照、F1'–F9' |
| `task_b_final_check.log` | 393 | 收尾（7a）完整复跑原始输出：git 状态、冻结区 diff、5 件 sha256 + EOL 探针、8 闸门逐个跑 + 与起点逐格比对、254 单测、`run_all.py` 双模式、`report_retrieval.py` 六模式 |
| `task_b_final_selfcheck.md` | 本文件 | 收尾自证（7a）：提交历史、tracked 零变动与冻结区未触碰的 git 记录级证明、冻结区 diff、5 件 sha256 对照、交付物哈希、收尾复跑、evidence 清单、M18 修正、发现清单 |

上表 18 个文件（不含本文件）合计 **3191 行**（`wc -l` 逐文件相加）。

这个合计值本轮改过一次：原本是 3174，因为第 7.1 节要求把扫描第一次失败的经过
如实记进 `task_b_sabotage_drill.md`，那份文件从 453 行变成 470 行（+17），
合计随之变成 3191。两个数都是 `wc -l` 的实测值，不是手算：3174 + 17 = 3191，
与 `wc -l` 多文件模式的 `total` 行逐字相符。**上表与本行的数字必须在所有
文档编辑完成之后重取一次**，否则就是 H8 那类行数失真。

另有两份不在上表里：

- `evidence/task_b_scan_report.log`（第 **20** 个）——第 6 步提交前的手工扫描记录，
  由仓库外的 `scan_evidence.py` 生成，逐文件×逐探针计数表 + 判定 + P19 上下文。
  **上表不列它的行数**：它的正文会回指本文件（第 4 节里列了本文件的命中行），
  把它的行数写进本文件就构成一个环——行数变了要重生成报告，报告重生成了行数又变。
  它的行数与 blob 哈希统一放到 7b（`task_b_blob_manifest.md`）里给，
  那时它已经被提交、不会再变。
- `evidence/task_b_blob_manifest.md`（第 **21** 个，7b）——在第 6 步提交**之后**生成并
  单独提交，里面是**全部 tracked 文件**的 `wc -l` + `git hash-object` 清单（含本文件
  与扫描记录自己）、提交后的 git status、最终 commit 数、以及提交后复跑 8 闸门的
  结果。它是最后一份，因为只有它能看到「提交之后」的世界。

### 7.1 消毒说明与手工扫描结果

机器绝对路径统一替换为记号：仓库根 `<repo>`、仓库外临时脚本目录 `<scratch>`、
用户家目录前缀 `<home>`、系统临时目录 `<tmp>`。替换只作用于路径字符串，
**分数、退出码、哈希、时间戳、用例数、逐条命中明细等实质内容逐字未改**。

临时脚本一律放在仓库外的 `<scratch>` 下（本轮用到 `gate_snapshot.py`、
`frozen_check.py`、`round_driver.py`、`drill_attribution.py`、`mutate_eval.py`、
`step4_driver.py`、`step7_driver.py`、`scan_evidence.py`），仓库内**没有留下任何临时脚本**。

**为什么必须手工扫。** `g0_environment` 与 `g0_secrets` 的 `SCAN_DIRS` 不含
`evidence/`，`SCAN_SUFFIXES` 不含 `.log`。也就是说即使某份 evidence 泄漏了机器绝对
路径或一枚凭据，这两个闸门照样报 PASS。手工扫描是这条盲区的补偿控制。

扫描共 **19 个探针**，分四类（ID / 类别 / 语义见 `evidence/task_b_scan_report.log` 第 1 节）：

1. **P01–P08 机器绝对路径**：本机用户家目录前缀、Linux 家目录前缀、Windows 两种
   盘符写法、每用户临时目录前缀、系统临时目录前缀、本地登录名、仓库绝对路径。
2. **P09–P16 密钥样式串**：`g0_secrets.py` 自带正则的超集，再加上常见厂商密钥前缀、
   赋值形式的凭据关键字、HTTP 授权头关键字、三种 PAT 前缀样式、PEM 私钥块头、
   AWS access key id 样式、连接串内嵌凭据。
3. **P17 上游 author 的 email 地址**：它是个人邮箱，虽然本来就在 git 历史里、不是秘密，
   但没有理由抄进证据文档，需要时用 `git log -1 origin/main` 现取。
4. **P18–P19 哈希（信息类，非泄漏）**：40 位十六进制串总数、以及 7 位短 hash 样式。
   这两条是**可读性核查**——本轮所有 commit hash 都会在 author 改写后失效，
   所以每个 hash 都必须带标签。逐条人工判读见下面的 7.2。

> **扫描第一次跑出来是失败的，如实记录。** 退出码 **1**、`泄漏类合计命中 = 3`、
> 判定 `=> 泄漏类全部为 0 : False`。三条全部指向同一个文件：
> `task_b_sabotage_drill.md` 命中 P02 / P05 / P06 各 1 处，位置是它第 38–39 行——
> 那两行为了解释「扫了哪些样式」，把三个路径类探针的字面样式串直接抄进了正文，
> 于是文件自己命中了自己描述的探针。这是本轮**第三次**犯同一类自指泄漏
> （前两次：`task_b_sabotage_drill.md` 早前的版本、本文件第 7.1 节的早前版本）。
> 修法与前两次相同：改成 ID + 语义指代，不印字面串。**修的过程里我差点犯了第四次**
> ——第一版修订正文为了说明改了什么，把「改前的原文」整句引了下来，
> 引下来就等于把三个样式串再抄一遍；这一点在 `task_b_sabotage_drill.md` 的修订说明里
> 也写明了。重跑后三个探针归 0。
>
> **接着又出现了第五次，而且犯在扫描器自己身上。** 重跑（第二轮）后 P02/P05/P06 归 0，
> 但 P16（连接串内嵌凭据）冒出 1 处，位置就在扫描报告自己里面：探针清单那一节里
> P16 的**语义描述**为了说清楚它扫的是什么形态，把那个形态直接写了出来——
> 而一个展示该形态的描述，本身就是该形态。**它命中了自己的探针清单。**
> 修法是同一条：描述只说“scheme 分隔符 + 冒号 + at 符号”这几个成分名，不把它们拼在一起。
>
> **还有一个不显然但必须说清楚的机制：扫描报告扫到的是上一轮的它自己。**
> 脚本先把目标文件读进内存、再写报告，而报告自己也在目标集里，所以它读到的是
> 磁盘上**上一轮**留下的那一份。后果是修正永远晚一轮：第三轮报告里 P16 仍然是 1，
> 不是因为它没修好，而是因为它扫的是第二轮那份还带着旧描述的报告。
> 因此判收敛不能只看一轮，必须连跑两轮并比对。实测：第四轮与第五轮的报告
> **除了时间戳那一行以外逐字相同**（`diff` 排除 `generated` 行后为空），
> 两轮退出码均为 **0**。这就是本轮的不动点。

上述探针的具体字面样式串**不写进本文件**，理由就是上面那两次失败。完整的
逐文件×逐探针计数表在 `evidence/task_b_scan_report.log`，那张表是脚本生成的、
探针只以 ID 出现，所以报告能被同一组探针扫、包括扫它自己；汇总见交付报告第 8 节。

> 特别说明：本轮对话里出现过一枚**已被要求吊销**的 GitHub PAT。
> 它以**任何形式**（原文、前缀、截断、编码、哈希）都**没有**出现在本文件、
> 任何一份 evidence、任何一条 commit message 里。P09–P16 的 0 命中覆盖这一点；
> 三种 PAT 前缀样式（P12 两种 + P13 一种）单独看也是 0。

### 7.2 P19 逐条人工判读

P19（7 位短 hash 样式）在收敛后的那一轮里共命中 **18 个令牌**，分布在 **16 行**
（两个令牌落在同一行的有 2 处，所以令牌数比行数多 2；扫描报告第 3 节给的是令牌数、
第 4 节给的是行数，两个数不相等是口径差异而不是矛盾）。逐行看过
（`file:line` 见扫描记录第 4 节），分成两类，**没有一处是裸 commit hash**：

| 类别 | 行数 | 是什么 | 判读 |
|---|---|---|---|
| `git log` 清单与锚点表格里的短 hash | 11 | `final_selfcheck.md` 第 101/102/105 行（MANIFEST 与 `.gitattributes` 的历史，带 author + subject）、`gate_snapshot_before.md` 第 352–358 行（7 条 commit 清单，带 subject）、`final_check.log` 第 28 行（HEAD 长 hash + 短 hash，带标签） | **合格**：旁边有 subject / 序数 / 标签，且所在文档开头都有那句「author 改写后 hash 全部失效」的显式标注 |
| drill 的哨兵字面量，形状上像 7 位十六进制但根本不是 hash | 5 | `after_drill.log` 第 165/171/179/191 行与 `sabotage_drill.md` 第 429 行里的 `__pycache__` 污染对照实验，哨兵值是同一个字母重复七次（第 179 行与第 429 行各包含两个令牌，这就是 16 行 / 18 令牌差的来源） | **误报**：探针按形状匹配，七个 `a` 或七个 `b` 落在 `[0-9a-f]{7}` 里。它们是实验载荷，不是定位符，author 改写对它们毫无影响 |

P18（40 位十六进制串）共 **209** 处，全部是带标签的锚点：blob 哈希、tree 哈希、
sha256、或 `HEAD` 长 hash。本轮**没有任何一处**把 40 位 hash 当唯一定位手段散写。

这个数变过一次，从 133 到 209，**差值 76 全部由 7b 那一个文件贡献，逐字可核**：
扫描记录第 2 节的逐文件计数表里，`task_b_blob_manifest.md` 那一行 P18 = **76**、
P19 = **0**；133 + 76 = 209，18 + 0 = 18。单独数那一个文件（`grep -oE` 40 位十六进制）
也是 76，构成是 74 个 tracked 文件的 blob 哈希 + `HEAD` 的 commit 与 tree 两个锚点。
**所以 P18 跳变不是泄漏信号，而是一份哈希清单本该有的锚点密度**；反过来 P19 一个
都没涨，说明那份清单里没有一处把短 hash 当唯一定位手段。P19 的 18 个令牌 / 16 行
在 23 个目标与 24 个目标两种范围下完全相同，上表的逐行判读因此仍然有效。

> 扫描记录的第 4 节在回显命中行时，把 hash 令牌本身替换成了记号，`file:line` 保留原样。
> 理由与探针字面串不入文档是同一条：若把令牌原样抄进报告，报告就会命中自己的第 4 节，
> 下一轮又把这些命中再抄一遍，计数永不收敛、不存在不动点。替换之后报告在同一组探针下
> 自洁，重跑两次的差别只有时间戳（这一点已实测，见交付报告第 8 节）。

### 7.3 扫描脚本自己修掉的两个缺陷

扫描脚本第一版有两个缺陷，都在跑出结果之前或之后被发现并修掉，记录在这里
（与 `task_b_self_sabotage.md` 里记录的另两个仓库外脚本缺陷同属一类）：

| # | 缺陷 | 后果 | 修法 |
|---|---|---|---|
| ① | P07（本地登录名）用裸子串计数 | 本机登录名正好是一个英文词片段，也是文档里合法提及的操作系统名的前缀；裸子串会在每一处合法提及上点亮，把真信号（登录名作为绝对路径的一部分泄漏）埋掉 | 改成两侧带词边界的正则，只在它独立成词（即作为路径分量）时匹配 |
| ② | 第 4 节回显命中行时原样抄了 hash 令牌 | 报告命中自己的第 4 节 → 下一轮再抄一遍 → 计数发散，不存在不动点 | 回显时把 P18/P19 的匹配令牌替换成记号，`file:line` 保留；判读标准也不预先下结论，只列标准，判读结果落在本节 |
| ③ | P16 的语义描述把待扫形态直接写了出来 | 一个展示该形态的描述本身就是该形态，报告命中自己的探针清单（第 7.1 节记的第五次自指泄漏） | 描述只列成分名（scheme 分隔符 / 冒号 / at 符号），不把它们拼接成可匹配的串 |

缺陷 ① 是在跑之前看代码时发现的；缺陷 ② 是在设计阶段推演“报告能不能扫自己”时
发现的；缺陷 ③ 是**跑出来才知道**的——第二轮报告里 P16 = 1 而全部 evidence 文件
里连一个 at 符号都扫不到（`grep` 实测为空），才定位到是报告自己的探针清单。

另有一个非缺陷但必须说明的事实：脚本第一次运行**根本跑不起来**——一个列表追加
调用少传了参数，`TypeError` 直接抛出，退出码 1，一个字都没写盘。修掉之后才有上面
那次「3 处泄漏」的真实结果。

全部轮次的完整顺序如下，每一轮的退出码都是实测值：

| 轮 | 目标文件数 | 泄漏类（P01–P17） | P18 | P19 | 退出码 | 发生了什么 |
|---|---|---|---|---|---|---|
| 1 | 22 | **3**（P02/P05/P06 各 1） | 133 | 18 | **1** | 三处全在 `task_b_sabotage_drill.md` 第 38–39 行（字面串抄进正文） |
| 2 | 23 | **1**（P16） | 133 | 18 | **1** | 前三处已归 0；报告自己的探针清单命中 P16 |
| 3 | 23 | **1**（P16） | 133 | 18 | **1** | P16 描述已改，但本轮扫到的是第 2 轮那份旧报告（一步滞后） |
| 4 | 23 | **0** | 133 | 18 | **0** | 收敛 |
| 5 | 23 | **0** | 133 | 18 | **0** | 与第 4 轮除时间戳外逐字相同，不动点 |
| 6 | 23 | **0** | 133 | 18 | **0** | 把第 1–5 轮的经过写进本文件后重扫（本文件也是扫描目标，改了就必须重扫） |
| 7 | 23 | **0** | 133 | 18 | **0** | 与第 6 轮除时间戳外逐字相同 |
| 8–11 | 23 | **0** | 133 | 18 | **0** | 两对：写入 F21 与 §11 之后一对，第 6 步四个 commit 落盘之前又一对 |
| 12–13 | **24** | **0** | **209** | 18 | **0** | 一对：7b 的 `task_b_blob_manifest.md` 写完之后重扫，目标多一个、P18 多 76（第 7.2 节逐字归因） |

第 6、7 轮必须存在的原因：第 5 轮之后我又改了本文件与 `task_b_sabotage_drill.md`
（把扫描失败的经过如实记进去），而这两份都是扫描目标。不重扫就提交，
等于拿一份描述旧文件的报告去为现在的文件背书。重扫后确认这些改动没扰动任何计数。
第 12、13 轮必须存在的原因完全相同，只是这次新增的目标是 7b 那一份。

目标文件数从 22 变 23，多的那一个就是扫描报告自己（第 1 轮时它还不存在）；
从 23 变 **24**，多的那一个是 `task_b_blob_manifest.md`（第 12 轮时才存在）。

> **上表的轮次序号不是锚点，不变量才是。** 写下上表本身又是一次文档修订，
> 修订之后就必须重扫，于是序号会继续往上涨——声称「入库的是第 N 轮」永远追不上。
> 所以判定标准换成一个会终止的不变量：
>
> **入库的那份扫描报告，是满足「最后连续两轮除时间戳那一行以外逐字相同、
> 且两轮退出码均为 0」这个条件的那一轮。**
>
> 本轮实测满足这个条件：第 4/5、6/7、8/9、10/11、12/13 各是一对，
> 每一对的 `diff`（排除 `generated` 行）均为空、退出码均为 0，
> 且每一对的泄漏类（P01–P17）均为 0。P18/P19 不是不变量（P18 从 133 变到 209，
> 已逐字归因），所以不用它们做判据，只用它们做交叉校验。
>
> 上表最后一次修订之后还要再跑一对来验证这次修订（本文件自己就是目标），
> 那一对的结果记在**交付报告**里而不是本文件里——记进来就又要重跑，序号永远追不上。
> 这就是「序号不是锚点」的具体含义。

## 8. `evidence/run_*.json` 计数与 `README.md` 规则 3 的冲突

`ls evidence/run_*.json | wc -l` → 7a 时点 **60**，7b 时点 **66**。
两个数都是实测。差值 6 可逐个点名：按文件名时间戳排序，60 之后的六个正是
7b 驱动跑了三次、每次两个模式（普通 + strict）各新建一个；
7a 自己那两次已包含在 60 里（时间戳 17:04:07 / 17:04:10）。
7b 最后一次运行的前/后计数在它自己里有逐字记录：64 → 65 → 66
（`task_b_blob_manifest.md` 第 250 与 282 行），与这里的 66 对得上。
**这个计数只增不减**，所以引用它必须带时点。

`evidence/README.md`（8 行）规则 3 原文：「提交前删除过期运行记录，保留最后 10 条」。
但 `run_all.py` 第 57–60 行**只写不删**，没有任何裁剪逻辑；
而且 `run_*.json` 被 `.gitignore` 忽略，「保留」这件事对主仓侧根本不可见。
当前 66 个，超出上限 50 个（7a 写这一节时是 60 个，同样超）。

处置沿用上一轮：**取证者一个都没删**（那里面有别人留下的运行记录，删掉不可逆），
也**一个都没 `git add`**（任务书明确要求不强制 add）。这条口径冲突记进第 10 节，
由主仓或提交者处置。

上一版文档在这里记的是「开工前 8 个 + 本次新增 7 个 = 15 个」，
以及「派单预期 6 个 JSON、实际落盘 5 个（同秒覆盖）」。
计数已过期；**同秒覆盖这个问题本轮已通过 `sleep 3` 消除**：
三轮双模式 6 个 JSON 全部落盘，drill 后复验 2 个、收尾 4 个
（收尾跑了两次，见第 6.3 节的如实记录），共 12 个，**无一丢失**。

## 9. M18 修正：`ADVERSARIAL_REVIEW.md` 的引用

### 9.1 上一版的原文（悬空引用）

上一版本文件第 127 行原文：

> 取证过程中新发现的缺陷、闸门设计问题与证据口径歧义，供 `ADVERSARIAL_REVIEW.md` 收录。
> F1–F7 的完整论证在 `evidence/task_b_self_sabotage.md` 第 8 节，
> F9–F12、F14 在 `evidence/task_b_sabotage_drill.md`，F8、F15 在
> `evidence/task_b_gate_matrix.md`，F13 在本报告第 7 节。

这一句有**两类**问题，不止 M18 一类：

1. **M18 本体**：`ADVERSARIAL_REVIEW.md` 当时不存在，现在**仍然不存在**
   （`ls ADVERSARIAL_REVIEW.md` → `No such file or directory`）。
   用现在时态写「供 X 收录」，读者会去找一个不存在的文件。
2. **章节指向也全部失效**（这是本轮重写才发现的、M18 之外的第二个问题）：
   重写之后，反 Goodhart 的发现清单在 `task_b_self_sabotage.md` 的**第 10 节**
   而不是第 8 节；drill 的四个代码缺陷在 `task_b_sabotage_drill.md` 的**第 6 节**
   而不是第 4 节；`task_b_gate_matrix.md` 里**根本没有 F8/F15 这种编号**
   （它的发现是按闸门组织在第 4 节的，不是按 F 编号）；
   上一版说的「本报告第 7 节」现在对应本文件的**第 8 节**。
   四个指向里四个都错。这正是「打补丁式修订」会留下的典型残渣：
   改了正文没改交叉引用。

### 9.2 本轮的写法（准确的将来式 + 模板位置 + 不留悬空指向）

事实核定：

| 项 | 实测 |
|---|---|
| `ADVERSARIAL_REVIEW.md` | **不存在**（仓库根下无此文件） |
| 模板 | **存在**：`acceptance/ADVERSARIAL_REVIEW_TEMPLATE.md`，19 行、492 字节 |
| 谁要求它 | `README.md` 第 46 行（层2 对抗：「自写 `ADVERSARIAL_REVIEW.md`（HIGH/MEDIUM 全部"已修/驳回+理由"）」）、`README.md` 第 50 行（DoD：「ADVERSARIAL_REVIEW.md 完整」）、`INTEGRATION.md` 第 10 行（push 前置条件链）、`tasks/A-persona-prompt/SPEC.md` 第 16 行（证据要求标题） |
| 这四处能不能改 | **不能**。`README.md`、`INTEGRATION.md`、`tasks/` 都在冻结区，本轮禁改 |

所以本轮的引用一律写成将来式，并指明模板位置。第 10 节的发现清单开头就是这么写的：
「**尚未生成**；生成时应以 `acceptance/ADVERSARIAL_REVIEW_TEMPLATE.md` 为模板，
把下表逐条填进它的『发现清单』表格」。

模板第 18–19 行有两个槽位，本轮的取证结果**已经把它们填满**，
生成 `ADVERSARIAL_REVIEW.md` 时可以直接抄：

- 第 18 行「sabotage_drill.py 结果：__/3 检出（附 evidence 文件名）」
  → **3/3**，附 `evidence/task_b_sabotage_drill.log` 与
  `evidence/task_b_sabotage_drill.md`（判定依据见该文件第 5.2 节）。
  注意上一轮的保留意见（「有效检出实为 2/3」）**已解除**，
  但解除的理由不是 drill 变好了，而是集成后 `g0_freeze` 转 PASS
  让 `eval-tamper` 那一路的前置绿条件成立了——drill 自己依然无法自证，
  缺陷①没有修（`task_b_sabotage_drill.md` 第 5.3 节）。
- 第 19 行「若自实现新闸门：破坏自己实现的哪 3 处、套件是否变红（附日志）」
  → 本轮实际破坏的是**打分器**而不是闸门，共九路（不是 3 处），
  其中 6 路让指标掉、2 路观测不到、1 路基线；254 个单测里
  `tests/test_ranker_mutations.py` 的 10 个用例把其中有牙齿的几路钉成了断言。
  附 `evidence/task_b_self_sabotage.log` 与 `evidence/task_b_self_sabotage.md`。

## 10. 发现清单（只报告不处置）

下表是本轮取证暴露的缺陷、闸门设计问题与证据口径歧义。
**`ADVERSARIAL_REVIEW.md` 尚未生成**；生成时应以
`acceptance/ADVERSARIAL_REVIEW_TEMPLATE.md` 为模板，把下表逐条填进它的
「发现清单」表格（模板第 8–10 行），并按 `README.md` 第 46 行的要求给每条
标上「已修（commit）/ 驳回（理由）」。本节只提供事实与论证出处，不代替那次处置。

完整论证的出处（**章节号已按本轮重写后的实际结构核对**，不是沿用上一版的指向）：
F1'–F9' 在 `evidence/task_b_self_sabotage.md` **第 10 节**；
drill 的四个代码缺陷在 `evidence/task_b_sabotage_drill.md` **第 6 节**；
闸门归因与 `--strict` 语义在 `evidence/task_b_gate_matrix.md` **第 4 节**；
`g0_freeze` 转 PASS 的逐件归因在 `evidence/task_b_gate_snapshot_before.md` **第 4 节**。

### 10.1 仍然成立的发现

| 编号 | 类别 | 一句话 | 出处 |
|---|---|---|---|
| F1' | Goodhart 敞口 | 反过拟合约完全不在闸门判定路径上，而 `run_all.py` 不跑 unittest。实测：清空词典全部 member 或关掉 L3 后 golden 仍满分、v1 掉到 0.6667、v2 掉到 0.6500，真闸门 `g1_memory.run()` 仍是 `problems=[]` `pending=[]` **退出码 0**——**过拟合实现能通过全部 8 个闸门** | `task_b_self_sabotage.md` 第 7、10 节 |
| F2' | 评测集设计 | v1 留出集有位置偏置：12 条的 relevant 全在 `stored` 第 1 位，`rank()` 完全不排序时 v1 仍拿 12/12 = 1.0000。v2 明确打散了首次出现位置，同一路变异下从 24 掉到 12，说明 v2 的设计有效 | `task_b_self_sabotage.md` 第 10 节 |
| F3' | 阈值判别力 | golden 只有 8 对、阈值 0.8，判别余量恰好 1 个样本：错 1 对 = 0.875 仍 PASS，且 0.875 与 1.0000 在闸门输出里同样显示为 `G1_MEMORY: PASS`，看不出实现已经丢了一条 | `task_b_self_sabotage.md` 第 10 节 |
| F4' | 安全余量 | v1 第 6 对（0 基 #5）的 min_margin = 0.0500，**全部由 L4 单独提供**：`W_PREFERENCE = 0` 把它压到 0.0000，命中不变、余量归零，靠 `list.sort` 稳定性维持 | `task_b_self_sabotage.md` 第 10 节 |
| F5' | 实现惰性层 | L5 时态降权对三集指标完全惰性：指标与未命中索引逐位不变，整层删掉 8 个闸门状态不变 | `task_b_self_sabotage.md` 第 5、10 节 |
| F6' | 完整性缺口 | v1/v2 的哈希锁是自测断言，**不在冻结清单里**：`acceptance/MANIFEST.json` 只锁 5 个文件（4 个 vendor + `scenarios.json`），`tests/` 下一个都没有，所以 `g0_freeze` 对这两个集的篡改完全无感。结合 F1'，反过拟合约既不进闸门判定、又不受冻结锁覆盖 | `task_b_self_sabotage.md` 第 10 节 |
| F8' | 覆盖边界 | 颜色类 15 个单字 member 在三集上零可观测性：删掉后三集逐位与基线相同，连 min_margin 都一样。不构成缺陷，但精确划出了评测集的覆盖边界 | `task_b_self_sabotage.md` 第 6、10 节 |
| F9' | 证据可见性 | v2 基线本身低于 0.8（P=0.7742 / R=0.7500），而 8 个闸门全绿。**这个低于 0.8 的数不出现在任何闸门输出里**，谁只看闸门就会以为检索质量达标了 | `task_b_self_sabotage.md` 第 10 节 |
| F10 | drill 缺陷① | `sabotage_drill.py` 无「破坏前该 gate 必须是绿」的前置断言，本来就红的闸门会被恒判为「检出」。本轮靠外部快照补上了这一步，但**缺陷本身没有修** | `task_b_sabotage_drill.md` 第 5.3、6 节 |
| F11 | drill 缺陷② | 「恢复后复跑 gate 验证回绿」的代码位于 `try/finally` 之后，`try` 内 `return` 使其**永不执行**，`RESTORE FAILED` 分支不可达（死代码）。本轮用手工复验替代 | `task_b_sabotage_drill.md` 第 6 节缺陷②、第 7 节 |
| F12 | drill 缺陷③ | `run_gate()` 只返回 `proc.returncode`，**丢弃 stdout/stderr**。三路全成功时整个 drill 只输出一行 `DRILLS DETECTED: 3 of 3`，无法审计跑了哪几路、红在哪一行。这也是「全部 evidence 里 `content drifted from frozen manifest` 只作为源码引用出现过 1 次、从未作为真实报告出现」的原因 | `task_b_sabotage_drill.md` 第 6 节缺陷③ |
| F13 | 证据口径 | `evidence/README.md` 规则 3「保留最后 10 条」与 `run_all.py` 无裁剪逻辑冲突；当前 66 个（7a 时点 60 个），超上限 50 个；且 `run_*.json` 被 gitignore，「保留」对主仓侧不可见，**规则本身无法被执行** | 本文件第 8 节 |
| F16 | 证据口径 | `run_all.py` 第 59 行 JSON 文件名只到秒级，同秒两次调用**静默互相覆盖且无告警**。上一轮实测丢过一份；本轮靠外部 `sleep 3` 规避，但这是取证纪律在补工具的洞，**工具本身没有修** | `task_b_gate_matrix.md` 第 3 节、本文件第 6.3 节 |
| F17 | 棘轮余量 | v2 的三条棘轮里 **recall 与 hits 两条余量为 0**（0.7500 vs 0.75、24 vs 24），precision 余量 0.0042。即 v2 正好压在线上，任何一对从命中翻成未命中都会红。这不是缺陷，是「余量已知为零」这个事实需要写进交接，否则下一个人会以为还有空间 | 本文件第 6.5 节 |
| F18 | DoD 可达性 | `README.md` 第 50 行与 `INTEGRATION.md` 第 10 行把 DoD 写成「`run_all.py --strict` 全绿」。当前 strict 必然 `BLOCKED`，成因是 `g1_permissions`（Task C）与 `g1_tools`（Task E）未实现，**与任务 B 无关**。在 C/E 落地之前，DoD 按字面不可达；而这两处文档都在冻结区，本轮无权改 | `task_b_gate_matrix.md` 第 4.3 节、本文件第 6.3 节 |

### 10.2 已修或已失效的发现（留档，不再作为待处置项）

| 旧编号 | 旧内容 | 现在的状态 |
|---|---|---|
| F7 | 「三路自破坏靠仓库外临时脚本，仓库内无固化资产，重现需要重写脚本」 | **已修**。变异演练已固化为 `tests/test_ranker_mutations.py`（323 行、10 个用例、blob `3aa7a7d4bb4816bcbb75fd296faf263edd68e792`），本轮实测全绿 `Ran 10 tests in 0.050s` / `OK` / 0。仓库外脚本本轮仍在用，但目的是**独立重写评测口径做交叉校验**，不是因为没有仓库内资产 |
| F12（旧） | 「drill 用文本模式改写目标文件，把 CRLF 的 `scenarios.json`（118 处 CRLF）整体归一化成 LF，2870→2753 字节」 | **判定为不成立**，是上一轮误读代码。`sabotage_drill.py` 全文没有 `read_text()`，走 `read_bytes → decode('utf-8') → str.replace → encode('utf-8') → write_bytes`，纯编解码不做换行转换。本轮只读归因实测：三路破坏前后的行尾形态四元组 `(CRLF, bare_LF, bare_CR, BOM)` **逐个相同**，「行尾形态是否被改写 = False」。而且旧数字自身算错（−118+1 ≠ −117）并与同文档另一处「2870→2871」互相矛盾。**F12 这个编号本轮改用于 drill 缺陷③** |
| F14 | 「harness.py 的漂移不是行尾/BOM 造成，6 种变换后无一命中 MANIFEST 期望，需主仓比对原始字节」 | **已由上游裁决并修复**。上游 `10c05d1` 认定 bootstrap 时期记进 MANIFEST 的哈希本身不对（subject 写的是 `CRLF bootstrap drift`），修法是**重算 MANIFEST 期望**而不是回滚文件。harness.py 的字节从头到尾没变过 |
| F15 | 「派单口径『strict 模式三轮全绿』不可达：`g0_freeze` 恒 FAIL 让 verdict 恒为 FAIL，`--strict` 的差异化行为（BLOCKED）永远不会被触发」 | **已失效**。`g0_freeze` 现在 PASS，verdict 不再恒 FAIL，`--strict` 的差异化行为**每次都被触发**：本轮 strict 模式共调用 **6 次**（三轮 3 + drill 后复验 1 + 收尾 2），全部给出 `BLOCKED` / exit 1；当前 evidence 文件里留存 **5 条** `VERDICT: BLOCKED` 记录（`grep -c` 实测；收尾第一次那条随 `final_check.log` 重生成被覆盖，见第 6.3 节）。普通模式对称：调用 6 次全部 `PENDING-OK` / exit 0，留存 5 条。strict 模式现在提供真实信息量：它证明「不绿的原因只剩一条且正当」。后继问题是 DoD 的字面可达性，另立为 F18 |

### 10.3 本轮新发现（上一版没有的）

| 编号 | 类别 | 一句话 |
|---|---|---|
| F17 | 棘轮余量 | v2 的 recall 与 hits 两条棘轮余量为 **0** |
| F18 | DoD 可达性 | 冻结区里的 DoD 写着「strict 全绿」，在 Task C/E 落地前按字面不可达，而这两处文档本轮无权改 |
| F19 | 交叉引用腐坏 | 上一版第 127 行的四个章节指向**四个全错**（第 8 节→第 10 节、第 4 节→第 6 节、gate_matrix 根本没有 F 编号、本报告第 7 节→第 8 节）。这是「打补丁式修订」的典型残渣，也是任务书要求「重写而不是打补丁」的直接理由。本轮所有交叉引用都按重写后的实际结构重新核对过 |
| F20 | 工具返工（取证者自己的） | 本轮两个仓库外脚本第一版各有缺陷，都已修正并**在日志里如实记录**：① `drill_attribution.py` 第一版用含 `bytes=` 的字符串比较行尾形态，导致三路全部误报「行尾形态被改写 = True」（与要证明的结论方向相反）；② `mutate_eval.py` 第一版调 `score_holdout_v2(HOLDOUT_V2)` 未显式传 ranker，而它的 ranker 是**默认参数**、def 时已绑定，patch 不到，导致 `unsorted_rank` 一路误报 `*** DIVERGE ***`。两处都不是仓库缺陷，但如果不记，读者会把假信号当成实测结论 |
| F21 | 证据自指泄漏（取证者自己的，本轮犯了五次） | 为了解释消毒而把探针的字面样式串印进文档，文档就会命中自己描述的探针。本轮同类错误共出现 **5 次**：① `sabotage_drill.md` 早前的版本（1 处）；② 本文件第 7.1 节早前的版本（8 处）；③ 本轮重写后的 `sabotage_drill.md` 第 38–39 行（3 处，被扫描第 1 轮抓到）；④ 修 ③ 时的第一版修订正文又把「改前原文」整句引了下来（在重扫前自己发现并改掉，未进过任何一轮扫描）；⑤ 扫描器自己的 P16 语义描述（1 处，被第 2 轮抓到）。**根因是同一条：一个展示某形态的描述，本身就是该形态。** 已固化成纪律：探针一律用 ID + 语义指代。附带发现：扫描报告扫到的是**上一轮的它自己**（一步滞后），所以单轮为 0 不构成证据，判收敛必须连跑两轮并比对（第 7.1 节） |

## 11. 结论

1. **7a 全绿，与起点逐格一致**：8 闸门 `0/0/0/0/0/2/2/0`、FAIL 数 0、
   254 单测 `OK`/exit 0、`run_all.py` 普通模式 `PENDING-OK`/0 与 strict 模式
   `BLOCKED`/1（两者都零 FAIL）、`report_retrieval.py` 六种模式全部 exit 0、
   冻结件 5/5 MATCH、EOL 残留探针 PASS、三集指标 golden 8/8 1.0000 /
   v1 12/12 1.0000 / v2 24/32 P=0.7742 R=0.7500。
2. **本轮取证对仓库零写入**（第 6 步的 evidence 提交除外）：tracked 工作区自始至终干净，
   HEAD 与 HEAD tree 全程未变，冻结区 5 件逐件 CLEAN 且 blob 三方相等。
   「没跑过 `--update`、没手改过 MANIFEST」这件事有 **git 记录级的证明**（第 2.1 节）：
   `MANIFEST.json` 与 `.gitattributes` 只被上游两条 commit 碰过，本地 39 条一次都没碰
   （第 6 步之后本地是 43 条，7b 重测触碰数同样是 **0**）。
3. **相对上一轮，唯一一处闸门状态变化是 `g0_freeze` 从 FAIL 转 PASS**，
   可逐件归因、可复算、且归因落在上游那一侧（第 4 节）。
4. **M18 已修**：`ADVERSARIAL_REVIEW.md` 的引用改成准确的将来式并指明模板位置
   `acceptance/ADVERSARIAL_REVIEW_TEMPLATE.md`；同时修掉了旧引用里**四个全部失效的
   章节指向**（第 9.1 节），本轮所有交叉引用按重写后的实际结构重新核对。
5. **H7 同族问题已修**：本轮全部时间戳由 `date` 生成，7a 收尾落在
   2026-09-04 17:04:02 → 17:04:12 之间，**同一天，没有跨日**。
   （上一版是 2026-09-02 17:39 起、2026-09-03 07:55 收尾复核，跨日。）
6. **H8 同族问题已修**：本轮全部行数由 `wc -l` 生成，计数逐个可复算
   （19 份实质证据文件 + 1 份扫描记录 + 1 份 7b 清单 = 21 份本轮拥有，18 个不含本文件
   合计 **3191** 行、66 个 `run_*.json`、本地 43 条 commit）。
   上一版这三处分别是 18 个 / 1721 行 / 15 个，且与另一份文档互相矛盾。
   本轮自己的合计值也改过一次（3174 → 3191），原因是 `sabotage_drill.md`
   因如实记录扫描失败而长了 17 行；两个数都是 `wc -l` 实测，3174 + 17 = 3191（第 7 节）。
   同一族的问题本轮又抓到两处并已修：`run_*.json` 计数（60 → 66，只增不减，
   已改成带时点引用）与扫描的 P18 总数（133 → 209，已逐字归因到 7b 那一个文件）。
7. **手工扫描已做到不动点**：19 个探针× 24 个目标文件，泄漏类（P01–P17）
   合计 **0**，退出码 **0**，最后连续两轮报告除时间戳外逐字相同（第 7.1–7.3 节）。
   那枚已被要求吊销的 GitHub PAT 以任何形式都未出现。
   扫描本身不是一跑就绿：第 1–3 轮退出码都是 1，共抓到 4 处自指泄漏，
   已全部修掉并如实留档（F21）。
8. **待办移交**：7b（提交后的 git status、最终 commit 数、8 闸门复跑、
   全部 tracked 文件的 `wc -l` + blob 哈希清单）在
   `evidence/task_b_blob_manifest.md`；发现清单 F1'–F21 只报告不处置，
   等 `ADVERSARIAL_REVIEW.md` 生成时按模板逐条填。
9. **不 push**。本轮结束时 ahead 39 / behind 0，没有执行任何 push、force、
   rebase、author 改写、git config 修改、远端 URL 修改或凭据写入。
   author 改写由后续专人按备份 tag + tree 逐字节比对的规程执行。
