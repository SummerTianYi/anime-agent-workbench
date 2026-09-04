# 任务 B 取证收尾自证（7b）：提交后的世界、逐文件行数与 blob 哈希清单

generated : 2026-09-04 17:41:55 +0100

> **【关于 commit hash 的显式标注】本文件里出现的 commit hash 是 author 改写前的值。**
> push 前全部本地 commit 的 author 会被改写为与上游那个 commit 一致的身份，
> 改写后**所有 commit hash 全部失效**。长期有效的稳定锚点是 **blob 哈希与 tree 哈希**，
> 以及 commit 的 **subject + 序数**：author 改写不动 tree 也不动 blob，
> 这两类哈希在改写前后逐字不变。复核时请勿拿本文件里的 commit hash 去 `git show`，
> 那会打不到东西、并误判成证据造假。

本文件是第 7 步的**提交后**一半（7b）。提交前的一半（7a）在
`evidence/task_b_final_check.log` 与 `evidence/task_b_final_selfcheck.md` 里。
拆成两半的理由在 7a 的第 0 节写过，这里只说 7b 存在的意义：**只有 7b 能看到
「往仓库里加了 20 个 evidence 文件」这件事之后的世界**，因此只有它能证明
这次提交没有扰动任何一个被闸门看的东西。7a 与 7b 的 8 闸门结果逐格比对见第 5 节。

消毒规则：仓库根记作 `<repo>`，仓库外临时目录记作 `<scratch>`，
用户家目录前缀记作 `<home>`。所有数字均由命令输出产生，无一处手抄：
时间戳来自 `date`，行数来自 `wc -l`，blob 哈希来自 `git hash-object`，
sha256 来自 `hashlib`，退出码来自子进程 `returncode`。

### 本文件不可能包含的三样东西

先把话说在前面，免得复核时以为漏了：

| # | 缺什么 | 为什么不可能有 | 到哪里去看 |
|---|---|---|---|
| 1 | 本文件自己的 blob 哈希 | blob 哈希是内容的函数；一份内容要包含自己的哈希，就得在写完之后改变，改变了哈希又变 | 交付报告；或复核者自己跑 `git hash-object evidence/task_b_blob_manifest.md` |
| 2 | 本文件自己的行数 | 写下这个数字本身就会改变这个数字 | 同上，`wc -l` |
| 3 | 最终的 HEAD tree 哈希 | tree 包含本文件的 blob，所以 tree 哈希依赖于「已经含有 tree 哈希的内容」 | 交付报告。**它是主锚点**：拿到 tree 哈希，树里每一个 blob（包括本文件的）都能独立复验 |

这三条与 7a 的第 0 节是同一个道理的不同层次：7a 不能记录提交之后的世界，
7b 能记录提交之后的世界、但不能记录它自己被提交之后的世界。
**最终 tree 哈希放在交付报告（聊天消息，不进仓库）里，正是为了切断这个环。**

## 1. 提交后的 git 状态

| 项 | 值 | 命令 |
|---|---|---|
| tracked 工作区状态 | `''` | `git status --porcelain -uno` |
| HEAD commit（author 改写前） | `0150a008d0444241c9c1fd1100ac16fa59b5d7d6`（短 `0150a00`） | `git rev-parse HEAD` |
| **HEAD tree（稳定锚点）** | `7805665e918b34408b4be08bef4efff189c2992b` | `git rev-parse HEAD^{tree}` |
| ahead / behind | **43 / 0** | `git rev-list --left-right --count origin/main...HEAD` |
| `origin/main..HEAD` commit 数 | **43** | `git log --format=%h origin/main..HEAD \| wc -l` |
| 剩余 untracked | 2 个 | `git status --porcelain -uall` |
|   | `evidence/task_b_blob_manifest.md` |
|   | `evidence/task_b_gate_objections.md` |

- **tracked 工作区为空 = True**。第 6 步的四个 commit 之后没有留下任何未提交改动。
- 剩余 untracked 共 2 个：**本文件自己**（它正在被生成，还没提交）与并行修改中的那一份闸门异议卷宗。后者本轮全程禁读、禁写、禁 `git add`、不纳入任何统计，由最终 push 前检查单独扫。

  这里有一个绕不过去的自指：**本文件永远无法报告「它自己被提交之后」的 status**。它生成时自己必然是 untracked，所以它看到的永远不是终态。终态留给复核者验：在本文件被提交之后跑 `git status --porcelain -uall`，应当只剩并行修改中的那一份。
- behind = 0，快进关系成立，push 时不需要 force。
- `evidence/run_*.json` 被 `.gitignore` 第 4 行忽略，不出现在 status 里，也**没有被强制 add**。

**关于最终 commit 数**：上表的 43 是本文件生成时的值，也就是第 6 步四个
docs(evidence) commit 之后的状态。本文件自己会成为第 **44** 条。
那一条之后的状态无法由任何仓库内文件报告，最终数字见交付报告。

## 2. 第 6 步的四个 commit，以及全部 commit 的序数清单

本轮新增 **4** 个 commit，全部以 `docs(evidence):` 开头，全部只添加 `evidence/` 下的文件：

| 序数 | 短 hash（author 改写前） | subject | 添加了几个文件 |
|---|---|---|---|
| 40 | `7239f7f` | docs(evidence): 补三轮双模式闸门取证与 48 格矩阵 | 10 |
| 41 | `6431d5f` | docs(evidence): 补 sabotage_drill 取证、前置绿快照与手工复验回绿 | 5 |
| 42 | `53cedc3` | docs(evidence): 补反 Goodhart 自证（九路变异 x 三集）与中间态数字复核 | 2 |
| 43 | `0150a00` | docs(evidence): 补收尾自证 7a 与提交前手工扫描记录 | 3 |

为什么小步而不是一次提交：四个 commit 各自对应一项可独立复核的证据（DoD a 项的闸门矩阵 / DoD b 项前半的 drill / DoD b 项后半的反 Goodhart 自证 / 收尾与准入扫描），复核者可以只读其中一段。每个 commit message 里都写了「为什么这样分」。

扫描记录只能落在最后一个 commit：它是提交前的准入检查，覆盖对象包含前三个 commit 里的
全部文件，在那些文件写完之前它不存在；也不能提前到第一个 commit，那时它扫不到后面才写的文件。

### 2.1 全部 commit 的序数 + 短 hash + subject

**序数与 subject 是稳定锚点，短 hash 不是。** `evidence/task_b_gate_snapshot_before.md` 第 5.1 节里有一个已经发生过的实例：上一版文档记的 7 个 hash 里有 6 个已经因为 rebase 换基而失效了，author 改写会对下表全部条目做同一件事。

| 序数 | 短 hash（author 改写前） | subject |
|---|---|---|
| 1 | `f60e946` | feat(memory): 补检索文本归一化与字符 bigram 相似度 |
| 2 | `a70a1ab` | feat(memory): 补概念词典桥接，让无字面重叠的查询能命中 |
| 3 | `80d794a` | feat(memory): 补偏好断言加权与临时状态降权 |
| 4 | `ed4528f` | feat(memory): score_retrieval 落地宏平均查准查全评测 |
| 5 | `4e18ffa` | feat(memory): MemoryStore 增补按查询排序的召回与 prompt 片段格式化 |
| 6 | `9ab6b8e` | docs(memory): 补检索难度分析、留出集结果与主仓集成说明 |
| 7 | `8158ed5` | fix(memory): recall_relevant 改按行下标排序，修重复 fact 文本下的身份归并 |
| 8 | `f0de024` | fix(memory): format_memory_prompt 三层消毒，堵住存储型 prompt 注入 |
| 9 | `ee49e71` | fix(ranker): 词典与打分语义三修（M1 单字 head / M2 极性 / M4 嵌套计数） |
| 10 | `bc9046b` | docs(ranker): M3 bigram_similarity 契约改为如实描述余弦的成比例性质 |
| 11 | `b12a5e0` | perf(memory): M5 扫描窗口上限 + M6 query 侧预计算与长度上限 |
| 12 | `2235cc6` | test(memory): M11 变异演练 + M7/M10/L5/L12/M20 测试有效性 |
| 13 | `110ac45` | test(memory): L1-L8/L11/M19 延后项的复现测试（TDD 红阶段快照） |
| 14 | `db2b848` | fix(ranker): L3 None 折转 + L4 casefold 与通用标点剥离 + L6 词典只读化 |
| 15 | `ba1035c` | fix(memory): L1 scope 谓词单点化 + L2 recall_relevant 入参校验 |
| 16 | `2150e84` | test(holdout): v2 接线——计分口径先定、sha256 审计锁、语料结构交叉核对 |
| 17 | `fbf284b` | test(analysis): 三集检索分析固化——v2 逐对明细/分层归因/消融/权重敏感性 |
| 18 | `e75d09e` | test(lexicon): H2 反过拟合判据重建——三集并集 + 占比上限 + 填充词免疫（红阶段快照） |
| 19 | `ab4c220` | test(retrieval): TDD 红阶段——RC-3a/RC-3b/RC-5 三条 L3/L4 结构缺陷的复现测试 |
| 20 | `49b774c` | fix(ranker): RC-5 —— 查询侧的偏好谓词本身就决定 L4 的取向 |
| 21 | `82c8f06` | fix(ranker): RC-3a/RC-3b —— L3 的双侧 head-only 排除与跨类 noisy-OR 合成 |
| 22 | `14b53ad` | test(holdout): 把 v2 语料纳入版本控制 |
| 23 | `52e8c27` | fix(lexicon): 按外部通用知识规则扩词，词典拆出 memory_lexicon |
| 24 | `2672dad` | test(analysis): 词典审计对照表模式——把反 Goodhart 的证据变成可复跑的输出 |
| 25 | `af81aec` | test(ranker): RC-4 红阶段——极性谓词规则「极性前缀 + 单字活动动词」的产物集不完整 |
| 26 | `e8c1fd8` | fix(ranker): RC-4 补全极性谓词构词规则，RC-7 修否定辖域丢失导致的极性反转 |
| 27 | `6d3667b` | test(analysis): RC-2 判定依据的复跑口径——L2 四归一化 + W_BIGRAM 扫描 |
| 28 | `0baf60a` | docs(ranker): RC-2 判定为不可原则性修复，附特征化测试钉住稀释比值 |
| 29 | `6689b40` | test(holdout-v2): 3.3 棘轮断言——v2 钉实测值，golden/v1 钉满分不回归 |
| 30 | `5ff9072` | test(analysis): 3.4 消融补 M15 口径与 owner，敏感性补翻转归因与脆弱对榜 |
| 31 | `db3c2ee` | test(memory): N4 拆分 test_memory_retrieval.py 为三文件（纯搬移，219 项不变） |
| 32 | `ce8fb2a` | test(holdout): N2 消毒 v2 语料的隐私自述注释——数据 digest 逐字节未变 |
| 33 | `42d1159` | test(n10): N10-1 判据先行——权重鲁棒性的目标/硬约束/禁止理由先落盘，扫描留空 |
| 34 | `99cfeca` | test(n10): N10-2 扫描落地——W_PREFERENCE 六值 × 88 格全跑完，负面结果，保持 0.10 |
| 35 | `29eb2bc` | test(n10): N10-3 决策落地——驳回调权重，四个值一个不改，负面结果留在常量旁边 |
| 36 | `d30bc41` | docs(ranker): 按最终状态整段重写 analysis.md（H4/H6/M14-M17/L9/L10 全修正） |
| 37 | `6a6264b` | docs(ranker): 按最终状态整段重写 integration.md（H4/L9/闸门归因/建议） |
| 38 | `0ed5f15` | docs(ranker): 修正语料规模口径「100 对」→「52 对语料」并补 PEP8 空行 |
| 39 | `d6868c6` | test(n1): 按正确粒度重写 N1 不修理由并固化成变异测试 |
| 40 | `7239f7f` | docs(evidence): 补三轮双模式闸门取证与 48 格矩阵 ←本轮 |
| 41 | `6431d5f` | docs(evidence): 补 sabotage_drill 取证、前置绿快照与手工复验回绿 ←本轮 |
| 42 | `53cedc3` | docs(evidence): 补反 Goodhart 自证（九路变异 x 三集）与中间态数字复核 ←本轮 |
| 43 | `0150a00` | docs(evidence): 补收尾自证 7a 与提交前手工扫描记录 ←本轮 |
| 0（基底） | `10c05d1` | fix: regenerate frozen MANIFEST (CRLF bootstrap drift) + force LF via .gitattributes（author `SummerTianYi`，即 `origin/main`，不在本地提交里） |

## 3. 冻结区复核（提交后重测）

| 冻结件 | `git diff --stat` | `git diff --stat HEAD` | `hash-object` == `HEAD:` | sha256 == MANIFEST |
|---|---|---|---|---|
| `vendor/agent_core/harness.py` | 空 | 空 | True | True |
| `vendor/agent_core/song_catalog.py` | 空 | 空 | True | True |
| `vendor/agent_core/voice_text.py` | 空 | 空 | True | True |
| `vendor/agent_core/data/luotianyi_original_songs.json` | 空 | 空 | True | True |
| `acceptance/evals/scenarios.json` | 空 | 空 | True | True |

=> 冻结区 5 件全部无改动且哈希相符 : **True**

逐件 sha256（`hashlib`，与 MANIFEST 期望值逐一比对）：

| 冻结件 | sha256（实测 = MANIFEST 期望） |
|---|---|
| `vendor/agent_core/harness.py` | `cb1ae928f80674952c4ac6e6385d260a7dbd5cf93ac5ab96889ff6bdb32b2807` |
| `vendor/agent_core/song_catalog.py` | `57d257d1084a67271a78a3b79393839c1442d37499c8a25862d80071a411e49e` |
| `vendor/agent_core/voice_text.py` | `c652a1b868029a5f1d46b23e1720af44363081ce441c1ff008bcc86f913e4da8` |
| `vendor/agent_core/data/luotianyi_original_songs.json` | `22552757d32c86e1bf9d52217c3c3ff588bd35a86ba1ceada6707198f2710f8d` |
| `acceptance/evals/scenarios.json` | `2c5dab3fc5e414680193c7b998bb62cf9fe3c6299f2f002682a75efa8179b00e` |

git 记录级的证明（比哈希对照更强，因为它与「有没有恰好改回原样」无关）：

```
$ git log --format='%h' origin/main..HEAD | while read h; do
      git show --name-only --format='' $h \
        | grep -E '^acceptance/MANIFEST.json$|^\.gitattributes$|^vendor/agent_core/|^acceptance/evals/scenarios.json$'
  done
（43 条全部无输出：命中数 = 0）
```

=> 本地 43 条 commit 对冻结区与 MANIFEST 的触碰次数 = **0**

这条排除了「取证者跑过 `g0_freeze.py --update`」与「取证者手改 MANIFEST 让闸门变绿」
两种可能——不是靠声明，而是靠 git 自己的提交记录。`MANIFEST.json` 只被上游修复与
bootstrap 两条 commit 碰过，`.gitattributes` 只被上游修复碰过，两条都不在本地提交里。

**本轮四个 docs(evidence) commit 各自改了哪些文件**（`git show --name-only`，逐个列出）：

- `0150a00`：3 个文件，全部在 `evidence/` 下 = True
- `53cedc3`：2 个文件，全部在 `evidence/` 下 = True
- `6431d5f`：5 个文件，全部在 `evidence/` 下 = True
- `7239f7f`：10 个文件，全部在 `evidence/` 下 = True

=> 四个 commit 合计触碰 `evidence/` 以外的文件数 = **0**
=> 即：`src/`、`tests/`、`acceptance/`、`vendor/`、`tasks/`、`.gitattributes` **一个都没有被 add 或 commit**。

## 4. 8 闸门提交后逐个重跑

| 闸门 | 起点 | 7a | **7b（提交后）** | 三者一致 | verdict |
|---|---|---|---|---|---|
| `g0_environment` | 0 | 0 | **0** | True | PASS |
| `g0_secrets` | 0 | 0 | **0** | True | PASS |
| `g0_freeze` | 0 | 0 | **0** | True | PASS |
| `g1_contract` | 0 | 0 | **0** | True | PASS |
| `g1_memory` | 0 | 0 | **0** | True | PASS |
| `g1_permissions` | 2 | 2 | **2** | True | PENDING |
| `g1_tools` | 2 | 2 | **2** | True | PENDING |
| `g3_simulate` | 0 | 0 | **0** | True | PASS |

```
  TOTAL: PASS=6 FAIL=0 PENDING=2  (of 8)
  => 与期望矩阵 0/0/0/0/0/2/2/0 一致 : True
  => 与 7a 逐格一致 : True
  => FAIL 数 = 0
```

**判读**：添加 20 个 evidence 文件（合计约 3800 行）之后，8 个闸门的退出码逐格未变，FAIL 数仍为 0。这正是 7a/7b 拆分要证明的事——
`g0_environment` 与 `g0_secrets` 的 `SCAN_DIRS` 不含 `evidence/`，
所以往 `evidence/` 里加文件对闸门是**不可见的**；这既是「提交不会弄红闸门」的好消息，
也是「闸门看不见 evidence 里的泄漏」的坏消息，后者靠第 7 节的手工扫描补偿。

## 5. 单元测试（提交后重跑）

```
$ ./.venv/bin/python -m unittest discover -s tests -p 'test_*.py' -t tests
----------------------------------------------------------------------
Ran 254 tests in 0.169s

OK
===EXIT=0===
```

- 用例数 = **254**（7a 是 254，起点也是 254）
- 退出码 = **0**（7a 是 0）
- 结果行含 `OK` = True；耗时 0.169s
- => 与 7a 一致 : **True**

`-t tests` 是必需的：用 `-t .` 会报 `ImportError: Start directory is not importable`。

## 6. `run_all.py` 双模式（提交后重跑）

### 6.1 普通模式

  sleep 3 before invocation at 2026-09-04 17:41:57 +0100
```
$ ./.venv/bin/python acceptance/run_all.py
PASS     g0_environment
         G0_ENVIRONMENT: PASS
PASS     g0_secrets
         G0_SECRETS: PASS
PASS     g0_freeze
         G0_FREEZE: PASS
PASS     g1_contract
         G1_CONTRACT: PASS
PASS     g1_memory
         G1_MEMORY: PASS
PENDING  g1_permissions
         evaluate() not implemented (Task C)
         G1_PERMISSIONS: PENDING
PENDING  g1_tools
         openai_schema/execute not implemented (Task E)
         G1_TOOLS: PENDING
PASS     g3_simulate
         G3_SIMULATE: PASS
evidence: evidence/run_20260904_174200.json
VERDICT: PENDING-OK
===EXIT=0===
```

- verdict = **PENDING-OK**，退出码 = **0**，FAIL 行 = 0，PENDING 行 = 2
- `evidence/run_*.json` 计数：调用前 64 → 调用后 65，新建 ['run_20260904_174200.json']
- => 无同秒覆盖 : **True**

### 6.2 `--strict` 模式

  sleep 3 before invocation at 2026-09-04 17:42:00 +0100
```
$ ./.venv/bin/python acceptance/run_all.py --strict
PASS     g0_environment
         G0_ENVIRONMENT: PASS
PASS     g0_secrets
         G0_SECRETS: PASS
PASS     g0_freeze
         G0_FREEZE: PASS
PASS     g1_contract
         G1_CONTRACT: PASS
PASS     g1_memory
         G1_MEMORY: PASS
PENDING  g1_permissions
         evaluate() not implemented (Task C)
         G1_PERMISSIONS: PENDING
PENDING  g1_tools
         openai_schema/execute not implemented (Task E)
         G1_TOOLS: PENDING
PASS     g3_simulate
         G3_SIMULATE: PASS
evidence: evidence/run_20260904_174203.json
VERDICT: BLOCKED
===EXIT=1===
```

- verdict = **BLOCKED**，退出码 = **1**，FAIL 行 = 0，PENDING 行 = 2
- `evidence/run_*.json` 计数：调用前 65 → 调用后 66，新建 ['run_20260904_174203.json']
- => 无同秒覆盖 : **True**

### 6.3 与 7a 逐格比对

| 模式 | 7a verdict | 7b verdict | 一致 | 7a 退出码 | 7b 退出码 | 一致 |
|---|---|---|---|---|---|---|
| 普通 | `PENDING-OK` | `PENDING-OK` | True | 0 | 0 | True |
| `--strict` | `BLOCKED` | `BLOCKED` | True | 1 | 1 | True |

两次调用之间 `sleep 3`，因为 `run_all.py` 第 59 行用只到秒级的时间戳给 JSON 命名，
同秒两次调用会静默互相覆盖且无告警。

`evidence/run_*.json` 当前共 **66** 个，全部被 `.gitignore` 忽略、一个都没有 add。`evidence/README.md` 规则 3 要求「保留最后 10 条」，而 `run_all.py`
第 57–60 行只写不删、没有任何裁剪逻辑，且这些文件对主仓侧不可见——这条口径冲突记为 F13，取证者一个都没删也一个都没 add。

这个数字与 7a 里记的 60 不相等是**正常的，不是矛盾**：7a 那个 60 是当时`ls evidence/run_*.json | wc -l` 的实测值，而每调一次 `run_all.py` 就会多一个。7a 之后又跑过 7b，所以只增不减。两个数都是各自时刻的实测值，比较它们时必须把「中间又调了几次」算进去。

## 7. 逐文件行数与 blob 哈希清单（全部 tracked 文件）

生成本文件时 tracked 文件共 **74** 个（`git ls-files | wc -l`）。
本文件自己会成为第 **75** 个，它**不在下表里**，理由见开头的三条自指限制。

blob 哈希由 `git hash-object <path>` 生成，行数由 `wc -l <path>` 生成。
**blob 哈希是 author 改写前后唯一逐字不变的定位锚点。**

| # | 文件 | 行数（`wc -l`） | blob（`git hash-object`） | sha256（前 16 位） |
|---|---|---|---|---|
| 1 | `.gitattributes` | 1 | `6313b56c57848efce05faa7aa7e901ccfc2886ea` | `d60f352d0db1404c…` |
| 2 | `.gitignore` | 4 | `76f9f2111231c6425e169674e63ecc1bfa9479f9` | `6b38e1848520d3f2…` |
| 3 | `INTEGRATION.md` | 12 | `3ba574e66a8a8ad298698c5c37a88f8c78a0c2e2` | `b57ea79841a38ae5…` |
| 4 | `README.md` | 59 | `8fba8bf3d3538d99efe133f81fe5cdee2bed95a6` | `cc3085a6499789e5…` |
| 5 | `acceptance/ADVERSARIAL_REVIEW_TEMPLATE.md` | 19 | `f05eb8c5e3ddf16d10663eb6f9f311fe835fbaf3` | `d75fd638774851a6…` |
| 6 | `acceptance/MANIFEST.json` | 6 | `b93dbab76542e93eedd98a365f1f089f9ab4c934` | `274f6e491045832c…` |
| 7 | `acceptance/evals/providers.py` | 88 | `d0d5d8fb3e1075556d125cd53f05ad003a8528e5` | `af8a975b9a77daf6…` |
| 8 | `acceptance/evals/scenarios.json` | 118 | `53ab5c2bf54027f3e333e0f980259acbe0e72150` | `2c5dab3fc5e41468…` |
| 9 | `acceptance/gates/g0_environment.py` | 53 | `30b0d4e15308f55c9cf676f681f5d0cf179d56a8` | `6469d0b1fa5d5b65…` |
| 10 | `acceptance/gates/g0_freeze.py` | 55 | `7a3bba278d99087be8f1ec7cf25970cf93af97a9` | `558e64117d6cbb9d…` |
| 11 | `acceptance/gates/g0_secrets.py` | 40 | `c9bcecb6f4738001edb37188cf48fc2ad41ba5cc` | `fa9174fa240f40a5…` |
| 12 | `acceptance/gates/g1_contract.py` | 101 | `5ea2795fcef7db15b1e6ba4b29c0536d015cf74f` | `73a8f897584f9398…` |
| 13 | `acceptance/gates/g1_memory.py` | 70 | `7bca7b83221865fd23c36243229653c91a8c81b9` | `21cacd162b4eb3c0…` |
| 14 | `acceptance/gates/g1_permissions.py` | 46 | `31ab51c6df85cb3e18e2d83503269a88e53c5d3a` | `16147f778b5a4f2c…` |
| 15 | `acceptance/gates/g1_tools.py` | 46 | `af0c955c49d83e2480e6c8e4cec53313238a444d` | `d5576dbe92ac640c…` |
| 16 | `acceptance/gates/g3_simulate.py` | 65 | `0ffe595a3ea138d5f1b7edf8d9231bd4a520c022` | `8e97b9e461c2f7de…` |
| 17 | `acceptance/run_all.py` | 67 | `984f9ed0c0eb7f31158641fd32d7c07bd77d6852` | `79444a9b4ef69964…` |
| 18 | `acceptance/sabotage_drill.py` | 60 | `0c4ce0bb4ceb74d7c4ad9d7aee84c97d6c3d3d34` | `be17184c8f3cc523…` |
| 19 | `evidence/README.md` | 8 | `7cc1b45a4bb89d635b626b3ae318ea1aca415038` | `55363b2b1a1faf36…` |
| 20 | `evidence/task_b_after_drill.log` | 243 | `856ddb7cbff62a70ce726916fd380f6aefa37e83` | `a8e0975cb816d9d4…` |
| 21 | `evidence/task_b_drill_attribution.log` | 105 | `9738994830fe30d655cd94c9f0ed2c7ce4a605f7` | `15701c2e85411163…` |
| 22 | `evidence/task_b_final_check.log` | 393 | `941b28a2f92014008fbb7e52c16b01b57a4ce515` | `7f263299bcf477b4…` |
| 23 | `evidence/task_b_final_selfcheck.md` | 690 | `5c420d5dcff7906734726392cfc562c60f705a30` | `1f0145503c15b6da…` |
| 24 | `evidence/task_b_gate_matrix.md` | 250 | `d9867c2b33577d1082d8951b5aea9c006c28a38d` | `982822a0d7634ae3…` |
| 25 | `evidence/task_b_gate_snapshot_before.md` | 570 | `34fcdb732d2cc252a5c1b530e2d7e23b137526dd` | `53ba249d07970c58…` |
| 26 | `evidence/task_b_integration.md` | 189 | `21a3e3e218eab96544b09a2540ab2a5a97ed2736` | `2e630d123efdcbc0…` |
| 27 | `evidence/task_b_retrieval_analysis.md` | 472 | `e9b31418b975737202901792d50dcd5640ae803b` | `e10f3f31ec35bdb9…` |
| 28 | `evidence/task_b_round1_normal.log` | 52 | `2846b481ae5f476fe5284af9017df822744764c4` | `bb9c1ebe7e7b9275…` |
| 29 | `evidence/task_b_round1_strict.log` | 32 | `a0640fc022b0658da3bfbe870eb7ddfb0f742041` | `2b0d7bb6d369468c…` |
| 30 | `evidence/task_b_round1_unittest.log` | 14 | `258ae730847828359e623d8d4b0b53bb9fceda05` | `8831f75c232dc9f4…` |
| 31 | `evidence/task_b_round2_normal.log` | 52 | `45f1338157ad9b659936b6642e684dcd0d64f7b7` | `f38b65c6f8b898a0…` |
| 32 | `evidence/task_b_round2_strict.log` | 32 | `a9f948bd28a5b5667b7c736b1f630a2bdf7da1f1` | `8fb96a04f4da3b60…` |
| 33 | `evidence/task_b_round2_unittest.log` | 14 | `9f551ec8cbdd9c1dc5cb2ed948f802cbab90912f` | `951849c22b7376f8…` |
| 34 | `evidence/task_b_round3_normal.log` | 52 | `3b0e50b07c13e4a378b776065647e9244e7ef9fd` | `a896cfcc94cf507b…` |
| 35 | `evidence/task_b_round3_strict.log` | 32 | `4240c84fe7e1dd12f386a885efc2eb2fa2345c5f` | `7fc8f892be586cc3…` |
| 36 | `evidence/task_b_round3_unittest.log` | 14 | `f0e424da1840d10d7c9f8c76ce3d7fae9f30fc36` | `50e10b62c43aa3b0…` |
| 37 | `evidence/task_b_sabotage_drill.log` | 9 | `5df7c696ce1329ef37bff9473ecc39c27958ed33` | `de94fe8194a5ce57…` |
| 38 | `evidence/task_b_sabotage_drill.md` | 470 | `4ec401055ca7566f1fc38c8cabf783634b41235c` | `a4609588babfe905…` |
| 39 | `evidence/task_b_scan_report.log` | 148 | `3b73298b3accd2b45cee5c1d669bd73a31648210` | `a0cb50bd3fd4aadc…` |
| 40 | `evidence/task_b_self_sabotage.log` | 362 | `81768fdf167cf812a6fb27fc099463e890de6990` | `4bd83f5b8e3f1762…` |
| 41 | `evidence/task_b_self_sabotage.md` | 495 | `0fa500f80835c216a014c4df9f35bbfef613b982` | `e7a9d77bb29b7d44…` |
| 42 | `examples/pilot.md` | 5 | `93d88543d8f9330edf340b0aca1bea95450ce938` | `72bd45af39ec9698…` |
| 43 | `src/__init__.py` | 1 | `ce098d2ec2c57bf89ea0053c415c45498a6d32a6` | `169d2036446b8f25…` |
| 44 | `src/memory_lexicon.py` | 349 | `bfba659bc411a981b7d9df8913a70793d6d63c6e` | `777c3a5835633589…` |
| 45 | `src/memory_ranker.py` | 767 | `2a125cae23544790a7e7f188b11f32c5e4070b55` | `e204b36022b071df…` |
| 46 | `src/memory_store.py` | 259 | `49d273aa9286afdf4d6f649b915c56042c9354e1` | `3c81cd6b973a2b18…` |
| 47 | `src/permissions.py` | 47 | `84ab25bb8e66d449f13c7826d98c8557c79fcef7` | `84fbc5a888436895…` |
| 48 | `src/prompt_persona/__init__.py` | 0 | `e69de29bb2d1d6434b8b29ae775ad8c2e48c5391` | `e3b0c44298fc1c14…` |
| 49 | `src/prompt_persona/system_prompt.py` | 21 | `3034e3dcc3bb97a3c01ccdf250db67dc22872bab` | `6ff0104e02235664…` |
| 50 | `src/tools_registry.py` | 40 | `786f2b6f2a4d4fdffb21ffd8d06e271daf349e54` | `ee0c4960a1baf311…` |
| 51 | `tasks/A-persona-prompt/SPEC.md` | 20 | `10aeb2568fa623dbfb9160d88e98caa50b32f96c` | `46a926af02ae21ae…` |
| 52 | `tasks/B-memory-system/SPEC.md` | 16 | `e6d0e0eafa8ce2b3c9ee520e9511dcb7cc23b05c` | `ce6c18296ac924a1…` |
| 53 | `tasks/C-permission-layer/SPEC.md` | 16 | `0e4fb9db499c5aa9a84e48e0284d3403afd569c3` | `8d3a535f851d9ffb…` |
| 54 | `tasks/E-readonly-tools/SPEC.md` | 16 | `0d22cefd0068b788fba85b330713a3000400d7c2` | `bd632fd2b41e18b0…` |
| 55 | `tests/holdout_v2.py` | 301 | `fcf727ff1a27cc5658c8023bbbb0ea72d9793f11` | `95266b3dc670d5d9…` |
| 56 | `tests/report_retrieval.py` | 757 | `e98054edbe2774dd76ac3866f4d790ee95ca826d` | `2627d3aa7679b3c4…` |
| 57 | `tests/report_weight_robustness.py` | 534 | `d5d051655f1c7a580192ec2dad75aaeced8a61d9` | `2bc93c39976ea1a7…` |
| 58 | `tests/test_holdout_v2.py` | 638 | `ec8fea1f586a4797a6f35502320bfc9880966421` | `7daa6188881fb893…` |
| 59 | `tests/test_lexicon_overfit.py` | 383 | `22988e6d2faa72bcc1c7726df7b322770396c459` | `16e775600af092c0…` |
| 60 | `tests/test_lexicon_polarity.py` | 148 | `da2a69902d4950edf714af05ae4cef4ea17ba3d8` | `c67cbf86fe512f84…` |
| 61 | `tests/test_memory_hardening.py` | 520 | `b8dddbd8641c0df9b9f872c3188fa44144c8c0a4` | `aab414c6fb665fcb…` |
| 62 | `tests/test_memory_retrieval.py` | 365 | `0c982e6afa8984d90e940fd05100766cbc098f8c` | `df5b47d1af97cdd7…` |
| 63 | `tests/test_ranker_layers.py` | 352 | `7b6f9969916f436b929890e5e26e961845899646` | `61a6cdbf60b21120…` |
| 64 | `tests/test_ranker_mutations.py` | 323 | `3aa7a7d4bb4816bcbb75fd296faf263edd68e792` | `c1d21ecaa950a42d…` |
| 65 | `tests/test_retrieval_structure.py` | 650 | `ca1b39cbc2d8fb282c11b602731878353e7a451c` | `3b44374283b1594f…` |
| 66 | `tests/test_weight_grid.py` | 145 | `5f0715ce5d1ddab1253fe5be2a4bf7e1aad7d9f3` | `f9f62e33d7a5922e…` |
| 67 | `tests/test_weight_sweep.py` | 228 | `ddbae9c064dce296553f7da4d841e25b96dde3fe` | `60192979ac9e0775…` |
| 68 | `tests/test_workbench.py` | 54 | `3c7dc9fd8ec675370a4336d50052ab3759c5bacd` | `f435cdaf1e3e8ace…` |
| 69 | `tests/weight_grid.py` | 96 | `2761fd1de007fcaaac0e98a5c2c474a3456951fd` | `ca8f8821a67b8964…` |
| 70 | `vendor/agent_core/__init__.py` | 0 | `e69de29bb2d1d6434b8b29ae775ad8c2e48c5391` | `e3b0c44298fc1c14…` |
| 71 | `vendor/agent_core/data/luotianyi_original_songs.json` | 262 | `426d0fe96116838e202948ce88925d4ca96e27a7` | `22552757d32c86e1…` |
| 72 | `vendor/agent_core/harness.py` | 257 | `29dca70bcc740976910cd0f85d38f2ce9034795c` | `cb1ae928f8067495…` |
| 73 | `vendor/agent_core/song_catalog.py` | 138 | `f5b16e8a436b4f9111b6d388fe9c904374b9a8b0` | `57d257d1084a6727…` |
| 74 | `vendor/agent_core/voice_text.py` | 29 | `f7fe9267465a4c044e1e1df632cfec1dcca1a593` | `c652a1b868029a5f…` |
| — | **合计（74 个，不含本文件）** | **13345** | — | — |

合计值不是逐项手加：`wc -l` 多文件模式自己的 `total` 行给出 **13345**，与上表合计逐字相符 = True。


sha256 只列前 16 位做对照用；完整 sha256 与 blob 哈希在 7a 的第 5 节里对任务 B 的
11 个交付物给全了。本表的权威列是 **blob**，因为它对 author 改写免疫。

### 7.1 与 `.gitignore` 的关系

| `.gitignore` 规则 | 当前命中文件数 | 是否被强制 add |
|---|---|---|
| `evidence/run_*.json` | 66 | **否** |
| `__pycache__/` + `*.pyc` | 436 | **否** |
| `.venv*/` | 894 | **否** |
| **合计被忽略** | **993** | **否** |

被 `.gitignore` 忽略的文件共 **993** 个，其中 `evidence/run_*.json` **66** 个，**一个都没有被强制 add**。

复核者用 tree 哈希可以一次性验证本表全部 blob：

```
$ git ls-tree -r <最终 tree 哈希> | awk '{print $3, $4}'
```

该命令输出的每一行 blob 哈希都与上表逐字相同——这就是把最终 tree 哈希当主锚点的用法。

### 7.2 上表有两行是定点补正的，不是整份重新生成的（如实记录）

上表第 23 行（`evidence/task_b_final_selfcheck.md`）与第 39 行
（`evidence/task_b_scan_report.log`）在本文件第一次生成之后又变过，所以重新取了一次值：

| 行 | 行数 | 为什么变 |
|---|---|---|
| 第 23 行 | 660 → **690** | 那份文件里写死的扫描数字过期了（P18 总数、目标文件数、轮次表、`run_*.json` 计数），按 H8 的纪律改成了带时点、可归因的写法 |
| 第 39 行 | 146 → **148** | 目标集从 23 个变 24 个（多了本文件），扫描重跑到新的不动点，逐文件计数表多了一行、判读段多了一行 |

合计随之从 13313 变 **13345**（+30 +2），并且仍然与 `wc -l` 多文件模式自己的
`total` 行双向相符。**补正由仓库外的脚本做，数值全部来自命令**
（`wc -l` / `git hash-object` / sha256），一个哈希都没有手抄——把 40 位摘要手打进
一份以「权威摘要清单」为职责的文档，正是本轮要消的那一类缺陷。

**为什么不重跑生成器。** 生成器会重跑 8 闸门、单测与 `run_all.py` 两次，
而每次 `run_all.py` 都新建一个 `evidence/run_*.json`。那会把计数从 66 推到 68，
而 `task_b_final_selfcheck.md` 第 8 节已经定稿、已经扫到不动点、里面写着 66
并逐个点名了差值的来源。改动那个计数就会让一份已冻结的文档失效，
于是又要改、又要重扫、又要重生——那就是本步要终止的那个循环。
所以只刷真正过期的两行。

**补正之后本文件的行数未变**（507 → 507，本节写入前），因为两行都是原地替换。
上表不包含本文件自己，所以本节的存在不会让任何一行自相矛盾。

**残留的一个覆盖缺口，说清楚。** 入库的那份扫描记录冻结在补正**之前**，
所以它看到的本文件是补正前的形态。补正后又跑了一次扫描做验证，
结果记在**交付报告**里（仓库外），而没有覆写仓库内那份。
理由：重跑只会改扫描记录自己的时间戳行，从而让它在上表里的那一行过期；
而补正只改了哈希的**值**与行数的**数字**，没改哈希的**个数**，
所以扫描记录里本文件那一行的计数在补正前后完全相同。换句话说：
冻结的那份记录对补正后的本文件仍然逐格有效，差的只是本节这段新散文；
而这段新散文已由补正后的那次验证扫描覆盖（泄漏类为 0）。
验证扫描跑完后把仓库内那份按字节还原成冻结版，还原后的 blob 与上表第 39 行相符。

本节不写任何哈希字面量，就是为了不扰动上面那两个计数。

## 8. commit message 的敏感内容扫描

第 6 节的手工扫描覆盖的是 `evidence/` 下的文件内容。commit message 是另一条通道，
单独扫一遍。范围是 `origin/main..HEAD` 全部 commit 的完整 message（`%B`）。

探针同样只用 ID 指代，不印字面样式串（理由见 `evidence/task_b_scan_report.log` 表头）。

| ID | 语义 | 命中 |
|---|---|---|
| C01 | GitHub PAT 前缀样式（两种） | 0 |
| C02 | GitLab PAT 前缀样式 | 0 |
| C03 | 常见厂商 API key 前缀样式 | 0 |
| C04 | AWS access key id 样式 | 0 |
| C05 | PEM 私钥块头 | 0 |
| C06 | HTTP 授权头关键字 | 0 |
| C07 | 赋值形式的凭据关键字 | 0 |
| C08 | 连接串里内嵌用户名与密码的形态 | 0 |
| C09 | 用户家目录前缀 | 0 |
| C10 | Linux 家目录前缀 | 0 |
| C11 | 每用户临时目录前缀 | 0 |
| C12 | 系统临时目录前缀 | 0 |
| C13 | Windows 盘符（两种写法） | 1 |
| C14 | 上游 author 的个人邮箱 | 0 |

### 8.1 命中处的逐条定位

- **C13**（Windows 盘符（两种写法））→ 序数 **32** 的 commit `ce8fb2a`，message 第 44 行
  - 原文（形态已记号化）：`AssertionError: Lists differ: ['<路径形态> @ line 82', '<路径形态>\ @ line 82'] != []`

上面回显的原文里，命中探针的那几个形态已用记号替换。理由与扫描记录第 4 节把 hash
令牌记号化是同一条：本文件自己也是证据扫描的目标，而扫描的路径类探针会在盘符形态上
点火。把命中形态原样抄进本文件，就等于让本文件命中自己的探针。要看原文，跑
`git log -1 <那个 commit>` 即可——**序数与 subject 是稳定锚点，短 hash 不是**。

### 8.2 人工判读

这一节是手工写的，不由生成器产出。读完 8.1 的命中原文之后的结论如下。

**结论：14 个探针里 13 个为 0，唯一一处命中不是泄漏，不需要处置。**

逐条理由：

1. **它不在本轮的四个 commit 里。** 命中在序数 **32** 的 commit（`ce8fb2a`），
   subject 是「消毒 v2 语料的隐私自述注释」。本轮新增的是序数 40–43 四条，
   这四条在全部 14 个探针上都是 **0**。
2. **命中的是测试自己的词汇，不是一条真实路径。** 那一行是某条消毒测试的
   `AssertionError` 原文，而那条测试的职责就是在 v2 语料里搜绝对路径形态。
   它的失败消息刻意只报「模式 + 行号」而不 dump 语料正文（message 自己就解释了原因：
   用 `assertNotIn` 会把整份语料倒到终端，红因反而看不见）。所以被引号的
   就是**探针本身的字面样式**，而不是任何机器上的任何路径。
3. **决定性的区分证据是 C09 = 0。** C09 扫的是含本地登录名的完整家目录前缀。
   一条真实泄漏的机器路径必然命中 C09；而这里 C09 为 0，C13 为 1。
   也就是说命中的只是一个**裸盘符形态**与一个**不含登录名、不含任何目录的
   用户根前缀**，两者都不指向任何一台具体机器。
4. **这与 F21 是同一类自指，而且无法也不应消除。** 一个会报告「我匹配到了哪个模式」
   的消毒测试，必然在失败消息里点名那个模式；而任何引用该失败输出的 commit message
   必然带着它。这不是缺陷，是自描述式检查的固有属性。本轮对证据文件采取的同一条纪律
   （探针只用 ID + 语义指代）无法回溯应用到已有的 commit message 上。
5. **取证者无权也没必要改它。** 修改序数 32 的 message 需要改写历史，本轮明令禁止
   （禁 rebase、禁改 author、禁 force）。而且它不构成泄漏，所以也不需要处置。

**关于那枚已被要求吊销的 GitHub PAT：** C01（两种前缀样式）与 C02 在全部 43 条
commit message 上都是 **0**。这就验证了序数 43 那条 commit message 里写的那句话：
它以**任何形式**都没有出现在任何一条 commit message 里。当时那句话是先写下的承诺，
本节是事后的实测验证，两者现在对上了。

**两条通道的关系：** 第 6 节的文件扫描与第 8 节的 message 扫描是两条独立通道，
合起来才覆盖提交内容。只看前者会漏掉 message，只看后者会漏掉文件。
两者现在都是绿的，且两者的探针都只用 ID 指代、不印字面样式串。

判读不由生成器预先下结论：生成器只出计数与原文位置，读过原文之后的结论由取证者
手工写进上面这一节。这也是本轮反复踩到的那条自指教训的另一面——
**能由命令产生的东西交给命令，需要人来负责的东西不要塞进生成器。**

## 9. 判定

| # | 检查项 | 结果 |
|---|---|---|
| 1 | tracked 工作区为空 | **True** |
| 2 | 剩余 untracked 只有本文件自己与并行修改中的那一份（2 个） | **True** |
| 3 | 冻结区 5 件全部无改动且 sha256 与 MANIFEST 相符 | **True** |
| 4 | 本地 43 条 commit 对冻结区/MANIFEST 零触碰 | **True** |
| 5 | 四个新 commit 只碰 evidence/ 下的文件 | **True** |
| 6 | 8 闸门与期望矩阵 0/0/0/0/0/2/2/0 一致 | **True** |
| 7 | 8 闸门与 7a 逐格一致 | **True** |
| 8 | 8 闸门 FAIL 数为 0 | **True** |
| 9 | 单测 254 全绿、退出码 0 | **True** |
| 10 | 普通模式 verdict = PENDING-OK、退出码 0 | **True** |
| 11 | strict 模式 verdict = BLOCKED、退出码 1 | **True** |
| 12 | 两次 run_all 各新建 1 个 JSON，无同秒覆盖 | **True** |
| 13 | behind = 0，快进关系成立，push 不需要 force | **True** |
| 14 | commit message 里没有任何 PAT / 私钥 / 授权头样式 | **True** |

=> 14/14 项通过

**不 push。** 本轮没有执行任何 push、force、rebase、author 改写、git config 修改、
远端 URL 修改或凭据写入。author 改写由后续专人按备份 tag + tree 逐字节比对的规程执行。
