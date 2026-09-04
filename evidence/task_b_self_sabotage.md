# 任务 B（记忆系统）反 Goodhart 自证

本文件按 rebase 集成上游修复**之后**的最终状态整体重写，不是对上一版的补丁。
上一版（160 行，commit `9eade73` 时期）里有两条**自身错误**（H7 时间戳跨日矛盾、
H8 行数失真）与三条**已过期结论**（同一路变异下 golden 读作 0.875、
`HOLDOUT_GOLDEN` 无哈希保护、v1 第 6 对是 0 分差命中），本轮逐条改写，
修正前后对照见第 9 节。历史观测如实保留，没有抹掉。

所有数字均由命令输出产生，无一处手抄：时间戳来自 `date '+%Y-%m-%d %H:%M:%S %z'`，
行数来自 `wc -l`，指标来自打分器实测，退出码来自 `===EXIT=$?===` 标记，
哈希来自 `git hash-object` / `sha256`。

## 0. 定位锚点

> **本文件里的 commit hash 是 author 改写前的值。** push 前全部本地 commit 的
> author 会被改写，改写后所有 commit hash 全部失效。长期有效的稳定锚点是
> **tree 哈希、blob 哈希，以及 commit 的 subject + 序数**。author 改写不动 tree
> 也不动 blob，下面这两类哈希在改写前后逐字不变。

| 锚点 | 值 | 取得方式 |
|---|---|---|
| commit（全程未变） | `d6868c654a821abf7920d249683837db6068a87a`（短 `d6868c6`） | `git rev-parse HEAD` |
| **HEAD tree（稳定）** | `37d26de723f1571ec3c6aa0cced25f2794eece68` | `git rev-parse HEAD^{tree}` |
| `src/memory_ranker.py` **blob** | `2a125cae23544790a7e7f188b11f32c5e4070b55` | `git hash-object` |
| `src/memory_ranker.py` sha256 | `e204b36022b071df32a4dd52bd65f0e869c3a27d6878e5c0e0ea4c84fb5406f0` | `sha256` |
| `src/memory_lexicon.py` **blob** | `bfba659bc411a981b7d9df8913a70793d6d63c6e` | `git hash-object` |
| `src/memory_lexicon.py` sha256 | `777c3a5835633589dd3ba40d37a5ddaa74401c818e0b5cb791ba0f1b3df4e27f` | `sha256` |
| `src/memory_store.py` **blob** | `49d273aa9286afdf4d6f649b915c56042c9354e1` | `git hash-object` |
| `tests/test_ranker_mutations.py` **blob** | `3aa7a7d4bb4816bcbb75fd296faf263edd68e792` | `git hash-object` |
| `tests/test_memory_retrieval.py` **blob** | `0c982e6afa8984d90e940fd05100766cbc098f8c` | `git hash-object` |
| `tests/test_holdout_v2.py` **blob** | `ec8fea1f586a4797a6f35502320bfc9880966421` | `git hash-object` |
| `tests/holdout_v2.py` **blob** | `fcf727ff1a27cc5658c8023bbbb0ea72d9793f11` | `git hash-object` |
| `acceptance/gates/g1_memory.py` **blob** | `7bca7b83221865fd23c36243229653c91a8c81b9` | `git hash-object` |

执行时刻（由 `date` 生成，逐字取自日志）：变异测试清单 **2026-09-04 16:45:22 +0100**，
九路独立复跑与闸门实测 **16:47:22 +0100**，可逆性收尾复核 **16:47:22 +0100**。
全部落在 2026-09-04 同一天，**没有跨日**。

原始日志：`evidence/task_b_self_sabotage.log`，**362 行**（`wc -l`）。
该文件内机器绝对路径命中数 **0**；消毒规则：仓库根记作 `<repo>`，仓库外临时目录
记作 `<scratch>`，实质数值逐字未改。

> **关于旧日志的去向（不留悬空引用）**：上一版 `task_b_self_sabotage.log` 是 634 行、
> 记录三路**真改文件**的破坏（含破坏态 sha256、`git diff` 原文、54 个单测的失败明细），
> 本轮按「重写而不是打补丁」的要求整份覆盖，它已不在盘上，而且是 untracked、
> 从未进过 commit，所以也不在 git 历史里。本文件里凡是引「旧日志第 N 行」的地方
> （第 9.2、9.4 节），引文都是在覆盖**之前**用 `grep -n` 抓下来的原文，
> 当时同时记下了行号；读者无法再 `sed` 到那些行，这一点如实说明，不假装可验。

临时脚本一律放在仓库外的 `<scratch>` 下（`mutate_eval.py`、`step4_driver.py`），
仓库内**一个文件都没有被修改过**——本轮所有变异都在进程内用 `mock.patch.object`
施加，不写盘。这一点由第 8 节的 blob 哈希前后比对实测证明，不是靠声明。

## 1. 为什么要做这件事

`score_retrieval()` 是「自己实现检索、又自己给自己打分」的自评结构：打分器
`src/memory_ranker.py` 与被评的检索实现是同一套代码，评测口径（top-1 + 宏平均）也由
它自己定义。这种结构下闸门报 1.0 有两种可能——实现真的好，或者打分器根本不会给低分。
区分这两者只能靠自破坏：把实现弄坏，看分数是否真的掉。

本轮的三个集：

| 集 | 对数 | 来源 | 谁在看它 |
|---|---|---|---|
| `golden` | 8 | `acceptance/gates/g1_memory.py` 的 `GOLDEN` | **闸门 `g1_memory`（唯一进闸门判定路径的集）** |
| `v1` | 12 | `tests/test_memory_retrieval.py` 的 `HOLDOUT_GOLDEN` | 只有 `tests/`（哈希锁 `561f17ba423dfa024ba9a940632e5d6a8399ea5638ec5b56119e72c6c9b72619`） |
| `v2` | 32 | `tests/holdout_v2.py` 的 `HOLDOUT_V2` | 只有 `tests/`（文件字节锁 + 语料哈希锁） |

判定线 0.8 取自 `g1_memory.py` 第 55 行：
`if result.get("precision", 0) < 0.8 or result.get("recall", 0) < 0.8`。

**这张表就是本轮全部结论的骨架**：闸门只看 golden 8 对，v1 与 v2 一共 44 对
完全不在闸门视野里，而 `run_all.py` 又不跑 unittest。第 7 节把这件事直接测出来了。

## 2. 已固化的变异演练（仓库内资产）

变异演练上一轮是仓库外临时脚本，本轮已固化为 **`tests/test_ranker_mutations.py`
（323 行，blob `3aa7a7d4bb4816bcbb75fd296faf263edd68e792`）**。清单由
`./.venv/bin/python -m unittest tests.test_ranker_mutations -v` 生成，
**10 个用例全绿，`Ran 10 tests in 0.050s` / `OK` / 退出码 0**（2026-09-04 16:45:22）：

| # | 测试名 | 类 | 结果 |
|---|---|---|---|
| 1 | `test_emptying_every_lexicon_member_drops_holdout_below_threshold` | `MetricTeethTests` | ok |
| 2 | `test_emptying_the_whole_lexicon_drops_golden_below_threshold` | `MetricTeethTests` | ok |
| 3 | `test_killing_l3_drops_holdout_below_threshold` | `MetricTeethTests` | ok |
| 4 | `test_unsorted_rank_drops_golden_below_threshold` | `MetricTeethTests` | ok |
| 5 | `test_variant_a_dropping_color_singles_keeps_all_three_sets_and_v2_29` | `N1SingleCharMemberTests` | ok |
| 6 | `test_variant_b_dropping_all_28_singles_loses_v1_2_3_and_v2_24` | `N1SingleCharMemberTests` | ok |
| 7 | `test_killing_l4_keeps_metrics_but_collapses_the_safety_margin` | `NoMetricTeethTests` | ok |
| 8 | `test_killing_l5_leaves_metrics_untouched_and_silences_the_layer` | `NoMetricTeethTests` | ok |
| 9 | `test_reverting_to_naive_substring_counting_resurfaces_m4` | `NoMetricTeethTests` | ok |
| 10 | `test_splitting_the_polarity_scan_resurfaces_m2` | `NoMetricTeethTests` | ok |

**回滚机制（源码逐行核对，不是声明）**：每个变异都在 `with mock.patch.object(mr, ...)`
块内施加（第 139、149、160、169、190、204、228、244、262、290、307 行），块退出即还原；
`MutationDrill.setUp`（第 108 行）先快照模块状态，再
`self.addCleanup(self._assert_module_restored)`（第 117 行），后者（第 119–126 行）用
`assertIs` 逐个断言 `CONCEPT_LEXICON` / `rank` / `_concept_hits` / `_concept_hit_parts` /
`_polarity_hits` 都回到了**同一个对象**——不是「值相等」，是「同一身份」，所以任何一路
变异泄漏到下一个用例都会立刻红。词典类变异用 `dataclasses.replace` 整体 rebind
（第 98 行），因为 `CONCEPT_LEXICON` 是 `MappingProxyType` 只读视图，不能原地
`__setitem__`。

## 3. 九路独立复跑的实测分数

**不只信测试绿。** 下表每一格都由 `<scratch>/mutate_eval.py` 在进程内施加变异后
实测打印，三集评测口径在该脚本里**独立重写**了一遍，官方 `score_holdout_v2` 只用作
交叉校验，偏差 >1e-12 直接判 `ROUTE INVALID`。**九路全部 `AGREE (<1e-12)`。**

`acc` = top-1 命中对数 ÷ 总对数；`macroP`/`macroR` 按声明口径宏平均
（空 stored 跳过、空 relevant 时 precision 取「返回非空即 0.0 否则 1.0」、recall 跳过），
`n(P)`/`n(R)` 是实际计入宏平均的对数。`<0.8?` 问的是 acc 是否跌破 0.8。
`min_margin` 是命中对里最小的 top1−top2 分差（安全余量）。

| 路 | 变异 | golden acc / P / R | v1 acc / P / R | v2 acc / P / R | v2 hits | 交叉校验 |
|---|---|---|---|---|---|---|
| baseline | 无 | 8/8 **1.0000** / 1.0000 / 1.0000 | 12/12 **1.0000** / 1.0000 / 1.0000 | **0.7500** / 0.7742 / 0.7500 | 24/32 | AGREE |
| kill_l3 | `W_CONCEPT = 0` | 8/8 **1.0000** / 1.0000 / 1.0000 | 8/12 **0.6667** ↓ | **0.6562** / 0.6774 / 0.6500 | 21/32 | AGREE |
| kill_l4 | `W_PREFERENCE = 0` | 8/8 1.0000 | 12/12 1.0000 | **0.6875** / 0.7097 / 0.6833 | 22/32 | AGREE |
| kill_l5 | `W_TRANSIENT = 0` | 8/8 1.0000 | 12/12 1.0000 | 0.7500 / 0.7742 / 0.7500 | 24/32 | AGREE |
| unsorted_rank | `rank()` 不排序 | 5/8 **0.6250** ↓ | 12/12 **1.0000** | **0.3750** / 0.3871 / 0.3500 | 12/32 | AGREE |
| empty_all_members | 清空全部 member | 8/8 **1.0000** | 8/12 **0.6667** ↓ | **0.6562** / 0.6774 / 0.6500 | 21/32 | AGREE |
| empty_whole_lexicon | 清空整个词典 `{}` | 6/8 **0.7500** ↓ | 10/12 **0.8333** ↓ | **0.5938** / 0.6129 / 0.5833 | 19/32 | AGREE |
| n1_color_singles | 删颜色类 15 个单字 member | 8/8 1.0000 | 12/12 1.0000 | 0.7500 / 0.7742 / 0.7500 | 24/32 | AGREE |
| n1_all_singles | 删全词典 28 个单字 member | 8/8 **1.0000** | 10/12 **0.8333** ↓ | **0.7188** / 0.7419 / 0.7167 | 23/32 | AGREE |

未命中索引（`miss idx`，0 基）：

| 路 | golden | v1 | v2 |
|---|---|---|---|
| baseline | — | — | `[17, 19, 20, 21, 22, 25, 30, 31]` |
| kill_l3 | — | `[2, 3, 6, 8]` | `[15, 17, 18, 19, 20, 21, 22, 24, 25, 30, 31]` |
| kill_l4 | — | — | `[7, 17, 19, 20, 21, 22, 23, 25, 30, 31]` |
| kill_l5 | — | — | `[17, 19, 20, 21, 22, 25, 30, 31]`（与基线**逐个相同**） |
| unsorted_rank | `[1, 4, 7]` | — | `[0, 2, 3, 4, 5, 7, 8, 10, 11, 14, 15, 16, 17, 19, 20, 22, 24, 25, 30, 31]` |
| empty_all_members | — | `[2, 3, 6, 8]` | 同 kill_l3 |
| empty_whole_lexicon | `[6, 7]` | `[2, 3]` | `[1, 6, 15, 17, 18, 19, 20, 21, 22, 24, 25, 30, 31]` |
| n1_color_singles | — | — | 与基线**逐个相同** |
| n1_all_singles | — | `[2, 3]` | `[17, 19, 20, 21, 22, 24, 25, 30, 31]`（只比基线多丢 #24） |

安全余量 `min_margin`（命中对里最小的 top1−top2）：

| 路 | golden | v1 | v2 |
|---|---|---|---|
| baseline | 0.2676 @#7 | **0.0500 @#5** | 0.0067 @#5 |
| kill_l3 | 0.0113 @#1 | 0.0249 @#11 | 0.0067 @#5 |
| kill_l4 | 0.2176 @#7 | **0.0000 @#5** | 0.0067 @#5 |
| kill_l5 | 0.0926 @#7 | 0.0500 @#5 | 0.0023 @#0 |
| unsorted_rank | 0.4455 @#6 | 0.0500 @#5 | −0.0160 @#21（**此路该列无意义**，见下） |
| empty_all_members | 0.0113 @#1 | 0.0249 @#11 | 0.0067 @#5 |
| empty_whole_lexicon | 0.0613 @#1 | 0.0030 @#6 | 0.0000 @#0 |
| n1_color_singles | 0.2676 @#7 | 0.0500 @#5 | 0.0067 @#5 |
| n1_all_singles | 0.0671 @#4 | 0.0500 @#5 | 0.0067 @#5 |

`unsorted_rank` 的 min_margin 出现负值（v2 −0.0160）：不排序时 top1 未必是最高分，
「top1 − top2」这个量本身失去定义，该列对这一路没有解释力。日志的 TOOLING NOTE
里也记了这条读法提醒。

## 4. 有牙齿 / 无牙齿的分类（本轮实测，不是沿用旧结论）

**有牙齿（指标真的掉，且掉到能被判据看见）**：

| 路 | 掉在哪 | 谁会红 |
|---|---|---|
| `unsorted_rank` | golden 8→5（0.625）、v2 24→12 | **闸门 `g1_memory` 会红**（golden 0.625 < 0.8）+ 单测 |
| `empty_whole_lexicon` | golden 8→6（0.75）、v1 12→10、v2 24→19 | **闸门 `g1_memory` 会红**（golden 0.75 < 0.8）+ 单测 |
| `kill_l3` | v1 12→8（0.6667）、v2 24→21 | **只有单测会红**，闸门不动（见第 7 节） |
| `empty_all_members` | v1 12→8（0.6667）、v2 24→21 | **只有单测会红**，闸门不动 |
| `n1_all_singles` | v1 12→10、v2 24→23 | **只有单测会红**（v1 0.8333 仍 ≥0.8，但满分棘轮 1.0 会红） |
| `kill_l4` | v2 24→22 | **只有单测会红**（v2 棘轮 P 0.7097 < 0.77） |

**无牙齿（三集指标一个不动）**：

| 路 | 实测 | 说明 |
|---|---|---|
| `kill_l5` | golden / v1 / v2 三集 acc、P、R **逐位与基线相同**，v2 未命中索引也逐个相同 | L5 是「分差放大器」不是「决策改变者」，见第 5 节 |
| `n1_color_singles` | 三集**逐位与基线相同**，连 min_margin 都一样（golden 0.2676 @#7、v1 0.0500 @#5、v2 0.0067 @#5） | 删掉颜色类 15 个单字 member 对三集**完全不可观测**，见第 6 节 |

按派单口径「让 golden 或留出集分数掉到 0.8 以下」：`kill_l5` 与 `n1_color_singles`
两路**未达标**。按纪律**如实记为无牙齿，未加大破坏力度、未改判定口径**——
加大破坏（比如同时摘 L4）会破坏单变量归因，也违背「不许为了让结果好看而加大破坏力度」。

## 5. `kill_l5` 为什么无牙齿（如实记录，不加大破坏力度）

`W_TRANSIENT = 0.0` 之后 `transient_penalty()` 本身仍照常返回，只是合成时乘 0，
等价于整层失效。实测三集指标与基线**逐位相同**：golden 8/8 1.0000、v1 12/12 1.0000、
v2 24/32 P=0.7742 R=0.7500，v2 的 8 个未命中索引 `[17,19,20,21,22,25,30,31]` 也一个不差。

唯一动的是安全余量：

| 集 | 基线 min_margin | `kill_l5` min_margin | 变化 |
|---|---|---|---|
| golden | 0.2676 @#7 | 0.0926 @#7 | −0.1750 |
| v1 | 0.0500 @#5 | 0.0500 @#5 | 0 |
| v2 | 0.0067 @#5 | 0.0023 @#0 | −0.0044 |

golden #7 的余量掉 0.1750，正好等于 `W_TRANSIENT 0.35 × transient_penalty 0.5`——
L5 的全部贡献就是把一个**本来已经赢的**分差再拉大 0.175，从来没有翻转任何一对。

结论：**L5 在当前三个集上对 top-1 指标的贡献恒为 0。** 它的价值只体现在
（a）单测层面的分数单调性断言（`test_killing_l5_leaves_metrics_untouched_and_silences_the_layer`
把这个「不动」本身钉成了断言，摘掉 L5 不会让任何指标红，但会让这条断言的语义失效）、
（b）「带时态标记的短期状态不该排在稳定属性前面」这个设计意图本身。

一个诚实的推论：**如果有人把 L5 整层删掉，8 个验收闸门的状态一个都不会变**
（`g1_memory` 仍 PASS），三个集的指标一个都不会动，只有单测会红。而 `run_all.py`
不跑单测。这条与上一版第 112 行的推论一致，本轮在最终树上重新实测确认。

## 6. `n1_color_singles`：一个三集完全观测不到的变异

删掉颜色类的 15 个单字 member（全词典 28 个单字里颜色类占 15 个：生日 4、宠物 4、
过敏 3、称呼 2）。实测三集**逐位与基线相同**——不只是 acc/P/R 相同，连三个集的
min_margin 与 v2 的未命中索引都相同。

原因：`_masked_scan` 是**最长优先贪心**，查询里出现「藏青」时它取「藏青」这个双字
member，不会退化去取单字「青」。删掉单字后，双字 member 仍在，扫描结果不变。
所以这一路变异在三集上**零可观测性**。

它的意义是反向的：变异体 B（删全 28 个单字）会让 v1 掉 2 对（#2、#3）、v2 掉 1 对
（#24），说明单字 member 确实在少数几对上起作用；而这少数几对**不涉及颜色类**。
换句话说，颜色类的 15 个单字 member 在当前三集上是**纯冗余**——删掉没有任何指标
能发现。这不构成缺陷（词表按语义完备性组织，不按「每个词都要被评测集用到」组织），
但它精确划出了评测集的覆盖边界：**三集无法为颜色类单字 member 的存在提供任何证据**。
`test_variant_a_dropping_color_singles_keeps_all_three_sets_and_v2_29` 把这件事钉成了
断言，所以将来若有人扩了评测集让这一路变得可观测，那条测试会红，提醒同步更新结论。

## 7. Goodhart 敞口的直接实测：**闸门会不会放过一个过拟合实现**

这是本轮最关键的一节。上一版靠推理得出「留出集不在闸门视野里」，本轮**把真的
闸门函数在变异下跑了一遍**。

`g1_memory.run()` 在进程内、在 `mock.patch.object` 生效期间被直接调用，
读的是它自己的 `problems` / `pending` 与由此推出的退出码（`1 if problems else
(2 if pending else 0)`，与 `g1_memory.py` 第 63–70 行的分支一一对应）。
它内部会 `MemoryStore()`，而 `MemoryStore.__init__`（`src/memory_store.py` 第 56–64 行）
在无参时走 `tempfile.NamedTemporaryFile`，数据库落在系统临时目录，**不写仓库**。

| 路 | golden P/R | v1 P/R | v2 P/R (hits) | **`g1_memory` 实测退出码** | v1≥0.8 单测 | v1==1.0 棘轮 | v2 棘轮 |
|---|---|---|---|---|---|---|---|
| baseline | 1.0000 / 1.0000 | 1.0000 / 1.0000 | 0.7742 / 0.7500 (24/32) | **0 = PASS**，`problems=[]` `pending=[]` | PASS | PASS | PASS |
| **empty_all_members** | **1.0000 / 1.0000** | **0.6667 / 0.6667** | 0.6774 / 0.6500 (21/32) | **0 = PASS**，`problems=[]` `pending=[]` | **FAIL** | **FAIL** | **FAIL** |
| **kill_l3** | **1.0000 / 1.0000** | **0.6667 / 0.6667** | 0.6774 / 0.6500 (21/32) | **0 = PASS**，`problems=[]` `pending=[]` | **FAIL** | **FAIL** | **FAIL** |
| empty_whole_lexicon | 0.7500 / 0.7500 | 0.8333 / 0.8333 | 0.6129 / 0.5833 (19/32) | **1 = FAIL**，`problems=["retrieval quality below 0.8: {'precision': 0.75, 'recall': 0.75}"]` | PASS | FAIL | FAIL |

判据来源（`g1_memory.py` 逐行照录）：

```
 51:     result = score_retrieval(GOLDEN)
 52:     if result is None:
 53:         pending.append("retrieval quality: score_retrieval() not implemented (Task B)")
 55:         if result.get("precision", 0) < 0.8 or result.get("recall", 0) < 0.8:
 56:             problems.append(f"retrieval quality below 0.8: {result}")
```

### 7.1 对派单那个问题的明确回答

> **一个 golden 满分但 v2 只有 0.667 的过拟合实现，能否通过全部 8 个验收闸门？**

**能。实测确认，不是推论。**

`empty_all_members` 与 `kill_l3` 两路都是这个形状：golden P=R=**1.0000**（满分），
v1 掉到 **0.6667**，v2 掉到 **0.6500 / hits 21/32**（比派单说的 0.667 还低一点，
因为派单引的是 v1 的数；两个集都远低于 0.8）。这两路下 `g1_memory.run()` 实测
`problems=[]`、`pending=[]`、**退出码 0 = PASS**。其余 7 个闸门与检索质量无关
（`g0_environment`/`g0_secrets`/`g0_freeze`/`g1_contract`/`g1_permissions`/`g1_tools`/
`g3_simulate`），第 2 步的 48 格与第 3 步的 drill 前后快照都实测它们不受
`src/memory_ranker.py` 的打分行为影响。所以 **8 个闸门全绿**。

原因是结构性的，两条：

1. **闸门只看 golden 8 对。** `g1_memory.py` 只 import `GOLDEN`，从不看
   `HOLDOUT_GOLDEN`（12 对）与 `HOLDOUT_V2`（32 对）。44 对反过拟合语料
   完全不在 DoD 的闸门判定路径上。
2. **`run_all.py` 不跑 unittest。** 它的 `GATES` 列表只有 8 个闸门。反过拟合的
   唯一防线（`test_holdout_set_reaches_threshold`、`ThreeCorpusRatchetTests`、
   v2 三条棘轮）活在 `tests/` 里，而 `tests/` 不在编排器里。

对照：**同一批变异在 254 个单测下会红**——`empty_all_members` / `kill_l3` 让
`test_holdout_set_reaches_threshold`（v1 ≥ 0.8）、`test_v1_holdout_is_still_perfect`
（v1 == 1.0）、v2 三条棘轮全部 FAIL。所以防线是存在的，只是**不在闸门那一侧**。

一句话结论：**「8 个闸门全绿」与「检索实现没有过拟合」是两件独立的事，前者不蕴含
后者。** 谁只看 `run_all.py` 的 verdict 就放行，就会放过 `kill_l3` 这种
「整层删掉、闸门不动」的实现。

### 7.2 一个反方向的对照：闸门确实有牙齿，只是牙齿只覆盖 8 对

`empty_whole_lexicon` 这一路 golden 掉到 0.7500，`g1_memory` 实测
**退出码 1 = FAIL**，`problems` 里带的是真实数值
`retrieval quality below 0.8: {'precision': 0.75, 'recall': 0.75}`，不是空泛的
「质量不足」。加上 `unsorted_rank` 让 golden 掉到 0.6250（同样 < 0.8，必然 FAIL），
说明**只要退化落在 golden 那 8 对上，闸门就会咬**。

所以准确的表述不是「闸门没有牙齿」，而是：**闸门的牙齿只覆盖 8 对样本，
且这 8 对的阈值 0.8 意味着错 1 对（0.875）仍然 PASS，判别余量恰好 1 个样本。**
`empty_all_members` 之所以能溜过去，是因为它恰好一条 golden 都没丢。

## 8. 可逆性：整份日志跑完之后仓库有没有动过一个字节

**两层实测。** 第一层在每条 route 内部（第 3 节表格里每一路末尾都打印了
`module state restored after patch exit : True` 与 `blob hashes unchanged : True`，
九路全为 True）；第二层在整份日志的尺度上，A 节之前与 E 节之后各取一次哈希：

| 被观察路径 | blob before | blob after | same |
|---|---|---|---|
| `src/memory_ranker.py` | `2a125cae23544790a7e7f188b11f32c5e4070b55` | 同左 | True |
| `src/memory_lexicon.py` | `bfba659bc411a981b7d9df8913a70793d6d63c6e` | 同左 | True |
| `src/memory_store.py` | `49d273aa9286afdf4d6f649b915c56042c9354e1` | 同左 | True |
| `tests/test_ranker_mutations.py` | `3aa7a7d4bb4816bcbb75fd296faf263edd68e792` | 同左 | True |
| `tests/test_memory_retrieval.py` | `0c982e6afa8984d90e940fd05100766cbc098f8c` | 同左 | True |
| `tests/test_holdout_v2.py` | `ec8fea1f586a4797a6f35502320bfc9880966421` | 同左 | True |
| `tests/holdout_v2.py` | `fcf727ff1a27cc5658c8023bbbb0ea72d9793f11` | 同左 | True |
| `acceptance/gates/g1_memory.py` | `7bca7b83221865fd23c36243229653c91a8c81b9` | 同左 | True |

| git 状态 | before | after | same |
|---|---|---|---|
| `git status --porcelain -uno` | `''` | `''` | True |
| `git diff --stat` | `''` | `''` | True |
| `git rev-parse HEAD` | `d6868c654a821abf7920d249683837db6068a87a` | 同左 | True |
| `git rev-parse HEAD^{tree}` | `37d26de723f1571ec3c6aa0cced25f2794eece68` | 同左 | True |

**全部 blob 与 git 状态一字未动：True。**

与上一版的差别值得说清楚：上一版是**真的改了 `src/memory_ranker.py`**
（三路各一次 `git diff`，破坏后 sha256 分别是 `5b57a0dc…`、`d36e746a…`、`3e481889…`，
每路做完 `git checkout -- src/memory_ranker.py` 恢复）。本轮九路**一次都没有写盘**，
全部在进程内 rebind 模块属性。可逆性从「靠 `git checkout` 兜底」变成了
「根本不产生需要兜底的东西」——这是更强的保证，代价是破坏不再体现在 `git diff` 里，
所以本轮改用 blob 哈希前后比对 + 模块身份 `assertIs` 来证明复原，两者都是实测。

## 9. 与上一版的差异：H7 / H8 修正与结论改写

### 9.1 H7（时间戳跨日矛盾）——已修

| | 上一版 | 本轮 |
|---|---|---|
| `.md` 声称的执行时间 | 「本地 2026-09-02 17:46 – 17:49（UTC+1）」（第 3 行） | 2026-09-04 16:45:22 / 16:47:22 +0100（由 `date` 生成） |
| `.log` 里的实际时间戳 | `local=2026-09-03 07:49:24+0100`（基线）、`07:49:39`（第 1 路）、`07:50:13`（第 2 路）、`07:50:37`（第 3 路） | 16:45:22（A 节）、16:47:22（B/C/D 节）、16:47:22（E 节） |
| 是否自相矛盾 | **是**：`.md` 说 09-02 傍晚，`.log` 说 09-03 早晨，跨了一日 | **否**：`.md` 与 `.log` 全部指向 2026-09-04 同一天的两个时刻 |

成因：上一版的时间是**手抄**的，抄错了日期与时段。本轮所有时间戳一律由
`date '+%Y-%m-%d %H:%M:%S %z'` 在写日志的那一刻生成，`.md` 里的时刻逐字取自 `.log`，
不存在第二个来源。

### 9.2 H8（行数失真且与另一份文档互相矛盾）——已修

| | 上一版 | 本轮 |
|---|---|---|
| `task_b_self_sabotage.md` 声称 | 「632 行」（第 4 行） | 「362 行」 |
| `task_b_final_selfcheck.md` 声称 | 「634 行」（清单表内） | 见该文件本轮重写版 |
| `wc -l` 实测 | **634** | **362** |
| 矛盾 | **是**：632 vs 634，两份文档对同一个文件给了两个数 | 否：两处都由 `wc -l` 生成，指向同一次测量 |

成因同上：手抄。本轮所有行数一律由 `wc -l` 生成。旧日志确实曾是 634 行
（上一版 `.md` 写 632 是抄错，`final_selfcheck.md` 写 634 是对的），
本轮该文件已按最终状态整体重写为 362 行，旧的三路破坏记录（含破坏态 sha256、
`git diff` 原文、54 个单测的失败明细）随之被九路进程内变异的记录取代。

### 9.3 结论改写

| 旧结论 | 本轮判定 | 依据 |
|---|---|---|
| 「清空全部 member → golden **0.875**（7/8），停在 0.8 门槛线上，只差一个样本就翻红」（上一版第 30、58 行与 F3） | **已过期。** 最终树上同一路变异 golden = **1.0000（8/8）**，一条都没丢；翻红的是 v1（0.6667）与 v2（0.6500） | 第 3 节 `empty_all_members` 行 |
| 「golden 只有 8 条、阈值 0.8，判别余量恰好 1 个样本」（F3） | **结构仍然成立**，但「本次正好停在 0.875 这条线上」这个实例已不存在——本轮 golden 要么是 1.0000（6 路）要么是 0.7500/0.6250（2 路），没有落在 0.875 | 第 3 节 |
| 「`HOLDOUT_GOLDEN` 没有哈希保护，可以被无痕修改，改完 `g0_freeze` 不会响」（F6） | **部分已修。** v1 现在有哈希锁 `HOLDOUT_GOLDEN_SHA256 = 561f17ba…`（`test_memory_retrieval.py` 第 61 行）+ `test_holdout_data_is_hash_locked`（第 86 行）；v2 有语料哈希锁 + **文件字节锁**（`test_v2_data_is_hash_locked`、`test_v2_file_bytes_match_the_pinned_lock`）。**但仍未修的那一半是：这两个锁都是自测断言，不在 `acceptance/MANIFEST.json` 的 5 个冻结件里，`g0_freeze` 依然看不见它们** | 第 10 节 F6' |
| 「自破坏实验的可复现性依赖仓库外临时脚本，若主仓希望成为回归资产需要固化」（F7） | **已修。** 变异演练已固化为 `tests/test_ranker_mutations.py`（323 行、10 个用例、`mock.patch.object` + `addCleanup` 自动回滚），进了 254 个单测的一部分 | 第 2 节 |
| 「留出集有位置偏置：12 条的 relevant 全部位于 `stored` 第 1 位，`rank()` 退化成原序仍拿 12/12」（F2） | **仍然成立，本轮复现。** `unsorted_rank` 下 v1 = 12/12 = **1.0000** 一条没掉，而 golden 掉到 5/8、v2 掉到 12/32 | 第 3、10 节 |
| 「留出集 #6 是 0 分差命中，靠 `list.sort` 的稳定性取胜」（F4） | **基线上已不成立**：v1 的 min_margin 现在是 **0.0500 @#5**（0 基索引，即旧文档的 1 基 #6），不再为 0。那 0.05 恰好来自 L4——`kill_l4` 一路把它压回 **0.0000 @#5**，`test_killing_l4_keeps_metrics_but_collapses_the_safety_margin` 正是钉这件事。所以准确表述改成：**这一对的安全余量完全由 L4 单独提供，L4 归零即回到 0 分差** | 第 3 节 min_margin 表 |
| 「L5 对指标惰性」（F5） | **仍然成立**，本轮在最终树上重测，三集逐位不变 | 第 5 节 |
| 「留出集不在任何验收闸门里，反过拟合控制完全落在单元测试上，而单元测试不在编排器里」（F1） | **仍然成立，且本轮由实测升级为直接证据**：真的 `g1_memory.run()` 在 `empty_all_members` / `kill_l3` 下退出码 0 | 第 7 节 |

### 9.4 Sarah 早前那组数字的复核（派单点名要求）

派单给的三个读数：Sarah 在 Lee 阶段二进行中的树上测「清空词典 member」得
**golden 1.000 / 旧留出集 0.667**；更早的文档记载 **golden 0.875**。

本轮在**最终树**上重测同一路变异（`empty_all_members`），实测：

| 集 | 本轮实测 | Sarah（中间态树） | 更早文档（`9eade73` 树） |
|---|---|---|---|
| golden P/R | **1.0000 / 1.0000**（8/8） | 1.000 | **0.875000 / 0.875000**（7/8） |
| v1 P/R | **0.6667 / 0.6667**（8/12） | 0.667 | **0.666667 / 0.666667**（8/12） |
| v2 P/R (hits) | 0.6774 / 0.6500（21/32） | 未测 | 当时还没有 v2 |
| `g1_memory` 退出码 | **0 = PASS** | 未测 | **0（旧日志第 218 行 `===EXIT=0===`）** |

判定：**三个读数没有一个是错的，它们测的是三棵不同的树。**

- `0.875` 出自 commit `9eade73` 时期的实现（旧日志第 116 行原文
  `GOLDEN precision=0.875000 recall=0.875000 低于0.8=False`，第 128 行 `top1 命中 7/8`）。
- `1.000` 出自 Sarah 复核时的阶段二中间态树。
- 本轮最终树也是 `1.000`，与 Sarah 一致，**复现成功**。

变化发生在 golden #2「用户在哪座城市」这一对：旧实现里抽掉 member 层之后
「用户最喜欢的颜色是蓝色」会压过「用户在杭州工作」（旧文档第 48 行记的分差
+0.038730），阶段二/三的修复让这一对不再依赖 member 级桥接，于是同一路变异
在最终树上丢的是 v1 的 4 对（#2、#3、#6、#8）而不是 golden 的 1 对。
`v1 = 0.6667` 这个数在三棵树上**完全没变**，说明退化的总量是一样的，
只是从「闸门看得见的集」搬到了「闸门看不见的集」——**这本身就是 Goodhart
敞口的一次真实演示**：修复把退化从 golden 挪到 v1，闸门侧的读数因此变得更好看，
而实现的实际检索能力损失并没有变小。

## 10. 本次自证暴露的问题（只报告不处置）

**F1'　反过拟合约完全不在闸门判定路径上，而 `run_all.py` 不跑 unittest。**
`g1_memory.py` 只 import `GOLDEN`（8 对），从不看 `HOLDOUT_GOLDEN`（12 对）与
`HOLDOUT_V2`（32 对）；`run_all.py` 的 `GATES` 列表只有 8 个闸门。实测：
`empty_all_members` 与 `kill_l3` 两路下 v1 掉到 0.6667、v2 掉到 0.6500，
`g1_memory.run()` 仍然 `problems=[]` `pending=[]` **退出码 0**。
也就是说，**一个 golden 满分而两个留出集都远低于 0.8 的过拟合实现可以通过全部
8 个验收闸门**。同一批变异在 254 个单测下会红 4 条以上，所以防线存在，
只是不在闸门那一侧。处置建议（不在本轮范围）：把 v1/v2 的棘轮断言接进
`g1_memory` 的判据，或让 `run_all.py` 增加一个跑 unittest 的步骤。

**F2'　v1 留出集有位置偏置：12 条的 relevant 全部位于 `stored` 第 1 位。**
`unsorted_rank`（完全不排序）下 v1 仍拿 **12/12 = 1.0000**，而 golden 掉到 5/8、
v2 掉到 12/32。v1 因此对「排序能力」零判别力。golden 里 relevant 不在首位的
只有 3 条（0 基 #1/#4/#7），也正是这 3 条把这一路拦下来的；v2 的设计
（`test_first_occurrence_positions_are_spread` 明确断言首次出现位置被打散）
就是为了修这个偏置，实测有效——同一路变异 v2 从 24 掉到 12。

**F3'　golden 只有 8 对、阈值 0.8，判别余量恰好 1 个样本。**
错 1 对 = 0.875 仍 PASS，错 2 对 = 0.75 才 FAIL。本轮九路里 golden 只出现过
1.0000（6 路）、0.7500（1 路）、0.6250（1 路）三个值，0.875 这个「悄悄丢一对」
的区间没被踩到，但它在结构上依然存在，且 0.875 与 1.0000 在闸门输出里同样显示为
`G1_MEMORY: PASS`，看不出实现已经丢了一条。

**F4'　v1 第 6 对（0 基 #5）的安全余量完全由 L4 单独提供。**
基线 min_margin = **0.0500**，`kill_l4`（`W_PREFERENCE = 0`）把它压到 **0.0000**——
即命中不变、余量归零，靠 `list.sort` 的稳定性维持。上一版记的「0 分差命中」在基线上
已经不成立（那是 L4 加入之前的状态），但「这一对没有安全边际」这个风险换了个形式
留在原地：只要 L4 的权重或 `preference_bonus` 有任何退化，它就会回到 0 分差。
`test_killing_l4_keeps_metrics_but_collapses_the_safety_margin` 已把 0.0500 → 0.0000
这个塌陷钉成断言，所以它不会无声发生。

**F5'　L5 时态降权层对指标惰性。**
见第 5 节。三集指标与未命中索引逐位不变，唯一变化是 golden 余量 −0.1750、
v2 余量 −0.0044。整层删掉，8 个闸门状态不变，三集指标不变。

**F6'　v1/v2 的完整性锁是自测断言，不在冻结清单里。**
v1 有 `HOLDOUT_GOLDEN_SHA256`（`test_memory_retrieval.py` 第 61 行）+
`test_holdout_data_is_hash_locked`（第 86 行，同时钉 `len == 12`）；v2 有
`test_v2_data_is_hash_locked` 与 `test_v2_file_bytes_match_the_pinned_lock`。
**但 `acceptance/MANIFEST.json` 只锁 5 个文件**（4 个 vendor + `acceptance/evals/scenarios.json`），
`tests/` 下一个都不在里面，所以 `g0_freeze` 对这两个集的篡改**完全无感**。
锁与闸门是两套互不相通的机制：改语料会让单测红，但 8 个闸门全绿。
结合 F1'，反过拟合约既不进闸门判定、又不受冻结锁覆盖。

**F7'　（已修，仅留档）自破坏实验的可复现性曾依赖仓库外临时脚本。**
上一版这条是处置建议，本轮已由 `tests/test_ranker_mutations.py`（323 行、10 个用例）
落实为仓库内回归资产。本轮的九路复跑仍用仓库外脚本（`<scratch>/mutate_eval.py`），
但那是**为了独立重写评测口径做交叉校验**，不是因为没有仓库内资产可用；
两者的分工是：仓库内测试负责「钉住结论」，仓库外脚本负责「验证结论不是自说自话」。

**F8'　颜色类 15 个单字 member 在三集上零可观测性。**
见第 6 节。`n1_color_singles` 一路三集逐位与基线相同，连 min_margin 都一样。
不构成缺陷，但精确划出了评测集的覆盖边界，也说明「词典 612 个 member」这个规模里
有一部分是评测集无法为其存在提供证据的。

**F9'　v2 基线本身就低于 0.8，而 8 个闸门全绿。**
v2 实测 P=0.7742 / R=0.7500 / hits 24/32，**低于派单口径的 0.8**。这是已知的、
被 `tests/test_holdout_v2.py` 三条棘轮（0.77 / 0.75 / 24）显式接纳的状态，
未命中的 8 对里 4 对属 D7（零字面重叠语义桥接：本命年→生肖→年龄、窑洞→黄土高原→籍贯
一类），按该文件第 507–519 行的论证归为「超出闭合词表 + 字符 bigram 架构的能力边界」。
需要向主仓说清的是：**这个低于 0.8 的数不出现在任何闸门输出里**，
`run_all.py --strict` 的 `BLOCKED` 与它无关（成因是任务 C/E 未认领，
见 `evidence/task_b_gate_matrix.md` 第 4.3 节）。谁只看闸门就会以为检索质量达标了。

## 11. 结论

1. 已固化的变异演练 `tests/test_ranker_mutations.py` **10 个用例全绿**
   （`Ran 10 tests in 0.050s` / `OK` / 退出码 0），回滚机制经源码逐行核对为
   `mock.patch.object` + `addCleanup` + `assertIs` 身份断言。
2. **不只信测试绿**：九路变异在三个集上的分数由仓库外脚本独立复跑实测，
   评测口径独立重写，与官方 `score_holdout_v2` 交叉校验**九路全部 AGREE (<1e-12)**。
3. 有牙齿 6 路（`unsorted_rank`、`empty_whole_lexicon`、`kill_l3`、`empty_all_members`、
   `n1_all_singles`、`kill_l4`），无牙齿 2 路（`kill_l5`、`n1_color_singles`），
   基线 1 路。无牙齿的两路**如实记录，未加大破坏力度、未改判定口径**。
4. **对派单问题的明确回答：能。** golden 满分而 v1/v2 远低于 0.8 的过拟合实现
   （`empty_all_members`、`kill_l3`）下 `g1_memory.run()` 实测退出码 **0 = PASS**，
   8 个闸门全绿。原因是闸门只看 golden 8 对、且 `run_all.py` 不跑 unittest。
   同一批变异在 254 个单测下会红——防线存在，但不在闸门那一侧。
5. Sarah 那组数字**复现成功**：最终树上「清空全部 member」= golden 1.0000 / v1 0.6667，
   与她在中间态树上的读数一致；更早文档的 golden 0.875 出自 `9eade73` 时期的实现，
   也不是错的——三个读数对应三棵不同的树。v1 = 0.6667 在三棵树上完全未变，
   说明退化总量没变，只是从闸门看得见的集搬到了闸门看不见的集。
6. **可逆性两层实测**：九路每路末尾 `module state restored = True` 且
   `blob hashes unchanged = True`；整份日志前后 8 个被观察路径的 blob 哈希、
   `git status --porcelain -uno`、`git diff --stat`、`HEAD`、`HEAD^{tree}` **全部一字未动**。
   本轮九路一次都没有写盘，与上一版「真改文件 + `git checkout` 兜底」相比是更强的保证。
7. H7（时间戳跨日矛盾）与 H8（行数失真且互相矛盾）**已修**，修法是把时间戳与行数的
   来源统一到 `date` 与 `wc -l`，杜绝手抄；修正前后对照见第 9.1、9.2 节。
8. 新发现 9 条（F1'–F9'），**只报告不处置**。其中 F1'、F2'、F3'、F5'、F6' 是上一版
   F1–F6 的延续或改写，F4' 是上一版 F4 的**反转**（基线上已不是 0 分差），
   F7' 已修仅留档，F8'、F9' 是本轮新增。
