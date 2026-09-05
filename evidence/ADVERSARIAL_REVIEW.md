# 对抗性审查记录（任务：B）

模板：`acceptance/ADVERSARIAL_REVIEW_TEMPLATE.md`（19 行、492 字节，冻结区，本仓无权改）。
本文件按模板的五节结构写，**另加第六节「终态锚点」**——它超出模板，加它的理由写在
该节开头：本文件是 push 前最后两格 commit 之一，模板五节里没有任何位置能容纳
「本文件无法记录自己提交之后的世界」这件事，而不写清楚它就会留下一串自我否定的数字。

要求它的四处，全部在冻结区，本仓一处都改不了，只能满足：`README.md` 第 46 行
（层2 对抗：HIGH/MEDIUM 全部「已修/驳回+理由」）、`README.md` 第 50 行（DoD）、
`INTEGRATION.md` 第 10 行（push 前置条件链）、`tasks/A-persona-prompt/SPEC.md` 第 16 行。

> **【关于 commit hash 的显式标注】** 本文件引用历史一律用 **序数 + subject**，不写
> commit hash。原因：push 前全部本地 commit 的 author 已被改写，改写让**每一个**
> commit hash 都失效了；长期有效的锚点是 **tree 哈希与 blob 哈希**（author 改写不动
> 它们），以及序数与 subject。本文件里的十六进制串**每一个都带类别标签**，共四类：**tree**（某一格时点的主锚点，见 §终态锚点）／**blob**（某个文件的字节）／**内容 sha256**（64 位，不是 git 对象名）／**commit**。
> commit 类只出现在两处：改写前的 `ORIG_HEAD` 值（已注明失效）与**上游基线**——后者不在本仓任何改写范围内，是所有 count / diff 口径的永久左端点，本文件一律用它而不用移动引用 `origin/main`（New-5）。**没有任何一处用 commit hash 指代本仓的某一格**，那一律用序数 + subject；另有 **6** 处 12 位短串与 **3** 处 8 位短串（扫描器不探这两档，逐个定位与标签由命令生成后写在 §提交前手工扫描 的「哈希类」小节），同样一律带类别标签。
> 逐个串的精确构成与裁定不靠手数、由命令生成，写在 §提交前手工扫描 的「哈希类」小节。拿本文件里的任何串去 `git show` 之前请先读标签。

**记号约定**（与 `evidence/task_b_gate_objections.md` 同一套，该卷宗第 20–32 行是原始定义）：
`<repo>` = 本仓库根目录绝对路径；`<scratch>` = 仓库外的取证临时目录；`<home-prefix>/`、
`<win-drive>:\`、`<linux-home-prefix>/`、`<tmp>` 同卷宗。本文件不写任何真实机器路径。

**探针字面样式一律不印出。** 一条描述某形态的句子，如果它展示了那个形态，它自己就
命中那个形态——本项目为此付过五次学费（见发现清单 F21）。所以下文提到扫描探针时
只给编号与语义，不给字面量。

---

## 范围

### 本批 diff 的文件清单（实测，不是声明）

`git diff --stat origin/main..HEAD` 的末行：

```
 40 files changed, 11973 insertions(+), 10 deletions(-)
```

40 个文件按归属分三类，逐类点清（数字来自 `git diff --stat` 与 `git ls-files`）：

| 归属 | 文件数 | 明细 |
|---|---:|---|
| `src/` 改写既有 | 1 | `memory_store.py`（+193 / −10，全部 10 处删除都在这一个文件里） |
| `src/` 新增 | 2 | `memory_ranker.py`（767 行）、`memory_lexicon.py`（349 行） |
| `tests/` 新增 | 14 | 11 个 `test_*.py` + 3 个非测试模块（`holdout_v2.py` 语料、`report_retrieval.py`、`report_weight_robustness.py` 两个报告生成器、`weight_grid.py` 权重网格定义点） |
| `evidence/` 新增 | 23 | 8 份 `.md` + 15 份 `.log` |
| **合计** | **40** | |

`src/memory_store.py` 是 `tasks/B-memory-system/SPEC.md` 第 7 行指定的**唯一工作文件**，
也是本批唯一被改写的既有代码文件。另两个 `src/` 文件是 SPEC 第 8 行允许的新增
（「可新增 `src/memory_ranker.py` 等文件（纯标准库，带 `main-repo-target:` 头）」）。

`tests/test_workbench.py` 是既有基底，**本批一个字节没动**（3 个 `def test_` 原样保留），
它在冻结区清单里。

### 冻结区零触碰：两条独立证据

冻结区 = `vendor/`、`acceptance/`、`tasks/`、`tests/test_workbench.py`、`.gitattributes`。

**证据一（端到端 diff 为空）**：

```
$ git diff origin/main..HEAD -- vendor acceptance tasks tests/test_workbench.py .gitattributes
（无输出）
```

**证据二（逐格 commit 累加为 0）**：对 `git rev-list origin/main..HEAD` 的每一条
commit 单独跑 `git show --pretty=format: --name-only <c> -- <冻结区五个路径>` 并把
命中行数累加，结果是 **0**。这条比证据一强：证据一只说明「起点与终点的冻结区相同」，
理论上允许「中途改了又改回来」；证据二说明**没有任何一格 commit 碰过冻结区的任何
一个文件**，中途改回来这种路径被排除。上一轮已对当时的 43 条跑过同一条命令，本轮
在补头那一格之后对 45 条重跑，两次都是 0。

补充一条现场证据：5 个冻结件的 sha256 与 `acceptance/MANIFEST.json` 逐一复算，
**5/5 MATCH**（`vendor/agent_core/harness.py`、`song_catalog.py`、`voice_text.py`、
`data/luotianyi_original_songs.json`、`acceptance/evals/scenarios.json`）。

### 本批之外的两处改动，如实划清界限

1. **`src/memory_store.py` 第 1 行**由本轮补入（Daniel-2 的处置，单独一格 commit）。
   它是本文件之前唯一一次代码改动，改动是 1 行插入、0 行删除，`git diff --stat`
   在本格提交前只有这一个文件。
2. **`evidence/task_b_gate_objections.md`** 是并行工作者的交付物（1780 行），本轮
   只做「扫描 + 原样提交」，**一个字节没改**：提交前后 sha256 都是
   `9fdd151de37e195709d3f60e8a4ad8aa983bff94f676087aa565bcf0999feadf`
   （内容哈希，不是 commit）。它的 sha256 在派单里已被钉死，逐字节原样入库是硬要求。

---

## 发现清单

表格四列沿用模板。**编号沿用各来源的原编号**，以便与六份原始材料交叉引用；同一问题
被多人独立发现的合并成一行并列出全部来源编号。处置列的四种取值：
**已修（附序数）** / **驳回（附理由）** / **闸门异议（指向卷宗条目，本文件不重复论证）** /
**如实记录（不是缺陷，但读者必须知道）**。

每一行的处置状态都由本轮**重新实测**过，不照抄任何人的登记册。与派单登记册不一致的
地方在行内用「⚠ 核实差异」标出，并在 §统计 之后汇总。

### 来源一 · 正确性视角（审查者 Mark，14 条）

| # | 严重度 | 发现（具体失败路径，file:line） | 处置 |
|---|---|---|---|
| Mark-1 | HIGH | `recall_relevant()`（`src/memory_store.py:129`）按 fact 文本反查行，文本重复时字典塌缩：同一对象返回两次、本会话行永远取不到、session 事实被误标成 `session_id=999` / `scope='global'` | **已修**（序数 7）。本轮核实：候选行改为按 `fact_id` 索引，重复文本场景由 `tests/test_memory_retrieval.py` 的用例钉住 |
| Mark-2 | HIGH | 反过拟合自检断言零判别力：「答案词 + 3 个填充词」即可绕过；且旧留出集 12 条的答案关键词已全部进入词典，消融后留出集 1.000→0.667 而断言仍 8/8 PASS | **已修**（序数 18 重建判据 + 序数 23 按外部规则扩词 + 序数 16 接 v2）。本轮核实：v2 32 对已纳入版本控制并有语料 digest 锁与文件字节锁（`tests/test_holdout_v2.py:102`、`:218`、`:227`） |
| Mark-3 | MEDIUM | 单字 head 子串误命中：`色`/`市` 让「超市」「角色」「脸色」「色号」被判为稳定属性提问，时态降权反噬对题事实，与该层自身 docstring 口径相反 | **已修**（序数 9）。本轮核实：`_masked_scan`（`src/memory_ranker.py:204`）为最长优先贪心掩码 |
| Mark-4 | MEDIUM | `PREFERENCE_MARKERS` 混入否定谓词且不辨极性：问「用户的爱好」时「用户讨厌运动」压过「用户周末徒步」，注入 prompt 即语义反转 | **已修**（序数 9；序数 25/26 深化 RC-4 构词规则与 RC-7 否定辖域）。本轮核实：该名字已不存在于打分路径，拆成 `POSITIVE_MARKERS` / `NEGATIVE_MARKERS` / `QUERY_NEGATIVE_MARKERS` 三组（`src/memory_ranker.py:496`/`:500`/`:506`）+ `_polarity_hits`（`:579`）；残留 2 处命中都是历史交代性引用（`memory_ranker.py:449` 注释、`tests/test_lexicon_polarity.py:101` docstring） |
| Mark-5 | MEDIUM | `bigram_similarity` 对成比例向量返回 1.0，违反 docstring 契约「1.0 only for identical normalized forms」 | **已修**（序数 10，选改契约不改实现 + 锁定断言）。本轮核实：`src/memory_ranker.py:139` 起的契约现写「1.0 iff the two normalized n-gram multisets are proportional」，与实现一致 |
| Mark-6 | MEDIUM | `_concept_hits` 对嵌套子串重复计数（「颜色」同时命中 head「颜色」与 member「色」），自匹配强度跨类不可比（0.500 vs 0.667） | **已修**（序数 9，最长优先贪心掩码）。本轮核实：原语是 `_concept_hit_parts`（`src/memory_ranker.py:246`，被 `:344` 与 `:389` 调用），`_concept_hits`（`:264`）已退化为它的求和包装、**不在打分路径上** |
| Mark-7 ＋ Ryan-1 | HIGH | 同一个函数 `format_memory_prompt()`（`src/memory_store.py:222`）的两个面：Mark 报**未处理 fact 内换行**、输出行结构被破坏；Ryan 报**对 fact 文本零消毒**→存储型 prompt 注入，三条已复现攻击链（伪造段落标记与真实系统提示标记字面相同、多行突破列表结构、伪造列表项前缀），`scope=global` 时跨所有后续会话持久生效 | **已修**（序数 8，两人发现同源合并）。本轮核实：`_sanitize_fact`（`src/memory_store.py:198`）三步顺序不可换——空白折叠为单行 → 段落标记中和（`_MARKER_TRANSLATION`，`:195`）→ 截断到 `_MAX_FACT_CHARS=200`（`:190`）。不变量「输出行数 == 2 + len(facts)」本轮实测成立：limit=1/2/3/4 时行数 3/4/5/6 |
| Mark-8 ＋ Ryan-4 | MEDIUM | `_visible_facts()`（`src/memory_store.py:100`）无 LIMIT：Mark 报全表扫描+全量打分，20000 行时 3996ms（`recall` 同条件 0.3ms），每轮拼 prompt 必经且无上界；Ryan 从安全侧报同一处 `fetchall()` 无界加载 | **已修**（序数 11，两人发现同源合并）。本轮核实：`_RECALL_SCAN_LIMIT = 2000`（`src/memory_store.py:53`），窗口取舍的理由写在 `:46`–`:52` 的注释里（按桌面端单用户每天 20 条计，2000 行≈100 天沉淀） |
| Mark-9 | MEDIUM | `test_empty_query_returns_recent_first` 对顺序零判别力：把 DESC 改成 ASC 也照样绿 | **已修**（序数 12，钉死 `fact_id` 序列）。本轮核实：该用例在 `tests/test_memory_retrieval.py`，文件 31 个用例 |
| Mark-10 | LOW | scope SQL 谓词在 `recall()` 与 `_visible_facts()` 各手抄一遍，无机制强制同步 | **已修**（序数 15）。本轮核实：`_SCOPE_SQL` 常量在 `src/memory_store.py:42`，全仓 4 处引用，另有一致性测试 |
| Mark-11 | LOW | `recall_relevant` 的 `limit`/`query` 无校验：`limit=-1` 静默少返回一条、`limit=True` 当成 1、`limit=1.5`/`'2'` 抛切片 TypeError、`query=None` 抛 AttributeError | **已修**（序数 15）。本轮核实：入口在 `src/memory_store.py:129` |
| Mark-12 | LOW | `str(item.get("query",""))` 对显式 `None` 产出字面量 `"None"`，与含 `"none"` 的事实产生虚假相似度——**指标虚高而非报错** | **已修**（序数 14，抽出 `_as_text`）。本轮核实：`src/` 内 7 处引用 |
| Mark-13 | LOW | 归一化剥离集缺中文弯引号/破折号/间隔号，且实现用 `.lower()` 而 docstring 写 casefold | **已修**（序数 14）。本轮核实：`src/memory_ranker.py:84` 为 `.casefold()`；`:64` 的字符类含通用标点区与间隔号；`:54` 与 `:78`–`:83` 的注释交代了为什么改（lower 不做完全大小写折叠，属文档与代码不符） |
| Mark-14 | LOW | 测试把概念类数钉死为 8（正当新增第 9 类会挂）；桥接只测单向 | **已修**（序数 12，改 `assertGreaterEqual` + 加对称性测试）。本轮核实：类数实测仍为 8（`颜色/城市/称呼/生日/宠物/过敏/职业/爱好`），断言已放宽 |

### 来源二 · 安全视角（审查者 Ryan，4 条；其中 2 条与来源一合并，见上）

| # | 严重度 | 发现（具体失败路径，file:line） | 处置 |
|---|---|---|---|
| Ryan-1 | HIGH | 见 Mark-7 ＋ Ryan-1 行 | 同上（序数 8） |
| Ryan-2 | MEDIUM | `rank()`（`src/memory_ranker.py:682`）每条候选重复归一化 query（8 次）并重建 Counter，query 无长度上限：100000 字符 × 500 候选实测 72.70s，逼近闸门 120s 硬超时 | **已修**（序数 11）。本轮核实：`_QueryContext` 预计算（`src/` 内 10 处引用）+ `_MAX_QUERY_CHARS = 500`（`src/memory_ranker.py:273`）；登记的性能改善为 500 候选 150.9ms→15.2ms |
| Ryan-3 | LOW | `CONCEPT_LEXICON` 与 `W_*` 为模块级可变对象，同进程可篡改 | **已修（一半）＋ ⚠ 核实差异**。本轮实测：`CONCEPT_LEXICON` 确已 `MappingProxyType` 只读化（`src/memory_lexicon.py:63`），且 `memory_ranker.CONCEPT_LEXICON is memory_lexicon.CONCEPT_LEXICON` → `True`，再导出与 `mock.patch.object` 的整体 rebind 都仍有效。**但 `W_*` 一行未动**：序数 14 那格的 diff 里只出现 `CONCEPT_LEXICON` 与 `MappingProxyType`，`W_BIGRAM`/`W_CONCEPT`/`W_PREFERENCE`/`W_TRANSIENT` 至今是 4 个 float 标量（`src/memory_ranker.py:442`–`:445`）。float 本身不可变，没有「内容」可被就地篡改，所以只读化对它不适用；而**模块属性 rebind 对两者都仍然可能**（这是 Python 的固有性质，`MappingProxyType` 也防不住把整个名字指向别的对象）。准确表述：登记册说的「`W_*` 已 MappingProxyType 只读化」**与代码不符**，实际处置是「容器只读化 + 权重保持为不可变标量」，防的是同一件事（就地篡改），手段不同 |
| Ryan-4 | LOW | 见 Mark-8 ＋ Ryan-4 行 | 同上（序数 11） |

### 来源三 · 一致性视角（审查者 Daniel，20 条）

| # | 严重度 | 发现（具体失败路径，file:line） | 处置 |
|---|---|---|---|
| Daniel-1 | HIGH | `evidence/task_b_integration.md` 称用例数「原 15 + 新增 39」，实测基底只有 3 个 `def test_`，两个操作数都错，且与 `gate_snapshot_before.md` 的记载直接矛盾 | **已修一半 ＋ ⚠ 核实差异（本轮重新统计）**。序数 36/37 把「原 15」纠正为「原 3」，但重写时写下的新数字**又过期了**：`integration.md:124` 现称「252 个用例全绿（原 3 + 新增 249）」，本轮实测 **254（原 3 + 新增 251）**。差异**精确到一个文件**：`:134` 那行 `test_ranker_mutations.py` 记 8，实测 10，差的 2 个是 N1 的两个变异体用例（序数 39 加入，晚于 `integration.md` 成文的序数 36/37）。其余 10 行逐个相符。逐文件最终统计见下表。`integration.md` 是已定稿 evidence 文档、本轮铁律禁改，所以**不回改那个 252**；该文档的读法本来就是「各自 commit 时点的测量值」 |
| Daniel-2 | HIGH | `src/memory_store.py` 缺 `main-repo-target:` 头，而 `integration.md` / commit message / `README.md:54` / `SPEC.md:8` 都声称按该头映射，主仓侧只能映射到 1 个文件 | **已修（本轮，序数 45，单独一格 commit）**。核查与处置理由见 §发现清单之后的「Daniel-2 处置专节」。⚠ 核查时另发现一处**比 Daniel-2 更严重**的同族问题（映射表漏列第三个交付文件），一并登记为新条目 New-1 |
| Daniel-3 | HIGH | 五层分工表给 L1/L2/L4 赋予判别职责，但消融实测四层在旧两集零判定翻转；`normalize` 在评测集 50 条去重字符串上是恒等函数（0 条含全角标点、0 条含大写字母），「L1 保证数字形态稳定」从未发生；pair3/pair6 是单候选对，「L2 几乎全重叠」是空归因；且 `self_sabotage.md` 已披露 L5 惰性却未披露 L1/L2/L4，同批交付物内部口径分裂 | **已修**（序数 36）。本轮核实：`evidence/task_b_retrieval_analysis.md` 改为三集实测双口径（翻转数 + 分差贡献），并写入方法论纠正「零翻转 ≠ 无价值」；L5 的惰性在 `self_sabotage.md` §5 有专节，L4 的分差贡献在 §4/§5 有实测数字 |
| Daniel-4 | HIGH | `self_sabotage.md` 头部声称执行时间 09-02 17:46–17:49，其唯一原始日志实为 09-03 07:49–07:50，跨日矛盾且时长不符 | **已修**（上一轮 #11 整份重写而非打补丁，时间戳全部由 `date` 生成）。本轮核实：该文件 495 行，头部锚点节的 commit/tree 与日志内的记录一致 |
| Daniel-5 | HIGH | 同文件称原始日志 632 行，实测 634，且与 `final_selfcheck.md` 的 634 互相矛盾 | **已修**（同上，行数全部由 `wc -l` 生成）。本轮核实：`task_b_self_sabotage.log` 362 行、`task_b_final_check.log` 393 行，两份文档里的行数与 `wc -l` 一致 |
| Daniel-6 | MEDIUM | 序数 3 那格 commit message 的「为什么」称「纯相似度层无法表达这个口径」，实测在其自身代码状态下 L1+L2+L3 已让 golden 8/8、pair8 已分开，只有关掉 L3 才翻转 | **已修**（阶段一 rebase reword，现序数 3）。本轮核实：归因改为「关掉 L3 才翻转」，与消融实测一致 |
| Daniel-7 | MEDIUM | 序数 1 那格 message 说「两块地基」，但该格写入的 docstring 已描述五层并前向引用 4 格之后才创建的证据文件 | **已修**（reword）。现 message 如实交代「docstring 先定五层契约、本格只落 L1/L2、前向引用属有意」 |
| Daniel-8 | MEDIUM | `analysis.md` §五「复现方法」脚本去重后只产出 9 个配置，覆盖不了表里「改 2 个权重」与「改 4 个权重」两行 | **已修**（序数 36）。本轮核实：权重定义点唯一化到 `tests/weight_grid.py`（96 行），命令总表覆盖全部表行。**但本行左侧那两处指针本轮核实已失效，与 `F19` 同类，就地补正**：仓内没有名为 `analysis.md` 的文件（`find` 全仓只有一个匹配 `*analysis*` 的文件），实名 `evidence/task_b_retrieval_analysis.md`；它经序数 36 重写后 §五 的标题是「88 格权重敏感性」，而「复现方法」这个标题在全仓 `grep -rn --include=*.md` 下只剩本行左侧这一处命中，即它已不存在。左侧原文**不回改**（保留 Daniel 当时的表述以便追溯，处置方式与第 262 行一致），补正写在此处 |
| Daniel-9 | MEDIUM | 「结构最恶劣方向」标注为 `W_CONCEPT×0.5 且 W_TRANSIENT×2`（实测 0.1224），而真正最恶劣是三者组合（0.0224，低 5.5 倍） | **已修**（序数 36）。本轮核实：改为实测最恶劣组合 = 0.0014，并注明 0.1224 在全 88 格出现 0 次 |
| Daniel-10 | MEDIUM | 「11/11 扰动配置」把基线算成扰动，实为基线 + 10 个 | **已修**（序数 6 reword + 序数 36 改为 88 个扰动、基线不计入）。⚠ 本轮核实发现**同族问题在另一份文档里仍然存在**：`self_sabotage.md` §3 标题「九路独立复跑的实测分数」，其表为 baseline + 8 路变异，即「九路」把基线计入。登记为 New-2 |
| Daniel-11 | MEDIUM | 「要求 ≥10」「≥3」被写成外部要求，而 SPEC 通篇无此条款、`g1_memory` 也不校验 | **已修**（序数 36）。改为工作台自设并给出理由 + 判据演进史 |
| Daniel-12 | MEDIUM | `final_selfcheck.md:127` 引用了当时尚不存在的 `ADVERSARIAL_REVIEW.md`，F1–F15 无实际落点 | **已修 ＋ 本格彻底闭合**。上一轮 #11 把悬空引用改成准确将来式并挪到 §9，同时修掉旧引用里**四个全部失效的章节指向**（F19）。本轮核实：`final_selfcheck.md` 第 127 行现在是 §3「冻结区 diff 复核」那段命令输出的代码块起始行（标题逐字核对过），悬空引用已不在原位；§9.2（`:567`–`:596`）把模板第 18–19 行两个槽位的实测答案写成了「生成时可以直接抄」的形式。**本文件就是那份被引用的文件，它落地之后这条引用不再悬空——闭合点在此，不在别处** |
| Daniel-13 | MEDIUM | 术语混用「时态降权」/「临时状态降权」/「时态标记」 | **已修**（序数 12 + 阶段三 M19）。统一到「时态降权」 |
| Daniel-14 | MEDIUM | 术语混用「留出集」/「留出验证集」 | **已修**（序数 12）。统一到「留出集」 |
| Daniel-15 | LOW | `rank()` docstring 称 `score_retrieval` 与 `recall_relevant` 都取 top-1，实际后者是 `limit` 参数化 top-k | **已修**（序数 14）。本轮核实：`src/memory_ranker.py:687`–`:691` 明确写「Callers wanting top-k slice the result themselves: score_retrieval always takes top-1 by protocol … the parameter is genuinely top-k and the old wording here wrongly described both callers as top-1」，并标注 review finding L7 |
| Daniel-16 | LOW | docstring 与 commit message 用「Optional」指代 `X \| None`，而全仓零 `typing.Optional` | **docstring 侧已修（序数 15）＋ commit message 侧驳回**。本轮核实：`grep -rn "Optional" src/` → **0 命中**，docstring 侧确实清干净了。**驳回理由（写全）**：本仓已做过三次历史改写（reword ×1、rebase 集成换基 ×1、author 全量改写 ×1）。每一次改写都让全部 commit hash 失效一次，也都让已提交文档里引用的 hash 变成死链——`final_selfcheck.md` §0 现在整段都在解释这件事，`gate_snapshot_before.md` §5.1 里已经躺着 7 个失效 hash 中的 6 个。为「一个措辞不精确但语义正确」的 message 再动第四次历史，代价是又一轮全量死链 + 又一轮文档修订 + 又一次「哪些锚点还活着」的核对，收益是零个行为变化、零个数字变化。且该 message 的语义是对的（那个参数确实可以为 `None`），只是用了 `typing` 的旧名字而不是 PEP 604 的写法。**结论：不改，并把不改的理由留在这里，而不是留成一句「已修」** |
| Daniel-17 | LOW | `integration.md` 称 `limit=3` 时约 700 字符，实测上限 647 | **已修（序数 37）＋ 本轮复核通过**。本轮实测 `format_memory_prompt` 在 limit=1/2/3/4 下的字符数为 **244 / 447 / 650 / 853**，与 `integration.md:86`–`:89` 的表**逐字相符**，且与它 `:82` 的算式 `6+1+34+1+n×(2+200)+(n−1)` 完全一致（代入 n=1..4 得 244/447/650/853）。⚠ 派单登记册记的「实测上限 647」是审查者当时的值，序数 37 重算为 650，本轮独立复算确认 **650** 正确 |
| Daniel-18 | LOW | 「最大的单权重扰动只能挪动分差约 ±0.1 量级」只对 pair8 成立，全体 pair 最大位移 0.3906 | **已修**（序数 36，限定口径并更新为最终实测） |
| Daniel-19 | LOW | 新增文件内部中英混排粒度不统一（部分 docstring 纯英文、部分英文段里夹中文分句） | **已修**（序数 14）。本轮核实：规则原文写在 `src/memory_lexicon.py:24`–`:25`（「契约段纯英文，设计理由另起一段中文，不在英文句子里夹中文分句」），并注明沿用 `memory_ranker` 模块头的约定，供任务 C/E 沿用 |
| Daniel-20 | LOW | 测试辅助 `_fact` 返回注解退化为 `object`；三处方法内惰性 import 与文件顶部 import 并存 | **已修（序数 12）＋ 本轮复核**。`_fact` 的返回注解实测为 `MemoryFact`（`tests/test_memory_retrieval.py:156`、`:245`），不是 `object`。方法内 import 实测只剩 **1 处**（`src/memory_store.py:59` 的 `tempfile`），且它在 `if path is None:` 分支内部——是有意的条件惰性导入（无参构造才需要临时文件），不是「与顶部 import 并存」的那种坏味道。原报的三处已减到这一处 |

### Daniel-1 的逐文件最终统计（本轮实测，口径 = `grep -c "^\s*def test_"`）

| 文件 | 用例数 | | 文件 | 用例数 |
|---|---:|---|---|---:|
| `test_workbench.py`（既有基底，冻结） | 3 | | `test_retrieval_structure.py` | 33 |
| `test_memory_retrieval.py` | 31 | | `test_ranker_mutations.py` | **10** |
| `test_memory_hardening.py` | 43 | | `test_weight_grid.py` | 11 |
| `test_ranker_layers.py` | 43 | | `test_weight_sweep.py` | 21 |
| `test_lexicon_polarity.py` | 12 | | **合计** | **254** |
| `test_lexicon_overfit.py` | 15 | | 其中既有基底 | 3 |
| `test_holdout_v2.py` | 32 | | 其中任务 B 新增 | **251** |

交叉校验：`./.venv/bin/python -m unittest discover -s tests -p "test_*.py" -t tests`
→ `Ran 254 tests` / `OK`。**逐文件求和 254 与 unittest 报告的 254 相等**，两条独立
路径同值。3 个非测试模块（`holdout_v2.py`、`report_retrieval.py`、
`report_weight_robustness.py`、`weight_grid.py`）实测各 0 个 `def test_`，不计入。

### Daniel-2 处置专节（本轮唯一一次代码改动，必须说清为什么）

**核查结果（三条命令，逐条实测）**：

```
$ head -3 src/memory_store.py        # 补头前
"""Task B working file: …            ← 首行是模块 docstring，没有头

$ grep -rn "main-repo-target" src/ tests/ evidence/ README.md INTEGRATION.md tasks/
src/memory_ranker.py:1               ← 有头
src/memory_lexicon.py:1              ← 有头
evidence/task_b_integration.md:3     ← 声称「按 main-repo-target: 头映射」
evidence/task_b_integration.md:5,6   ← 但落点载体是两行表格
README.md:54                         ← 「每个交付文件头部注明主仓落点」
INTEGRATION.md:12                    ← 「并回时按头映射」
tasks/B-memory-system/SPEC.md:8      ← 「可新增 …（纯标准库，带 main-repo-target 头）」
```

判定：**不一致，Daniel-2 成立**。三个 `src/` 交付文件里两个有头、一个没有，而
`integration.md:3` 声称按头映射、实际给出的是表格。

**核查时另发现一处更严重的同族问题（登记为 New-1）**：`integration.md:3` 说
「工作台侧交付**两个**文件」，表格只有两行，**漏列了 `src/memory_lexicon.py`（349 行）**。
而 `src/memory_ranker.py:38` 是 `from .memory_lexicon import CONCEPT_LEXICON, ConceptClass`
——**硬依赖**。主仓侧严格按那张两行表并回，落地即 `ModuleNotFoundError`。Daniel 审查时
`memory_lexicon.py` 还不存在（它是阶段二新增的第三个交付文件），所以这一条不在他的
20 条里，是本轮新发现。

**处置：选 (a) 补头，不选 (b) 改文档。四条理由，按权重排**：

1. **决定性理由**：那份文档的映射表已被实测证明是错的（New-1）。在文档已知有缺陷的
   情况下，把落点信息的**权威载体**从文档表格换成代码头，是选更可靠的一侧。补头之后
   主仓侧一条命令即可机械取全三个落点，不需要先判断「哪个文件没头所以要按同名路径并回」：
   ```
   $ grep -rh "main-repo-target" src/ | sed 's/# main-repo-target: //'
   services/agent-core/agent_core/memory_lexicon.py
   services/agent-core/agent_core/memory_store.py
   services/agent-core/agent_core/memory_ranker.py
   ```
   三个落点齐了，`memory_lexicon.py` 不再可能被漏掉——**补头顺带修掉了 New-1 的后果**，
   而选 (b) 修不掉（(b) 只改措辞，表格仍是两行，除非同时改表格，而那是改已定稿文档）。
2. **铁律排除了 (b)**：本轮禁改已定稿的 evidence 文档，唯一写明的例外就是补这个头。
   所以 (b) 不在允许范围内，(a) 是唯一既处置了问题又不违铁律的做法。
3. **头的值与文档表格逐字相同**，不引入第二个互相矛盾的落点。
4. **「既有文件加头会不会与主仓冲突」——不会，且这一点是实测的**：
   `git log --diff-filter=A -- src/memory_store.py` → 引入它的是上游 bootstrap 那一格；
   `git ls-tree -r origin/main` 里它就在。所以它是**上游既有文件**，主仓侧本来就有同名
   副本，头的语义是「并回到这个既有路径」，与另两个文件的头同构，不产生覆盖冲突。
   按 `SPEC.md:8` 的字面（「可**新增**…带 main-repo-target 头」）该要求只约束新增文件，
   `memory_store.py` 作为既有工作文件严格说**没有违规**；但 `README.md:54` 的措辞是
   「每个交付文件」，更宽。两处口径不一致本身就是要消的东西，补头同时满足两处，
   比论证「谁优先」更省事也更稳。

**复跑验证（任务书要求，全部实测，一项未跳）**：

| 项 | 结果 |
|---|---|
| 模块 docstring 仍有效 | `__doc__` 首行逐字未变、非空（注释不是语句，插在第 1 行不影响第 2 行起的 `"""…"""` 作为模块 docstring）；`MemoryStore` 与 `format_memory_prompt` 两个符号都在 |
| 任务书点名的三个闸门 | `g0_environment` 0 / `g0_secrets` 0 / `g1_memory` 0 |
| 全套 8 闸门 | `0/0/0/0/0/2/2/0`，FAIL 数 0，与补头前基线**逐格相同** |
| 单测 | `Ran 254 tests` / `OK` |
| 三集指标 | golden 8/8 min_margin 0.2676、v1 12/12 min_margin 0.0500、v2 24/32 min_margin 0.0067，与补头前基线**逐字相同** |
| 冻结区 | `git diff --name-only -- <冻结区五路径>` → 0 个文件 |
| 变更范围 | `git diff --stat` → 只有 `src/memory_store.py`，1 insertion、0 deletion |
| 有没有锁会被这一行推倒 | `grep -rn "memory_store" tests/ acceptance/` 再过滤 sha256/hash/`wc -l`/`len(`/lineno/259 → **空**。没有任何断言钉住这个文件的字节数、行数或行号 |

**代价，如实登记不藏**：文件 259 → 260 行，blob（内容哈希，非 commit）从
`49d273aa9286afdf4d6f649b915c56042c9354e1` 变 `84554a5794d24bfa56f4164f79ab2f37894c15fc`。
因此**已提交的** `evidence/task_b_blob_manifest.md` §7 里 `memory_store.py` 那一行
（259 行 + 旧 blob）与合计 13345 成为「生成时点的测量值」，不再等于当前工作树。
本轮铁律禁改已定稿 evidence 文档，所以不回改那一行；对齐方式是一条命令，写在第六节。
tracked 文件数不变（仍 75），因为本格不新增也不删除文件。

**这一格让 commit 总数从派单预期的 46 变成 47**（多出的就是它）。派单第 2 步第 5 点
写的「`git rev-list --count origin/main..HEAD` 应为 46」是在假定 Daniel-2 走 (b)
（只改文档、且改文档也算一格）或假定不处置的前提下算的；选 (a) 就必须多一格。
这不是偏离任务书，任务书第 0.1 步明确要求「若选 (a)…**单独一格 commit** 说明为什么」。

### 来源四 · QA 取证 F 系列（18 条：己方侧 9 条在本文件处置，上游侧 9 条一律转闸门异议）

**己方侧**——缺陷或事实落在本仓交付物里，本文件必须给处置：

| # | 严重度 | 发现（具体失败路径，file:line） | 处置 |
|---|---|---|---|
| F2' | MEDIUM | v1 留出集 12 条的 relevant 全在 `stored` 的第 1 位 ⇒ 位置偏置：`rank()` **完全不排序**时 v1 仍 12/12 | **如实记录：v1 的判别力缺陷未修复，而是被 v2 覆盖。** 本轮实测确认这个覆盖是真的：`unsorted_rank` 那一路变异下 **v1 仍是 12/12 = 1.0000**（三集里唯一没掉的一个），而 golden 掉到 5/8、v2 掉到 12/32。**不改 v1 的数据**——改数据等于为迁就实现修改评测基准，与「照失败条目补词」是同一种 Goodhart，只是方向相反。v2 的位置分布实测为 first 12 / middle 11 / last 7，偏置被设计掉了。v1 保留为回归集，它仍有用（能抓 `n1_all_singles` 那种丢 #2/#3 的退步），只是**抓不到排序失效** |
| F4' | MEDIUM | v1 第 6 对的 min_margin 全部由 L4 单独提供，原为纯平局、靠输入序侥幸赢 | **已修**（序数 9 的极性模型）。本轮实测复核：基线 v1 min_margin = **0.0500 @#5**（0 基索引 #5 即第 6 对），`W_PREFERENCE=0` 时塌到 **0.0000 @#5**——平局确实回来了，说明这 0.0500 全部由 L4 提供，与登记一致。这不是照 badcase 补词：让「过敏」进否定谓词组的独立理由是它是负面约束断言最典型的表达形式，规则先于该对存在 |
| F5' | MEDIUM | L5 时态降权对三集**完全惰性**（零判定翻转） | **已按双口径如实记录**（序数 36）。本轮实测复核两个口径：① 翻转贡献 = **0**（`W_TRANSIENT=0` 时三集 acc/P/R **逐位**与基线相同，v2 的 8 个未命中索引也逐个相同）；② 分差贡献 ≠ 0——v2 #0 的 top1−top2 从基线 **0.1773** 塌到 **0.0023**，降 **98.7%**（出处 `evidence/task_b_retrieval_analysis.md:30`，本轮独立复跑同值）。所以准确表述是「L5 是分差放大器，不是决策改变者」，它是 D1（时态门控）维度的**唯一防线**：没有它，「用户最近在准备考研」与「用户长期定居在苏州」的分差几乎归零 |
| F6' | MEDIUM | v1/v2 的哈希锁是**自测断言**、不在冻结清单内，`g0_freeze` 对这两集篡改完全无感 | **己方一半已修，闸门一半转异议。** 本轮实测：v1 锁在 `tests/test_memory_retrieval.py:61`、v2 锁在 `tests/test_holdout_v2.py:102`，两个 digest 现场重算**均 MATCH**（序列化口径 = `sort_keys` + 紧凑分隔符 + `ensure_ascii=False`）；v2 另有文件字节级锁（`:227`）。**但 `acceptance/MANIFEST.json` 的 5 个冻结件里没有这两个文件**（实测 5 件为 vendor 四件 + `acceptance/evals/scenarios.json`），所以 `g0_freeze` 依然看不见它们 ⇒ 后一半登记为**闸门异议**，指向卷宗条目 22（闸门扫描盲区） |
| F8' | LOW | 颜色类 15 个单字 member 零可观测性 | **已修**（序数 39 固化为两个变异测试）。本轮实测复核，四个数字全部对上：全词典单字 member = **28** 个（颜色 15、生日 4、宠物 4、过敏 3、称呼 2）；`n1_color_singles` 一路三集**逐位**与基线相同、连 min_margin 都一样（golden 0.2676 @#7 / v1 0.0500 @#5 / v2 0.0067 @#5），v2 #29「藏青色」仍命中（`_masked_scan` 最长优先取到长词「藏青」）；`n1_all_singles` 一路丢 v1 #2/#3 与 v2 #24（24→23）。两个断言在 `tests/test_ranker_mutations.py:283` 与 `:300` |
| F17 | — | v2 两条棘轮余量为 **0** | **不是缺陷，是必须写进交接的事实。** 本轮实测 `tests/test_holdout_v2.py:496`–`:504`：precision 实测 0.7741935483870968 → 阈值 0.77，余量 **0.0042**；recall 实测 0.75 → 阈值 0.75，余量 **0.0000**；命中对数实测 24 → 棘轮 `V2_RATCHET_HITS = 24`，余量 **0**。三条棘轮里**两条余量为 0**（recall 与 hits）。**下一个人不要以为还有空间**：任何让 v2 少命中一对的改动会同时踩响两条。同处注释给了保守取整的论证——掉一对会让 precision 变 0.7419（跌 0.0323，是余量的 7.7 倍）、recall 变 0.7167（跌 0.0333），两者都能被单对退步触发、又不会被无害浮点扰动误触发 |
| F19 | MEDIUM | 交叉引用腐坏：上一版 `final_selfcheck.md` 第 127 行的四个章节指向**四个全错** | **已修**（上一轮 #11 整份重写而非打补丁）。本轮核实：`final_selfcheck.md:558`–`:565` 逐条记下了四个失效指向（反 Goodhart 清单在第 10 节不是第 8 节、drill 四缺陷在第 6 节不是第 4 节、`gate_matrix.md` 根本没有 F8/F15 这种编号、「本报告第 7 节」现已对应第 8 节），并给出定性：「这正是『打补丁式修订』会留下的典型残渣——改了正文没改交叉引用」 |
| F20 | LOW | 取证者自己的两个**仓库外**脚本第一版有缺陷：`drill_attribution.py` 用含 `bytes=` 的字符串比较行尾形态，导致三路全部误报「行尾被改写 = True」，**与要证明的结论方向相反**；`mutate_eval.py` 未显式传 ranker，而官方评分器的 `ranker` 是**默认参数、在 def 执行时就已绑定**，事后 patch 模块属性拦不住，导致一路误报 DIVERGE | **如实记录。** 两处都不是仓库缺陷，但若不记，读者会把假信号当实测结论。第二个缺陷的机制已写进脚本注释（`<scratch>/mutate_eval.py` 的 NOTE 段）与 `tests/test_holdout_v2.py` 的对应说明，并沉淀为 N11 的第二条 Python 语义陷阱。**本轮这两个脚本又被用了一次**（12 路变异 + 12 路闸门退出码），两处缺陷的修正版都经受了复跑：12 路交叉校验**全部 AGREE (<1e-12)**，零 DIVERGE |
| F21 | MEDIUM | 证据自指泄漏**上一轮犯了五次**：为解释消毒而把探针字面样式印进文档，文档就命中自己描述的探针。另有两个机制发现：**一步滞后**（扫描报告扫到的是磁盘上上一轮的它自己，所以单轮为 0 不构成证据，判收敛必须连跑两轮并 diff）与**回显发散**（原样回显命中令牌会让报告命中自己的回显节，计数不存在不动点，必须记号化） | **如实记录，并已固化成方法。** 收敛判据改为「最后连续两轮除时间戳行外逐字相同、且两轮退出码均为 0」，不用轮次序号（「入库的是第 N 轮」这句话本身又是一次修订，序号永远追不上）。**本文件自己遵守同一套纪律**：全文提到扫描探针时只给编号与语义，不印字面样式；§提交前手工扫描 记录本轮扫描结果时，命中令牌一律记号化。**本轮这套纪律又被验证了一次**——卷宗里有 6 处命中，全部是「为了证明不含某形态而必须展示该形态」，详见 §提交前手工扫描 |

**上游侧**——缺陷落在冻结区或上游资产里，本仓无权改，一律标**闸门异议**并指向
`evidence/task_b_gate_objections.md` 的对应条目，**本文件不重复论证**：

| # | 严重度 | 一句话 | 处置 |
|---|---|---|---|
| F1' | HIGH | **最有力的一条。** 一个 golden 满分但 v1 只有 0.667 的过拟合实现能通过全部 8 个闸门。本轮**不是引用上一轮结论，是重新实测**：12 路变异下逐路调真闸门 `g1_memory.run()`，**10 路退出码 0 = PASS、2 路 1 = FAIL**。PASS 的 10 路里含 `empty_all_members` 与 `kill_l3`（golden 仍 1.0000、v1 掉到 0.6667、v2 掉到 21/32），也含 `kill_l4`、`kill_l5`、`n1_color_singles`、`n1_all_singles` 与两路 M 复现。根因两条：闸门只 import 内联 GOLDEN、从不看 44 对反过拟合语料；`run_all.py` 的 `GATES` 不含 unittest ⇒ **钉住过拟合的三道棘轮全部在单测侧，而验收闸门一条都看不见** | **闸门异议** → 卷宗条目 10（`:703`，`GATES` 不含单测）、条目 11（`:732`，留出集不进闸门）、条目 12（`:747`，清空词典后闸门仍 PASS 的实测证据）、条目 14（`:807`，建议裁决方向）。本文件只补一件事：**把实测从 4 路扩到 12 路**，表在 §反 Goodhart 自证 的「十二路变异 × 三集 × 真闸门退出码」子节 |
| F3' | MEDIUM | golden 8 对 × 阈值 0.8 ⇒ 判别余量恰好 **1 个样本**：错 1 对是 0.875，仍 ≥ 0.8，与 1.0000 同样显示 PASS | **闸门异议** → 卷宗条目 13（`:793`，阈值判别力；建议闸门输出回显实测 P/R 数值或提高 golden 规模）。本轮实测复核这条余量确实被踩到过：`empty_whole_lexicon` 让 golden 掉到 **6/8 = 0.7500** 才终于 FAIL，`unsorted_rank` 掉到 5/8 = 0.6250；而 `n1_all_singles`、`kill_l4` 等 8 路 golden 都是 8/8，闸门一位不动 |
| F9' | MEDIUM | v2 基线低于 0.8 这个数（P 0.7742 / R 0.7500）**不出现在任何闸门输出里** | **闸门异议** → 卷宗条目 13（`:793`）与条目 11（`:732`）。补充本轮实测：8 闸门的输出里没有任何一个数来自 v1 或 v2，`g1_memory` 打印的 P/R 只由 golden 8 对算出 |
| F10 | HIGH | `sabotage_drill.py` 无「破坏前该 gate 必须是绿的」前置断言 | **闸门异议** → 卷宗条目 15（`:817`）。**状态已变**：集成后 `g0_freeze` 转 PASS，三路的前置绿条件现已全部满足，「有效检出实为 2/3」的推论**已失效**；但**缺陷①本身仍在代码里**，见卷宗条目 D（`:966`） |
| F11 | MEDIUM | drill「恢复后复跑 gate 验证回绿」是**死代码**（`try/finally` 后 `return` 使其不可达），已用 **AST 静态证明**三判据全 True | **闸门异议** → 卷宗条目 17（`:874`）与条目 D（`:966`，AST 证明的三判据）。本轮的补偿控制见 §反 Goodhart 自证 的第一个子项（那里列了三条补偿控制）：手工复验回绿 + 前后 blob 逐一比对 |
| F12 | MEDIUM | `run_gate()` 丢弃闸门 stdout+stderr ⇒ 三路全成功时 drill 只输出一行，无法审计；且 FAIL 项的 detail 可能为空 | **闸门异议** → 卷宗条目 18（`:927`，丢弃 stdout/stderr）与条目 9（`:685`，编排器侧丢弃子进程 stderr）。本轮实测印证：`evidence/task_b_sabotage_drill.log` 全文只有 **9 行**，其中实质输出仅 `DRILLS DETECTED: 3 of 3` 一行 |
| F13 | LOW | `evidence/README.md` 第 8 行「提交前删除过期运行记录，保留最后 10 条」与 `run_all.py` **无任何裁剪逻辑**冲突 | **闸门异议** → 卷宗条目 21（`:1016`）。本轮实测：`evidence/run_*.json` 已从 20 涨到 **66**，无任何环节裁剪或告警。补充一条本轮才看清的事实：这些 JSON 被 `.gitignore` 忽略，所以「保留最后 10 条」这条规则**既无法被执行也无法被核查**——它约束的对象根本不在版本控制里 |
| F16 | MEDIUM | `run_all.py` 第 59 行的 evidence 文件名只到**秒级**，同秒静默覆盖 | **闸门异议** → 卷宗条目 8（`:667`，实测已丢失 1 份 JSON）。本轮不重复论证 |
| F18 | HIGH | 冻结区里的 DoD 写着「`run_all.py --strict` 全绿」，在任务 C/E 落地前**按字面不可达**（`g1_permissions` 与 `g1_tools` 恒 PENDING，strict 模式遇 PENDING 判 `BLOCKED`），而这两处文档本仓无权改 | **闸门异议** → 卷宗条目 25（`:1188`，DoD 与单任务包交付节点的语义缝隙）、条目 7（`:621`，verdict 逻辑使 strict 在存在 FAIL 时零信息量）、条目 26（`:1213`，本仓侧的应对）。本轮实测复核：48 格矩阵 PASS 36 / PENDING 12 / **FAIL 0**，12 格 PENDING 全部落在 `g1_permissions` 与 `g1_tools` 两行（各 6 格） |

### 来源五 · 集成期新发现（Nick 的条目 A–F、Sarah 追加的双重转义、Nick 本轮 author 改写的 5 条）

条目 A–F 与双重转义**全部已在卷宗里完整论证**，本文件只做交叉引用与状态更新，
不重复论证。Nick 本轮（author 改写）新报的 5 条里，**N1 与 N2 要在本文件处置**，
N3/N4/N5 记为团队经验。

| # | 严重度 | 一句话 | 处置 |
|---|---|---|---|
| 条目 A | HIGH | `vendor/agent_core/harness.py` 的旧期望值无法由本仓任何字节得出：14 种行尾/编码变换 **0/14** 命中、全对象库 **108 个 blob** 反查无命中；而对照组 `scenarios.json` 的旧值**精确等于**其 blob 的 CRLF 渲染 ⇒ 上游 commit message 的「CRLF bootstrap drift」对 `scenarios.json` 成立、对 `harness.py` **不成立**。不能排除 vendor 的 `harness.py` 与主仓副本内容不同，而 `g1_contract`/`g3_simulate`/`sabotage_drill` 全以它为前提，**结论可迁移性存疑** | **闸门异议** → 卷宗条目 A（`:262`）。本轮补充一条现场证据：`vendor/agent_core/harness.py` 的 sha256 与 MANIFEST **MATCH**（5/5 之一），所以本仓侧它没被动过；存疑的是**上游那个旧期望值怎么来的**，这只能由主仓回答 |
| 条目 B | HIGH | `g0_freeze` 校验的是**磁盘 raw 字节**而非 git blob，与 clean/smudge 过滤器完全解耦 ⇒ 是全部漂移事故的**单一根因**，红绿不可跨机器复现 | **闸门异议** → 卷宗条目 B（`:400`）。本仓侧无法处置：修它要改 `acceptance/gates/g0_freeze.py`，在冻结区 |
| 条目 C | MEDIUM-HIGH | `MANIFEST.json` **自身不在 `FREEZE_TARGETS` 内**，且 `--update` 无任何守卫、缺文件时静默剔除该条 ⇒ **冻结锁缺完整性锚点，约束靠规程而非代码** | **闸门异议** → 卷宗条目 C（`:464`）。本轮实测印证「锁文件自己没被锁」：MANIFEST 列出的 5 个冻结件里没有它自己 |
| 条目 D | MEDIUM | drill 第 38–43 行不可达（AST 三判据全 True）。**并记录状态变化**：集成后 `g0_freeze` 转 PASS，「有效检出 2/3」的保留意见**已解除**，本轮实测 **3/3 有效** | **闸门异议 ＋ 状态更新** → 卷宗条目 D（`:966`）与条目 17（`:874`）。**解除的理由不是 drill 变好了**：前置绿断言是本轮用外部 8 闸门快照补上的，缺陷①仍在代码里。详见 §反 Goodhart 自证 的第一个子项 |
| 条目 E | LOW | `MANIFEST.json` 无尾换行，`git diff` 每次都要额外打一行「无尾换行」提示 | **闸门异议** → 卷宗条目 E（`:362`）。修它要改 MANIFEST 自身 sha256，须与 B/C 一并裁决 |
| 条目 F | HIGH | `git checkout --` 对「clean 过滤后等价于 index」的文件是 **no-op** ⇒ 必须 `rm` + `git checkout HEAD --`，形成「git 说 clean、闸门读 raw 说 FAIL」的语义裂缝，**主仓在 Windows 会原样复现** | **闸门异议** → 卷宗条目 F（`:542`，`<tmp>` 副本已完整复现 no-op 的成立条件与失效条件）。这条对集成最要紧：它不在任何文档里，而踩上它的人会以为自己在做正确的恢复操作 |
| 双重转义 | MEDIUM-HIGH | `g0_environment.py` 第 44 行的**路径 needle 双重转义**：它找的是「盘符 + 冒号 + **两个**反斜杠」，而真实 Windows 硬编码路径只有**一个**反斜杠 ⇒ **4 个路径 needle 里 2 个实际不工作**，常规盘符硬编码路径会漏检。加上第 45 行对 `acceptance/` 的整体豁免，这个缺陷能长期待在闸门目录里而不被自己检出 | **闸门异议** → 卷宗条目 22 盲区 ③（`:1045`），严重度已由 MEDIUM 上调为 MEDIUM-HIGH。**这条直接决定了本轮 §提交前手工扫描 的探针集**：不能只用闸门那四个 needle，否则会继承它的漏检，所以本仓侧自补了 Linux 家目录前缀与 macOS 私有临时目录前缀两个闸门根本不管的模式 |
| Nick-N1 | MEDIUM | `refs/original/refs/heads/main` 残留仍使改写前 44 个旧 commit **可达**：`git log --all` 会同时看到两套身份；`git push --mirror` 会把旧身份历史一并推上远端从而**抵消改写**（但 `git push origin main` 与 `git push --all` 都不会） | **本文件处置（安排写死在此，不留悬空项）**：本轮实测该 ref 仍在，指向 `2f49e325bbd2…`（**改写前**的 HEAD，短串仅作定位、已失效于改写后的编号体系之外）。它是当前**唯一的回滚把手**——删了它，改写前的 44 格就只能靠 reflog 捞，而 reflog 会过期。**处置顺序：本文件与卷宗提交后，由 push 那一格在推送成功之后执行 `git update-ref -d refs/original/refs/heads/main` 清理；在此之前谁都不许删。且 push 那一格必须用 `git push origin main`，不许用 `--mirror`** |
| Nick-N2 | LOW | `.git/ORIG_HEAD` 仍指向任务 #20 rebase 前的旧 HEAD（`3d7bdc9c…`），**不是** author 改写前的 `2f49e325…`；若有人以为 `git reset --hard ORIG_HEAD` 能回到「改写前」，实际会一次性退回 **14 格之前** | **本文件处置：如实写明，不清理。** 本轮实测 `ORIG_HEAD` = `3d7bdc9c3fefa4da87d55eee31ef0aeba86cf6db`，与 `refs/original` 指向的 `2f49e325bbd2…` **不是同一个**。**`ORIG_HEAD` 是任务 #20 那次 rebase 的遗留，不是本次 author 改写的回滚点。** 它是 `.git/` 下的伪 ref，不参与 push、不会被推到远端，所以没有清理的必要；留着它的唯一风险是被人误当回滚点，而这个风险由本条文字消除 |
| Nick-N3 | — | author 改写的手法 A（`--env-filter` 里重设 committer date）会**静默压平** committer date；已改用手法 B 规避 | **记为团队经验。** 本轮实测复核结果：`%cd` 去重 **16** 个值 = 基准 16，未被压平；`%ad` 亦完整保留；45 格 commit 的 author 与 committer **全部**为同一身份（本轮新提交的那一格由 `git config --local` 自动沿用，**没有传 `--author`、没有改任何 git config**） |
| Nick-N4 | — | 裸 hash 探针 `\b[0-9a-f]{7,40}\b` 会**误命中十进制小数**（如评测输出里的长浮点），建议收紧为「命中串必须 `git cat-file -e` 存在且类型为 `commit`」 | **记为探针改进建议，本轮已采纳并实测有效。** 本轮扫描对三个目标文件同时给出朴素计数与收紧计数：卷宗里朴素判据会命中的十进制小数形态 **1 处**，收紧后**全部排除**；收紧判据下算作 commit 的 = **0**（详见 §提交前手工扫描） |
| Nick-N5 | — | author 改写确为**纯元数据操作**，六重证据交叉确认未触碰工作树 | **记为团队经验。** 本轮起点复核再次确认：改写前后 HEAD tree **同为** `1ceaf1df5cf6c5bdca262f48efa5f42085cd408b`（序数 44 时点），tracked 仍 75，冻结区 diff 仍空，5 冻结件仍 5/5 MATCH |

### 统计

本节汇总上面五个来源。**所有数字由 `<scratch>/sev_by_source.py` 与
`<scratch>/dispo_stats2.py` 两个脚本现场解析本文件的表格行生成**，不是手数，也不是
沿用任何人的登记册；复现命令写在本节末。

**表行 68 / 独立条目 66。** 差的 2 行是 `Ryan-1` 与 `Ryan-4`：它们是纯交叉引用行
（问题本体已在来源一的 `Mark-7 ＋ Ryan-1`、`Mark-8 ＋ Ryan-4` 两行里登记），只列
来源编号、不独立计数，否则会虚增两条 HIGH/LOW。

按来源 × 严重度：

| 来源 | 表行 | HIGH | MEDIUM-HIGH | MEDIUM | LOW | 无严重度 |
|---|---:|---:|---:|---:|---:|---:|
| 来源一 · 正确性（Mark） | 14 | 3 | 0 | 6 | 5 | 0 |
| 来源二 · 安全（Ryan） | 4 | 1 | 0 | 1 | 2 | 0 |
| 来源三 · 一致性（Daniel） | 20 | 5 | 0 | 9 | 6 | 0 |
| 来源四 · QA 取证 F 系列 | 18 | 3 | 0 | 11 | 3 | 1 |
| 来源五 · 条目 A–F ＋ 双重转义 | 7 | 3 | 2 | 1 | 1 | 0 |
| 来源五 · Nick-N1…N5 | 5 | 0 | 0 | 1 | 1 | 3 |
| **表行合计** | **68** | **15** | **2** | **29** | **18** | **4** |
| **独立条目合计**（扣 `Ryan-1` HIGH、`Ryan-4` LOW 两条交叉引用行） | **66** | **14** | **2** | **29** | **17** | **4** |

按处置（表行口径，合计 68）：

| 处置 | 条数 | 说明 |
|---|---:|---|
| 已修（附序数） | 41 | 全部用 **subject ＋ 序数** 定位，不用裸 commit hash，理由见文件开头那个 blockquote |
| 闸门异议（指向卷宗条目） | 16 | 缺陷体在冻结区或上游资产里，本仓无权改；一律给出卷宗条目号与行号 |
| 闸门异议 ＋ 状态更新（条目 D） | 1 | 既是异议，又记录了「有效检出 2/3 → 3/3」的改判 |
| 本文件处置（Nick-N1、Nick-N2） | 2 | 处置动作是「写死清理顺序」与「如实写明不清理」，不是改代码 |
| 驳回（附理由） | 1 | `F2'`：不改 v1 数据，理由已在行内写全 |
| 如实记录（不是缺陷） | 2 | `F17`（无严重度，v2 棘轮余量为 0）、`F20`（LOW，取证者自己脚本的第一版缺陷） |
| 记为团队经验 / 探针改进建议 | 3 | `Nick-N3`、`Nick-N4`、`Nick-N5`，三条都无严重度 |
| 交叉引用行（不独立计数） | 2 | `Ryan-1`、`Ryan-4` |

**脚本里有三处人工判定，必须公开，否则「数字由脚本生成」这句话会藏住判断**：
`F2'`、`F5'`、`F21` 三行处置列的**首词**都是「如实记录」，但正文里都带硬处置，
所以脚本按行内证据分别归为 **驳回**（`F2'`：「不改 v1 的数据」＋理由写全 = 驳回＋理由）、
**已修**（`F5'`：序数 36 双口径重写）、**已修**（`F21`：收敛判据已改＋固化成方法）。
这三处归类是判断，不是解析；如果按首词机械归类，「如实记录」会从 2 变成 5、
「驳回」变成 0、「已修」变成 39。两种归法都不影响层2 判据的结论（下面那 45/45），
因为 `F2'` 与 `F21` 在两种归法下都算有明确处置。

**层2 判据核对（`README.md` 第 46 行要求的那一条）**：HIGH ＋ MEDIUM-HIGH ＋ MEDIUM
= 14 ＋ 2 ＋ 29 = **45 条**，脚本逐条检查其处置列，**45/45 都是硬处置**（已修 /
闸门异议 / 驳回 / 本文件处置），**0 条只有「如实记录」这类软处置**。这 45 条里有
**17 条**走的是「闸门异议」——不是回避，是缺陷体全在冻结区（`acceptance/`）或上游
资产里，本仓改不了；每条都给了卷宗条目号，异议本身有十章 27 条的完整论证。
LOW 17 条与无严重度 4 条按判据可以遗留，其中真正遗留不修的已在行内写明理由
（典型是 `F8'`「颜色类 15 个单字 member 零可观测性」——已用两个变异测试固化，
但 member 本身没删，因为删了会动语料 digest）。

复现这两个表：

```
$ <repo>/.venv/bin/python <scratch>/sev_by_source.py
$ <repo>/.venv/bin/python <scratch>/dispo_stats2.py
```

两个脚本都在仓库外（本轮铁律只准改本文件，不准往 `evidence/` 里加新文件），所以
它们**不是仓库内资产**；上面两个表是它们的完整输出转录，读者不需要脚本也能核。

**加一张新表之前先读 New-8。** 这两个脚本按第一列的编号前缀认来源，
表头若以那七个前缀之一开头，表头行自己就会被当成一条发现算进去——
本轮真的踩了一次，虚增出 1 行、1 个「未归类」处置和 1 个对不上的严重度。

### 核实差异与新增登记

**⚠ 核实差异 5 条**（本文件的实测结果与派单登记册或既有文档不一致，行内已标
「⚠」，此处汇总，按第 98 行的承诺放在 §统计 之后）：

| 编号 | 行 | 差异 | 处置 |
|---|---:|---|---|
| `Ryan-3` | 125 | 登记册称「`W_*` 已 `MappingProxyType` 只读化」**与代码不符**：只读化只覆盖了 `CONCEPT_LEXICON`（`src/memory_lexicon.py:63`），4 个 `W_*` 至今是 float 标量（`src/memory_ranker.py:442`–`:445`）。float 无内容可就地篡改，所以只读化对它不适用；但**模块属性 rebind 对两者都仍然可能** | 如实登记，不改代码（改不了：只读化那格是序数 14，已定稿）。防的是同一件事、手段不同，登记册的表述过强 |
| `Daniel-1` | 132 | 序数 36/37 纠正了「原 15 → 原 3」，但写下的新数字**又过期了**：`integration.md:124` 称「252（原 3 ＋ 新增 249）」，本轮实测 **254（原 3 ＋ 新增 251）**；差异精确到一个文件——`:134` 那行 `test_ranker_mutations.py` 记 8，实测 **10**，差的 2 个是 N1 两个变异体用例（序数 39 加入，晚于 `integration.md` 成文） | 不回改（已定稿 evidence，本轮铁律禁改）。对齐方式是一条命令，见 §终态锚点 |
| `Daniel-2` | 133 | 核查时另发现一处**比 Daniel-2 更严重**的同族问题 | 登记为 New-1 |
| `Daniel-10` | 141 | 同族口径问题在另一份文档里仍然存在：`self_sabotage.md` §3 标题「九路独立复跑的实测分数」，其表为 baseline ＋ 8 路变异，即**把基线计入「九路」** | 登记为 New-2，并在 §反 Goodhart 自证 开头把三种口径钉死 |
| `Daniel-17` | 148 | 派单登记册记的「实测上限 647」是审查者当时的值，序数 37 重算为 **650**，本轮独立复算确认 **650** 正确 | 登记册的值过期，以本轮复算为准 |

**本轮新增 8 条**（不占用任何来源的编号，统一用 `New-`，因为它们是本文件写作过程中
自己撞出来的，不属于五个来源里的任何一个；`New-6` 在 §反 Goodhart 自证 里论证、`New-7` 在
§提交前手工扫描 里论证、`New-8` 就在 §统计 的复现命令之后，此处一并登记）：

| # | 严重度 | 发现 | 处置 |
|---|---|---|---|
| New-1 | MEDIUM | `evidence/task_b_integration.md:3` 的交付文件映射表**漏列 `src/memory_lexicon.py`**，只列了 `memory_store.py` 与 `memory_ranker.py`。这比 Daniel-2 更严重：Daniel-2 是「文件缺头」，补头即可；New-1 是「映射表本身少一行」，主仓按表映射会**永久漏掉一个 349 行的交付文件**，而三个文件都带 `main-repo-target:` 头，靠头映射能对得上、靠表映射对不上 | **已修（序数 45）**：补头那一格同时把三个文件的头写全，使「按头映射」这条路径完备；表本身在已定稿文档里，不回改，在此登记 |
| New-2 | LOW | 「九路」在本项目有**三种互不相同的口径**：甲 = `task_b_self_sabotage.md` §3（基线计入，baseline ＋ 8 路 = 9）；乙 = `tests/test_ranker_mutations.py` docstring（有牙齿 4 ＋ 无牙齿 4 = 8 路变异，基线不计入）；丙 = 卷宗表 D「我方九路」（M1–M9，基线另列 = 9）。三个「九」指的不是同一组东西 | **如实记录 ＋ 口径钉死**：本轮采用口径丙，并把总数扩到 **12 路 = 1 基线 ＋ 9（M1–M9）＋ 2（N1 的 A/B 两个变异体）**，与 F1' 行已写死的「12 路 / 10 PASS / 2 FAIL」一致。三套口径的对照表在 §反 Goodhart 自证 |
| New-3 | LOW | `Nick-N3` 记的「`%cd` 去重 16」是**44 格时点的测量值，不是不变量**。本轮按同一口径逐格复测：44 格 = **16**、45 格 = **17**、46 格 = **18**（每多一格 ＋1）。Nick 的数字**正确**，但它随 commit 数增长，不能当锚点引用 | **如实记录。** 这不是差异，是口径补充。同时记一条方法论：本轮第一次测这个量时用 `git log … \| head -44` 取「前 44 格」，而 `git log` 是新→旧排序，`head -44` 取到的是**最新** 44 条，结果一度看起来像「Nick 的数字复现不出来」；改用 `<上游基线>..HEAD~2` 之后三个值全部对上。**差点因此在文档里写下一条对同事的错误指控** |
| New-4 | LOW | 提交前扫描的探针 P07（macOS 私有临时目录前缀）会**误命中本仓自己的消毒记号**：它的词边界字符类不排除连字符与尖括号，于是那个记号本身被判成「真实路径前缀」。实测卷宗里泄漏类命中 **12** 处，其中 **6** 处是这一类误命中（记号，不是路径），另外 **6** 处才是真正的 F21 型「为证明不含某形态而展示该形态」 | **如实记录 ＋ 在本文件内补全总数**：第 262 行写的「6 处」对 P09＋P10 那个子集是正确的，但**不完整**（泄漏类总数 12）。该行**不回改**（保留原始表述以便追溯），补全与逐条裁定见 §提交前手工扫描。探针本身在仓库外脚本里，本轮铁律禁改其它文件，故只登记不改；修法是把词边界类扩到排除 `-`/`<`/`>` |
| New-5 | MEDIUM | **`origin/main` 是移动引用，本文件写作期间它动了。** 本轮实测：`git reflog show origin/main` 有两条 `fetch origin: fast-forward`，第二条把 `origin/main` 从上游基线推进到 **基线 ＋ 6 格**（6 格里有任务 C、任务 E、任务 A 各若干，**以及上游那版任务 B 的实现**）。后果三条：① §范围 里 `git diff --stat origin/main..HEAD` 的「40 files changed, 11973 insertions(+), 10 deletions(-)」**已不可复现**，同一命令现在给出 61 files / 13767 / 4991；② `behind` 从本轮早先实测的 **0** 变成 **6**；③ **HEAD 与 `origin/main` 已分叉**（`merge-base` = 上游基线，两边各有 46 格与 6 格），**快进推送不再可能** | **如实记录 ＋ 换口径，不动 git。** 本文件此后所有 diff/count 一律用 **`<上游基线 commit>..HEAD`**（该 commit 不在任何改写范围内，是永久有效的锚点），不用 `origin/main`。稳定口径下的实测：序数 46 时点 `41 files changed, 13753 insertions(+), 10 deletions(-)`。分叉本身**不在本文件职权内**（本轮铁律禁 fetch / rebase / merge / push），移交 push 那一格处置 |
| New-6 | LOW | `tests/test_ranker_mutations.py` 把变异路 M6（`W_PREFERENCE = 0`）归入「无牙齿」，但那条用例（`:200`）只断言 golden 与 v1 两集，**没调文件里已存在的 `_v2_hit_count()`（`:74`）**；加上 v2 后这一路按「任一集指标动了」的判据是**有牙齿的：24 → 22** | **如实登记为己方发现，本轮不改 `tests/`**（铁律禁改）。三个可选处置与推荐顺序见 §反 Goodhart 自证 的「M6 的修正」小节 |
| New-7 | LOW | 提交前扫描的探针 P09（厂商 API key 前缀，两种样式）用的是**纯字面子串匹配、左右都没有词边界**：其中一种前缀的两个字母加连字符，恰好是英文里表示「任务」的那个常见词的**后半**，于是本项目每一个任务标识符（形如「任务词＋连字符＋单个大写字母」）都会被它判成「含密钥前缀」。本轮实测本文件命中 **4** 处，全部是这一个机制；卷宗那 **5** 处则是真 F21（把探针正则的字面写进文档），两者机制不同、必须分开裁定 | **如实记录 ＋ 就地降噪，探针本身不改**（它在仓库外脚本里，本轮铁律禁改其它文件）。降噪做法：凡是**自己的概述性提及**一律改用中文「任务 C / 任务 E / 任务 A」，命中从 4 压到 **1**；剩下那 1 处是**逐字引用上游 commit subject**，引用原文不该改，保留并在 §提交前手工扫描 逐条裁定。**写这一行本身也踩在同一个陷阱上**：解释这个误命中若直接展示那个形态，就会新增命中，所以本行全程用结构描述而不贴字面。探针修法同 New-4：给字面探针加左边界（排除字母） |
| New-8 | LOW | §统计 那两个表由脚本**解析本文件的表格行**生成，脚本按**第一列的编号前缀**认来源（`Mark` / `Ryan` / `Daniel` / `F`＋数字 / `条目` / `双重转义` / `Nick-N` 七个）。`### 核实差异与新增登记` 那张表的第一列原本叫「条目」，与来源五的「条目 A–F」**前缀撞车**，于是**表头行自己被当成一条发现算了进去**：表行 68 → 69、独立条目 66 → 67、处置分布里凭空多出一个「未归类 1」，严重度合计也对不上（多出的那行第二列是「行」，不是任何严重度） | **已修（就在本文件内，这一格）**：把那张表第一列的表头从「条目」改成「编号」，重跑两个脚本，三个数字全部回到 **68 / 66 / 无「未归类」**，与 §统计 表里已写死的值逐字一致。**方法学教训**：解析型统计脚本的识别规则与文档措辞是**耦合**的，任何人加一张新表都可能静默虚增计数，而且虚增出来的那一条既没有严重度也没有处置，看上去像是「漏了处置的 HIGH」。所以本文件立下规定：**任何表格第一列的表头都不得以那七个前缀开头**；两个脚本的输出原样转录进 §统计，读者可以逐格复核 |

---

## 视角

模板这一节的三个子项，对应的是**三个互不知情的独立审查者**：Mark 只做正确性、
Ryan 只做安全、Daniel 只做一致性，三人各自被明令**忽略另外两个维度**，也不看彼此的
产出。这是 `README.md` 第 50 行 DoD 的 d 项（「以正确性/安全/一致性三个独立视角各过
一遍自己的 diff」）的落实方式——同一个人分三遍看自己的 diff 不构成三个视角，
只有互相不知情才构成。三份报告的原文是派单材料、不在仓库内；本文件是把它们
**逐条重新实测**之后的落地记录，每条的 `file:line`、每个处置状态都由本轮命令生成，
不照抄。

- 正确性：审查者 Mark，**14 条**（HIGH 3 / MEDIUM 6 / LOW 5），总体结论**「有严重
  缺陷」**。他的 3 条 HIGH 全部指向「代码会返回错的东西」而不是「代码写得不好看」：
  `Mark-1` 按 fact 文本反查行、文本重复时字典塌缩（同一对象返回两次、本会话行永远
  取不到、session 事实被误标成 `session_id=999` / `scope='global'`）；`Mark-2` 反过拟合
  自检断言**零判别力**（「答案词 ＋ 3 个填充词」即可绕过，消融后留出集 1.000→0.667
  而断言仍 8/8 PASS）；`Mark-9` 是同一族的另一例——一个测试对顺序**零判别力**
  （把 DESC 改成 ASC 也照样绿）。**14 条全部已修**，无一条驳回、无一条转闸门异议。
  他最狠的一条不是 HIGH 而是 `Mark-2`：它说的不是「实现有 bug」，而是「**你用来
  证明实现没有 bug 的那个判据是空的**」，这条直接催生了后来的 44 对反过拟合语料
  与 v2 的 32 对留出集。
- 安全：审查者 Ryan，**4 条**（HIGH 1 / MEDIUM 1 / LOW 2），总体结论同样是**「有严重
  缺陷」**。4 条里 **2 条与正确性视角合并**（`Ryan-1` = `Mark-7`、`Ryan-4` = `Mark-8`），
  这不是重复计数，是同一个缺陷在两个维度上都被独立撞到——合并行在 §统计 里被扣掉，
  所以独立条目是 66 而不是 68。Ryan 独有的两条：`Ryan-2`（MEDIUM）`rank()` 每条候选
  重复归一化 query 并重建 Counter，query 无长度上限，**100000 字符 × 500 候选实测
  72.70s，逼近闸门 120s 硬超时**——这是可用性攻击面，不是正确性问题，正确性视角
  看不见它；`Ryan-3`（LOW）模块级可变对象同进程可篡改，本轮实测发现登记册的表述
  过强（`W_*` 一行未动），已登记为 ⚠ 核实差异。**安全视角的产出量最小（4 条）但
  交叉率最高（2/4）**，说明正确性与安全在这个模块上共享同一批失败路径：能把错误
  事实喂进 prompt 的缺陷，同时就是注入面。
- 一致性：审查者 Daniel，**20 条**（HIGH 5 / MEDIUM 9 / LOW 6），总体结论**「有严重
  缺陷」**，且是三个视角里**条数最多、HIGH 最多**的一个。他的 5 条 HIGH 全部是
  「文档与代码/文档与文档互相矛盾」：`Daniel-1`（用例数「原 15 ＋ 新增 39」，实测
  基底只有 3）、`Daniel-2`（`src/memory_store.py` 缺 `main-repo-target:` 头，而四处
  文档都声称按该头映射）、`Daniel-3`（五层分工表给 L1/L2/L4 赋予判别职责，但消融
  实测四层在旧两集**零判定翻转**）、`Daniel-4`（文档头部声称的执行时间与其唯一原始
  日志**跨日矛盾**）、`Daniel-5`（同一份日志的行数在两份文档里给出两个值）。**20 条
  全部已修**，其中 `Daniel-1` 是「已修一半」（上一轮写下的新数字又过期了，见
  ⚠ 核实差异）。一致性视角的价值在于它是唯一能发现「**自证材料本身失真**」的维度
  ——正确性看代码、安全看攻击面，只有它去看「你说的和你做的是不是一回事」。
  本轮的 5 条 ⚠ 核实差异里有 **4 条**出自他的条目，而其中 3 条
  （`Daniel-1`/`Daniel-10`/`Daniel-17`）的性质是「上一轮修好了，但修的时候写下的
  新数字又过期了」，这正是本文件要加 §终态锚点 的直接原因。

**三个视角合起来的一个结构性事实**：三位审查者共提 **38 行**（Mark 14 ＋ Ryan 4 ＋
Daniel 20；其中 `Ryan-1`/`Ryan-4` 是合并行，独立 36 条），**这 38 行的处置列全部以
「已修」开头，没有一行是驳回、也没有一行转闸门异议**（两行是「已修一半」：
`Ryan-3` 与 `Daniel-1`，已在 ⚠ 核实差异里说清另一半为何修不了）。而 17 条「闸门异议」
**全部来自来源四（QA 取证 F 系列）的 9＋1 行与来源五（集成期条目）的 7 行**。也就是说：
**审查者发现的都修得动，修不动的都是取证期与集成期撞到冻结区的。** 这不是巧合——
三个视角审的都是本仓自己的 diff，而 QA 取证与集成期审的是验收体系本身，后者不在
本仓职权内。这两类缺陷的比例（38 可修 / 17 不可修）本身就是对「冻结区边界画在哪里」
的一个实测输入，已随卷宗一并交主仓裁决。

三个视角**都是「有严重缺陷」**，没有一个给出「可以合入」。按 DoD 的 d 项，这个结论
本身就是交付物的一部分：它说明层2 对抗不是走过场，三份独立报告各自都拦下了东西。

### 交叉验证：哪些发现被第二个人独立撞到

「独立」的判据是**两个人给出了同一个失败路径**，不是两个人说了同一句话。下表 9 行
是本轮逐条 grep 复核出来的（每行的落点都由命令定位，不是记忆）：

| 同一缺陷 | 正确性 | 安全 | QA 取证 | 修复后的钉住点（仓库内） |
|---|---|---|---|---|
| 重复 fact 文本导致字典塌缩 | `Mark-1` | — | `H1` | `tests/test_memory_retrieval.py:188`（用例类）、`:202` / `:213` / `:227` |
| 反过拟合判据零判别力 | `Mark-2` | — | `H2` | `tests/test_lexicon_overfit.py`（15 个用例） |
| `format_memory_prompt` 未处理换行 ＋ 零消毒 | `Mark-7` | `Ryan-1` | `H3` | `tests/test_memory_retrieval.py:234`（用例类）、`:240`（三条链的说明）、`:250` / `:265` / `:274`（反例 A/B/C）、`:283`（CR 与 TAB）、`:288`（截断）、`:295`（长度上限） |
| `_visible_facts` 无 LIMIT | `Mark-8` | `Ryan-4` | `M5` | `src/memory_store.py:53` ＋ `tests/test_memory_retrieval.py` 的 M5 段 |
| 单字 head 子串误命中 | `Mark-3` | — | `M1` | `tests/test_ranker_layers.py:236`–`:241`（**四个查询逐个 assertFalse**：`:238` 超市、`:239` 角色、`:240` 脸色、`:241` 色号）、`tests/test_lexicon_polarity.py:27` / `:41` / `:49` / `:58` / `:59`、`src/memory_ranker.py:48` |
| 极性谓词不辨方向 | `Mark-4` | — | `M2` | `tests/test_lexicon_polarity.py:101`（用例类，含「实测 `score("用户讨厌运动")=0.3921`」）、`:111`（正向）、`:117`（反向）、`:123`（三值）、`:128`（相反极性得负分）、`:133`–`:135`、`:139` |
| `bigram_similarity` 成比例时返 1.0 | `Mark-5` | — | `M3` | `tests/test_ranker_layers.py` 的 M3 契约锁定段、`src/memory_ranker.py:139` |
| 嵌套子串重复计数 | `Mark-6` | — | `M4` | `tests/test_lexicon_polarity.py:27`、`tests/test_retrieval_structure.py:39` |
| 每条候选重复归一化 query（性能） | — | `Ryan-2` | `M6` | `tests/test_ranker_layers.py` 的 M6 段、`src/memory_ranker.py:273` |

**同名不同物，必须消歧**：上表最后一行的 `M6` 是 **QA 取证的「审查发现 M6」**
（= `Ryan-2`，性能问题），而 §反 Goodhart 自证 里的 **变异路 M6** 是 `kill_l4`
（`W_PREFERENCE = 0`）。两者编号撞车、毫无关系。本文件在两处都写了这条警告。

**有一条要如实说清楚，不能顺着派单的举例写**：派单里举的第三个交叉验证例子是
「scope 谓词重复被 Mark 与 QA 各自实测到同一行号」。本轮 grep 复核的结果是
**`Mark-10`（scope SQL 谓词在 `recall()` 与 `_visible_facts()` 各手抄一遍）是单源
发现**——QA 的 F 系列与 Ryan、Daniel 的条目里都没有第二个来源撞到它。需要特别
说明的是：QA 的 `M5` 也落在 `_visible_facts()`，但报的是**无 LIMIT**（性能与安全），
不是谓词重复；**同一个函数上的两个不同缺陷不构成交叉验证**。所以 `Mark-10` 不进
上面那张表。把它写成交叉验证会是伪造：交叉验证的价值全在于「独立」，凑数会稀释掉
真正撞上的那 9 行。

### 修复后由 QA 亲手复现审查者的原始反例

「已修」不能只靠「单测变绿」证明——单测是自己写的，绿是必然。所以修复之后由 QA
**拿审查者当初的原始反例重跑一遍**，确认反例在新代码上不再成立。四条：

| 反例 | 原始来源 | QA 复现的动作 | 结果 |
|---|---|---|---|
| 重复 fact 文本 | `Mark-1` / `H1` | 构造同一 `MemoryStore` 里两条 fact 文本完全相同的行，调 `recall_relevant()` | 不再返回同一对象两次；本会话行能取到；`session_id` 与 `scope` 不再被误标。钉在 `tests/test_memory_retrieval.py:202` / `:213` / `:227` |
| 三条注入链 | `Mark-7` / `Ryan-1` / `H3` | 把审查者给的三条链原样喂进 `format_memory_prompt`（反例 A/B/C），另加 CR、TAB、超长三种变体 | 三条链全部被消毒；换行被转义；截断与长度上限生效。钉在 `tests/test_memory_retrieval.py:250` / `:265` / `:274` / `:283` / `:288` / `:295` |
| 四个误判查询 | `Mark-3` / `M1` | 「超市」「角色」「脸色」「色号」四个查询逐个跑，断言**不**被判为稳定属性提问 | 四个全部 assertFalse 通过（`tests/test_ranker_layers.py:238`–`:241`），时态降权不再反噬对题事实 |
| 双向极性 | `Mark-4` / `M2` | 正向与反向各跑一遍，并跑「相反极性」 | 正向得正分、反向不再得正分、相反极性得**负分**（`tests/test_lexicon_polarity.py:111` / `:117` / `:128`）；`_polarity_hits("用户不喜欢吃香菜") == (0, 1)`（`:133`–`:135`） |

这四条的共同点是：**复现用的输入来自审查者，不来自实现者**。实现者自己想的反例
只能证明自己想到的那部分；审查者的反例是外生的，它通过了才算「已修」有据。

---

## 反 Goodhart 自证

**先把「九路」的口径钉死，否则本节的所有数字都对不上号。** 这个项目里「九路」有
**三种互不相同的用法**（已登记为 New-2）：

| 口径 | 出处 | 「九」指什么 | 基线算不算 |
|---|---|---|---|
| 甲 | `evidence/task_b_self_sabotage.md` §3 标题「九路独立复跑的实测分数」 | baseline ＋ 8 路变异 = 9 | **算** |
| 乙 | `tests/test_ranker_mutations.py` docstring | 有牙齿 4 ＋ 无牙齿 4 = 8 路变异 | 不算（所以说的是「八路」，标题却常被引成「九路」） |
| 丙 | `evidence/task_b_gate_objections.md` 表 D「我方九路」 | M1–M9 = 9 路变异 | 不算，基线另列 |

**本节采用口径丙**，并把总数扩到 **12 路 = 1 基线 ＋ 9 路（M1–M9）＋ 2 路（N1 的
A/B 两个变异体）**。这与发现清单 `F1'` 行已写死的「12 路 / 10 PASS / 2 FAIL」是同一
组数字，两处一致。派单要求的「九路变异」是口径丙的 M1–M9，已全部覆盖，另加 3 路
（基线作对照 ＋ N1 两个变异体）。

- sabotage_drill.py 结果：3/3 检出（附 evidence 文件名：`evidence/task_b_sabotage_drill.log`
  9 行 / 397 字节，`evidence/task_b_sabotage_drill.md` 470 行 / 30919 字节）

  原始输出只有一行实质内容：`DRILLS DETECTED: 3 of 3`（log 第 6 行），退出码 0；
  log 第 3–4 行钉住了当时的 HEAD 与其 tree（两个都是内容哈希，带标签，且都已注明
  是**那一格时点**的值）。这印证了 `F12`：drill 丢弃闸门 stdout/stderr，所以 3/3
  这个数字**本身不含任何可核查的细节**，它只是三个布尔的合取。

  **3/3 这个数字的效力不是 drill 自己给的，是外部补偿控制给的**，三条，缺一条这个
  3/3 就是空的：

  1. **前置绿断言**——drill 自身**没有**「破坏前那个闸门必须是绿的」这一步
     （缺陷①，`task_b_sabotage_drill.md` §6 缺陷①）。本轮用**外部 8 闸门快照**补：
     破坏前的完整快照与破坏后逐格比对（§4、§7.B）。
  2. **恢复后复验**——drill 的「恢复后复跑 gate 验证回绿」是**死代码**（缺陷②）：
     `try` 体内三条路径全部 `return`，而 `finally` 不 `return`，所以第 38–43 行
     **永不执行**。这一点已用 **AST 静态证明**，三个判据全 True（卷宗条目 D，`:966`）。
     本轮的补偿控制是**手工复验回绿**（`task_b_sabotage_drill.md` §7）。
  3. **前后哈希逐一比对**——四个相关文件（`src/memory_ranker.py`、
     `src/memory_lexicon.py`、`src/memory_store.py`、`acceptance/gates/g1_memory.py`）
     的 blob 与内容 sha256 在每一路前后逐一比对，12 路**全部 True**，整轮跑完
     「repo bytes untouched for the whole run : True」。

  **状态改判，以及为什么改判不等于缺陷消失**：集成上游修复之后 `g0_freeze` 由恒
  FAIL 转 PASS，于是「`eval-tamper` 那一路是假阳性」的保留意见**消失**，有效检出
  由上一轮的 **2/3** 改判为本轮**真正的 3/3**（改判过程见 `task_b_sabotage_drill.md`
  §5.1→§5.2）。但**解除的理由不是 drill 变好了**：前置绿断言是本轮用外部快照补上的，
  **缺陷①仍在代码里**，`acceptance/sabotage_drill.py` 在冻结区、本仓一个字节都改不了。
  下一轮如果没人再补这个外部快照，同一个 drill 会**再次**给出一个无法核查的 3/3。
  这就是 `F1'`/条目 D 那条闸门异议的实质。

- 若自实现新闸门：破坏自己实现的哪 3 处、套件是否变红（附日志）

  **`score_retrieval()` 属于「自己实现检索、又自己给检索打分」的自评闸门**，所以这一
  项对本任务是**适用**的，不能跳过。本轮做的不是「破坏 3 处」，是 **12 路**（上表
  口径丙的 M1–M9 ＋ N1 的 A/B ＋ 基线对照），是派单要求的四倍。

  更重要的是**它不再是仓库外的一次性脚本**：其中 8 路已固化为仓库内资产
  `tests/test_ranker_mutations.py`（323 行、10 个 `def test_`），进单测、进版本控制、
  任何人 clone 下来都能重跑。这是「演练」与「资产」的区别——演练做完就没了，
  资产会一直红给你看。

  **「套件是否变红」要分两层答，混在一起会得出错误结论：**

  1. **单测套件不变红，而且这是设计要求。** 变异全部在内存里做
     （`mock.patch.object` ＋ 每路结束调 `_assert_module_restored()` 断言模块态复原），
     跑完 12 路仓库**一个字节没动**。所以「254 个单测仍全绿」不是「没检测到破坏」，
     是「破坏从未落盘」。`tests/test_ranker_mutations.py` 那 10 个用例断言的是**每一路
     的实测行为**（哪几路指标动、哪几路不动、动到多少），它们本身就是绿的，因为它们
     写的是实测值而不是期望值。
  2. **真闸门变红的只有 2 路。** 逐路调 `acceptance/gates/g1_memory.py` 的 `run()`：
     **12 路里 PASS 10 / FAIL 2 / PENDING 0**，FAIL 的是 `unsorted_rank`（M2）与
     `empty_whole_lexicon`（M4）。剩下 **10 路闸门全绿**——这 10 路里包含把留出集
     打到 0.6667 的实现。**这就是 Goodhart 敞口，实测确认，不是推论。**

  日志：本轮 12 路的原始日志是 `<scratch>/mutate12.log`（16948 字节）与
  `<scratch>/gate12.log`（5199 字节）。**这两个文件在仓库外、未入库**——本轮铁律
  只准改本文件一个，不准往 `evidence/` 里加东西，所以它们不能成为仓库内资产。
  作为补偿：① 下面那张表是它们的**完整数据转录**，读者不需要日志也能核每一个数字；
  ② 仓库内有上一轮同族的日志 `evidence/task_b_self_sabotage.log`（362 行）与
  `evidence/task_b_self_sabotage.md`（495 行，§3 九路实测分数、§4 有牙齿/无牙齿分类、
  §7 闸门敞口直接实测），口径甲；③ 8 路已固化进 `tests/test_ranker_mutations.py`，
  这是比日志更强的资产。**如实说明这个缺口，不假装日志已入库。**

### 十二路变异 × 三集 × 真闸门退出码

三集口径：**golden** = 内联在 `acceptance/gates/g1_memory.py` 里的 8 对（闸门唯一
看的东西）；**v1** = `tests/test_memory_retrieval.py` 的 `HOLDOUT_GOLDEN` 12 对
（留出集）；**v2** = `tests/holdout_v2.py` 的 `HOLDOUT_V2` 32 对（反过拟合留出集，
语料 digest 锁 ＋ 文件字节锁）。指标 = top-1 命中数 ＋ 宏平均 P/R，判定函数统一用
`tests/test_holdout_v2.py` 的 `score_holdout_v2()`，只换 `ranker` 参数（换打分函数、
口径不变）。`min_margin` 只统计有正确答案的对，`excl` 是被排除的对数。

| 路 | 变异（改了什么） | golden 8 对 | v1 12 对 | v2 32 对 | v2 宏 P / R | `g1_memory` 退出码 | golden 是否跌破 0.8 | golden min_margin |
|---|---|---|---|---|---|---:|---|---:|
| baseline | 不变异（对照） | 8/8 · 1.0000 | 12/12 · 1.0000 | 24/32 · 0.7500 | 0.7742 / 0.7500 | **0 PASS** | 否 | 0.2676 @#7 |
| M1 `kill_l3` | `W_CONCEPT = 0`（关掉概念层） | 8/8 · 1.0000 | **8/12 · 0.6667** | **21/32 · 0.6562** | 0.6774 / 0.6500 | **0 PASS** | 否 | 0.0113 @#1 |
| M2 `unsorted_rank` | `rank()` 退化为不排序（只打分，保持输入序） | **5/8 · 0.6250** | 12/12 · 1.0000 | **12/32 · 0.3750** | 0.3871 / 0.3500 | **1 FAIL** | **是** | 0.4455 @#6 |
| M3 `empty_all_members` | 清空 `CONCEPT_LEXICON` 全部 member（每类退化为 head-only） | 8/8 · 1.0000 | **8/12 · 0.6667** | **21/32 · 0.6562** | 0.6774 / 0.6500 | **0 PASS** | 否 | 0.0113 @#1 |
| M4 `empty_whole_lexicon` | 清空整个 `CONCEPT_LEXICON`（`{}`） | **6/8 · 0.7500** | **10/12 · 0.8333** | **19/32 · 0.5938** | 0.6129 / 0.5833 | **1 FAIL** | **是** | 0.0613 @#1 |
| M5 `kill_l5` | `W_TRANSIENT = 0`（关掉时态降权） | 8/8 · 1.0000 | 12/12 · 1.0000 | 24/32 · 0.7500 | 0.7742 / 0.7500 | **0 PASS** | 否 | 0.0926 @#7 |
| M6 `kill_l4` | `W_PREFERENCE = 0`（关掉偏好极性层） | 8/8 · 1.0000 | 12/12 · 1.0000 | **22/32 · 0.6875** | 0.7097 / 0.6833 | **0 PASS** | 否 | 0.2176 @#7 |
| M7 `naive_concept_parts` | `_concept_hit_parts` 退回朴素子串计数（head/member 各数一遍，无最长优先掩码） | 8/8 · 1.0000 | 12/12 · 1.0000 | 24/32 · 0.7500 | 0.7742 / 0.7500 | **0 PASS** | 否 | 0.2676 @#7 |
| M8 `naive_concept_hits` | **假演练实证**：改打 `_concept_hits`——它已不在打分路径上 | 8/8 · 1.0000 | 12/12 · 1.0000 | 24/32 · 0.7500 | 0.7742 / 0.7500 | **0 PASS** | 否 | 0.2676 @#7 |
| M9 `split_polarity` | `_polarity_hits` 退回两组独立计数（否定辖域丢失） | 8/8 · 1.0000 | 12/12 · 1.0000 | 24/32 · 0.7500 | 0.7742 / 0.7500 | **0 PASS** | 否 | 0.2363 @#1 |
| N1-A `n1_color_singles` | 只删颜色类 15 个单字 member | 8/8 · 1.0000 | 12/12 · 1.0000 | 24/32 · 0.7500 | 0.7742 / 0.7500 | **0 PASS** | 否 | 0.2676 @#7 |
| N1-B `n1_all_singles` | 删全词典 28 个单字 member | 8/8 · 1.0000 | **10/12 · 0.8333** | **23/32 · 0.7188** | 0.7419 / 0.7167 | **0 PASS** | 否 | 0.0671 @#4 |

合计：**12 路，PASS 10 / FAIL 2 / PENDING 0**。每一路都另有三项独立校验，12/12 全过：
① `module state restored after patch exit : True`；② `blob hashes unchanged : True`；
③ `CROSS-CHECK independent impl vs official scorer: AGREE (<1e-12)`——独立实现与官方
评分器逐位一致，说明上表的数字不是某一实现的自说自话（这条同时是 `F20` 第二个缺陷
「未显式传 ranker 导致假 DIVERGE」修正版的复跑验证：本轮**零 DIVERGE**）。

两个安全余量的额外读数（不在上表里，但下一个人需要知道）：

- **M5（关掉时态降权）三集的 acc/P/R 与基线逐位相同**，只有余量动了：golden
  0.2676 → 0.0926、v2 的 min_margin 从 0.0067 @#5 变成 **0.0023 @#0**。也就是说
  这一层的全部价值是**余量**，不是**判定**——`self_sabotage.md` §5 有专节，本轮
  复核其数字仍然成立。
- **M6（关掉偏好极性层）把 v1 的最小余量打到 0.0000 @#5**（基线 0.0500），
  同时 v2 从 24 掉到 22。这条是 Nick 本轮修正的对象，见下。
- **N1-A 是最彻底的一路：连 min_margin 都与基线逐位相同**（golden 0.2676 @#7 /
  v1 0.0500 @#5 / v2 0.0067 @#5）。颜色类那 15 个单字 member 在三集上**完全不可
  观测**，v2 #29「藏青色」仍命中是因为 `_masked_scan` 最长优先取到了长词「藏青」。
  这一路的存在意义不是「证明它无害」，是**证明演练本身可能有假阳性**——改了代码、
  什么都没变，如果不做交叉校验就会误以为「这一层没被用到」。

### 「无牙齿」要分两档，混成一档会写出伪造的红灯

「有牙齿」在本项目有**两个不同的判据**，判出来的路数不一样，必须分开说：

| 判据 | 定义 | 有牙齿的路 | 路数 |
|---|---|---|---:|
| 判据甲（单测口径乙用的） | **任一**评测集的指标动了 | M1、M2、M3、M4（＋ M6、N1-B 在 v2 上也动了，但 `tests/test_ranker_mutations.py` 的 docstring 只断言 golden 与 v1 两集，所以没把它们算进去） | 4（两集口径） |
| 判据乙（闸门口径） | **golden 的 P/R 跌破 0.8**，从而 `g1_memory` 退出码变 1 | **只有 M2、M4** | **2** |

判据乙才是「验收会不会拦下它」的判据，因为 `g1_memory` **只看 golden 那 8 对**。
按判据乙，**12 路里只有 2 路有牙齿**。

「无牙齿」再分两档：

- **第一档：三集全不动（完全零可观测性）**——M7、M8、M9、N1-A。其中 **M8 是故意
  设计的假演练实证**（打的是一个已不在打分路径上的函数，用来证明「演练可能什么都没
  破坏」这种假阳性真实存在），M7/M9 是 `Mark-4`/`Mark-6` 两个缺陷的复现路——它们
  三集不动说明**这两个缺陷的修复在三集上不可观测**，钉住它们靠的是
  `tests/test_lexicon_polarity.py` 的层内断言，不是指标。
- **第二档：golden 不动、留出集动（对闸门无牙齿、对单测有牙齿）**——M1、M3
  （v1 12→8、v2 24→21）、M5（三集不动但余量崩）、M6（v2 24→22、v1 余量归零）、
  N1-B（v1 12→10、v2 24→23）。

**对这 10 路，把指标断言写成「跌破 0.8」会是伪造的红灯。** `tests/test_ranker_mutations.py`
的 docstring 把这句话写成了纪律（口径乙原文：「对它们只断言层内行为确实消失，
**不许**断言指标跌破 0.8，因为那是实测为假的期望」）。一个写死的假红灯比没有测试
更坏：它训练所有人「这个测试红是正常的」，等真红灯来的时候没人看。

### 最有力的那一条结论

**`empty_all_members`（M3）与 `kill_l3`（M1）两路下：golden 仍 8/8 = 1.0000，而 v1
掉到 0.6667、v2 掉到 21/32（宏 P 0.6774 / R 0.6500）；`g1_memory` 退出码仍为 0、
`problems = []`、`pending = []`。**

⇒ **一个 golden 满分的过拟合实现能通过全部 8 个验收闸门。这是实测确认，不是推论。**

「全部 8 个」的依据：`g1_memory` 是唯一一个看检索质量的闸门，它 PASS；其余 7 个
闸门与检索质量无关（环境/冻结/密钥/契约/权限/工具/仿真），本轮完整快照
`0/0/0/0/0/2/2/0`（两个 2 是恒 PENDING，与变异无关，基线也是这个值）。

根因两条，都是结构性的：

1. **闸门只 import 内联的 GOLDEN 那 8 对，从不看 44 对反过拟合语料，也不看 v1/v2。**
   所以「只对那 8 对有效」的实现在闸门眼里与真正正确的实现**不可区分**。
2. **`acceptance/run_all.py` 的 `GATES` 不含 unittest。** ⇒ **钉住过拟合的三道棘轮
   （`tests/test_lexicon_overfit.py` 15 个用例、`tests/test_holdout_v2.py` 的 v2 三条
   棘轮、`tests/test_ranker_mutations.py` 10 个用例）全部在单测侧，而验收闸门一条都
   看不见。** 单测是 254 全绿，但 `run_all.py` 根本不跑它。

这两条已作为闸门异议提交主仓：卷宗条目 10（`:703`，`GATES` 不含单测）、条目 11
（`:732`，留出集不进闸门）、条目 12（`:747`，清空词典后闸门仍 PASS 的实测证据）、
条目 14（`:807`，建议的裁决方向）。本文件补的是**把实测从 4 路扩到 12 路**，以及
把「10 路闸门全绿」这个数从推论变成日志。

**给下一个人的操作性结论**：如果你想让闸门真的能拦住过拟合，最小的改动是把
`g1_memory.py` 的语料从内联 8 对换成「8 对 ＋ v1 12 对 ＋ v2 32 对」，并把判据从
「golden P/R ≥ 0.8」改成「三集各自 ≥ 各自阈值」。但 `acceptance/` 在冻结区，本仓
改不了，所以这条只能作为裁决建议存在。**在那之前，任何人声称「8 闸门全 PASS 所以
检索是对的」，这句话在本仓是错的**——本节 12 路里有 10 路是反例。

### M6 的修正（Nick 本轮提出，本节如实登记为己方发现）

**发现**：`tests/test_ranker_mutations.py` 把 M6（`W_PREFERENCE = 0`）归入「无牙齿」，
但那条用例 `test_killing_l4_keeps_metrics_but_collapses_the_safety_margin`（`:200`）
**只断言 golden 与 v1 两集**——它调了 `_top1_hits(GOLDEN)` 与 `_top1_hits(HOLDOUT_GOLDEN)`，
**没有调文件里已经存在的 `_v2_hit_count()`（`:74`）**。那个辅助函数目前只在 `:287`、
`:294`、`:303`、`:318` 被调用，四处全属于 N1 的两个变异体用例。

**加上 v2 之后，这一路按判据甲是有牙齿的：24 → 22**（宏 P 0.7742 → 0.7097、
R 0.7500 → 0.6833）。本轮实测，数据在上表 M6 行。

**这不是矛盾，是原判定的适用范围只到两集。** docstring 那句「这 4 路在两个评测集上
都保持满分」在它自己声明的范围内是**真的**；错的只是读者容易把「两个评测集」当成
「全部评测集」。按判据乙（闸门口径）M6 仍然无牙齿——golden 一动没动，退出码仍 0。

**处置**（本轮铁律禁改 `tests/`，所以只能登记，不能自己修）：

1. **首选：修 docstring 的适用范围**——把「无牙齿（4 路）」那一段改成明确写
   「在 golden 与 v1 两集上无牙齿；M6 在 v2 上会从 24 掉到 22」。零风险，不动断言。
2. **并且：给 M6 用例补 v2 断言**——加一行 `self.assertEqual(_v2_hit_count(), 22)`，
   把 v2 的 22 钉成棘轮。风险是它会让 M6 用例依赖 v2 语料，而 v2 有 digest 锁，
   语料一动这条断言就红——**这正是想要的效果**，但要和 v2 那三条余量为 0 的棘轮
   （`F17`）放在一起看：v2 已经很紧了，再加一条会让「任何 v2 改动」都要过四道关。
3. **不建议**：把 M6 从「无牙齿」移到「有牙齿」而不写清判据。那会让口径乙的
   「有牙齿 4 路」变成 5 路，而按判据乙它其实是 2 路——两个判据混用是本节开头
   花一整段钉口径的原因。

登记为己方发现，编号 **New-6**（严重度 LOW：不影响任何交付物的正确性，影响的是一份
仓库内资产的表述精度）。

### 对上游那版任务 B 的独立复核（供主仓参考）

**口径声明，写在最前面**：这一小节是**对上游实现的独立复核发现，供主仓参考**，
不是「我们比他们好」的比较结论。上游宣称的 golden P/R = 1.0 **属实且可复现**——
本轮在上游 clone 上实测复现了它。问题不在他们的诚实度，在**评测体系的判别力**；
这与本仓 `F1'`/`F3'`/`F9'` 是**同一条闸门异议**，只是他们的评测体系里连 v2 那一层
都还没有。

背景（New-5）：上游那 6 格是本轮**并行 fetch** 进来的，本仓 HEAD 里没有他们的代码。
其中任务 B 那一格的 subject 是 `feat(task-B): lexical Chinese retriever with char
n-gram IDF + attribute query expansion; golden precision/recall 1.0`（按时间序是上游
基线之后第 3 格；引用它用 subject，不用 hash，同一套纪律）。所有测量都在仓库外的
上游 clone（`<tmp>/upstream-eval`）上做，变异实验做在它的**副本**
（`<tmp>/upstream-eval-u4`）上，原 clone 一个字节没改；真仓库工作树全程只有本文件
一个未跟踪项，每一步都复核过 `git status --porcelain -uall`。

**1. 他们的满分是真话。** golden 8 对：top-1 命中 **8/8**、acc 1.0000、宏 P 1.0000、
宏 R 1.0000；他们自己的 `score_retrieval(GOLDEN)` 给 precision 1.0 / recall 1.0，
8 对逐条 `missed=[]`、`false_positives=[]`。**可复现，无保留意见。**

**2. 同一口径下的三集对比**（口径 = 我方 `tests/test_holdout_v2.py` 的
`score_holdout_v2()` 判定 top-1，只把 `ranker` 参数换成各家实现；对照组是「恒返回
`stored[0]`」的平凡打分器，用来量每个集**本身**的判别力）：

| 集 | 对数 | 上游 | 我方 | 平凡对照组 |
|---|---:|---|---|---|
| golden | 8 | 8/8 · P 1.0000 · R 1.0000 | 8/8 · P 1.0000 · R 1.0000 | 5/8 · 0.6250 |
| v1（留出集） | 12 | 12/12 · P 1.0000 · R 1.0000 | 12/12 · P 1.0000 · R 1.0000 | **12/12 · P 1.0000 · R 1.0000** |
| v2（反过拟合留出集） | 32 | **21/32** · acc 0.6562 · P 0.6774 · R 0.6500 | **24/32** · acc 0.7500 · P 0.7742 · R 0.7500 | 12/32 · acc 0.3750 · P 0.3871 · R 0.3500 |
| 上游自带 HELD_OUT | 4 | 4/4 · P 1.0000 · R 1.0000 | 3/4 | **4/4 · P 1.0000 · R 1.0000** |

（上游 v2 的 P/R 分母是 Pn=31、Rn=30，因为 32 对里有 1 对 relevant 为空、2 对无法计
recall；我方同口径同分母，所以两个 P/R 可直接比。）

**3. v1 那 12 对对排序零判别力，两边的 v1 满分都是空的。** 平凡对照组在 v1 上拿
**12/12 满分**，因为 v1 的 relevant 首次下标**全为 0**（实测 12 个 0）。所以「上游
v1 = 1.0000」与「我方 v1 = 1.0000」这两句话**都不含任何关于排序能力的信息**。
golden 也有一大半是这个性质：首次下标 `[0,1,0,0,1,0,0,2]`，**5/8 在 `stored[0]`**，
所以对照组能拿 5/8。**这正是必须造 v2 的理由**：v2 的 32 对里只有 12 对的 relevant
首次下标为 0，另有 2 对 relevant 为空（记 `-1`），于是对照组掉到 12/32，
判别力才出现。

**4. 最关键的一条，本轮亲手复现（不是引用别人的结论）。** 把上游
`retrieve_relevant()` 里的 `sorted(...)` 整句删掉、退化成按 `stored` 原序返回
（改动只有一行：`for score, i in sorted(scores, key=lambda pair: (-pair[0], pair[1]))`
→ `for score, i in scores`），在副本上实测：

| 检查项 | 变异前（原 clone） | 变异后（副本） |
|---|---|---|
| golden top-1 | 8/8 · P 1.0000 · R 1.0000 | 8/8 · P 1.0000 · R 1.0000 |
| 上游自带 HELD_OUT top-1 | 4/4 · P 1.0000 · R 1.0000 | 4/4 · P 1.0000 · R 1.0000 |
| v1 top-1 | 12/12 · P 1.0000 · R 1.0000 | 12/12 · P 1.0000 · R 1.0000 |
| v2 top-1 | 21/32 · P 0.6774 · R 0.6500 | 21/32 · P 0.6774 · R 0.6500 |
| 上游自评 `score_retrieval(GOLDEN)` | precision 1.0 / recall 1.0 | precision 1.0 / recall 1.0 |
| 上游自评 `score_retrieval(HELD_OUT)` | precision 1.0 / recall 1.0 | precision 1.0 / recall 1.0 |
| 上游 8 闸门退出码 | `0/0/0/0/0/0/0/0` | `0/0/0/0/0/0/0/0` |
| 上游单测 | `Ran 25 tests` · OK | `Ran 25 tests` · OK |
| `acceptance/run_all.py --strict` | `VERDICT: PASS` · 退出码 0 | `VERDICT: PASS` · 退出码 0 |

四集那部分的两次完整输出**除「上游根目录」与「锚点出现次数」两行外逐字节相同**
（`diff` 退出码 **0**）。日志：`<scratch>/u4_pristine.log`、`<scratch>/u4_mutated.log`
（都在仓库外、未入库，理由同上一小节；表中数字是它们的完整转录）。

⇒ **一个排序完全失效的检索器能通过他们的全部验收关卡。**

机制：他们平分时靠**下标升序**决胜（上游 `src/memory_store.py:209`：
`for score, i in sorted(scores, key=lambda pair: (-pair[0], pair[1]))`），而他们自己的
HELD_OUT 4 对的正确答案**恒在 `stored[0]`**（relevant 首次下标 `[0,0,0,0]`、
stored 长度 `[2,2,2,2]`）。所以「排序」与「不排序」在这两个集上**不可区分**——
决胜规则本身就把答案送到了第一位。这与本仓 M2（`unsorted_rank`）在**我们**这边
让 golden 从 8/8 掉到 5/8 形成对照：同一个变异，他们的集看不出、我们的 golden
看得出 3 对、v2 看得出 12 对。**差别不在实现，在语料。**

**5. 另一条：把他们的 bigram IDF 整条支路清零，三集也一字不动**（8/12/21）。
本轮复跑 Nick 的对照脚本（`<scratch>/t24_adapt_upstream.py`，EXIT=0、127 行输出、
stderr 0 字节）复现了它的表 D。⇒ 那条支路在他们的评测体系里同样是**零判别力的
装饰**。表 D 里我方 M5–M9 那几路在上游**无同构物**（记 N/A）——**那不是「无牙齿」，
是根本没有这个机制**，两种「测不出来」必须分开写。

**6. 两套实现是互补而非包含。** 同一次复跑的表 B / 表 C：v2 上**共同命中 19/32**；
**仅上游命中** `[21, 22]`；**仅我方命中** `[0, 7, 8, 14, 15]`。按维度：

| 维度 | 上游 | 我方 | 谁赢 |
|---|---:|---:|---|
| D1 | 3/4 | 4/4 | 我方 |
| D2 | 2/2 | 2/2 | 平 |
| D3（极性） | 1/2 | 2/2 | 我方 |
| D4（极性） | 1/2 | 2/2 | 我方 |
| D5 | 4/4 | 4/4 | 平 |
| D6（高字面重叠干扰） | **1/4** | **3/4** | 我方 |
| D7（零字面重叠） | **3/5** | **1/5** | **上游** |
| D8 | 2/3 | 2/3 | 平 |
| D9 | 3/3 | 3/3 | 平 |
| D10 | 0/0 | 0/0 | 平 |
| D11 | 1/1 | 1/1 | 平 |

上游在 **D7（零字面重叠）** 上 3/5 赢我方 1/5，靠的是硬编码的 `_EXPANSION`
（属性查询扩展表）；我方在 **D6（高字面重叠干扰）** 上 3/4 赢他们 1/4、
**D3/D4（极性）** 各 2/2 赢他们各 1/2。**谁都不包含谁。** 主仓如果要合，
D7 那张扩展表与 D6/D3/D4 那套极性＋最长优先掩码机制是**可以叠加的**，不是二选一。

**7. 顺带一条对主仓有用的观察。** 我方 8 闸门是 `0/0/0/0/0/2/2/0`，两个 2 是
`g1_permissions` 与 `g1_tools` 恒 PENDING；上游那 6 格里有两格的 subject 明写
「harden `g1_permissions` into behavioral gate」与「harden `g1_tools` into behavioral
gate」。实测：这两个闸门文件我方与上游的 **blob 不同**（我方 `31ab51c6df85…` /
`af0c955c49d8…`，上游 `bb179702c1fb…` / `633b945b0cc5…`，四个都是 **blob 哈希**、
不是 commit），且上游 8 闸门**全 PASS**；而我方 `acceptance/gates/g1_memory.py` 与
`acceptance/run_all.py` 与上游**逐字节相同**（同一 blob）。⇒ 两条结论：
**① 本仓 `F1'`/`F3'`/`F9'` 那条闸门异议针对的就是上游正在用的同一个文件**，异议
不因为集成而失效；**② 集成上游那 6 格会顺带把我方两个恒 PENDING 的闸门补齐。**

**8. 这一节的边界，必须写死。** 以上所有结论只针对**评测体系的判别力**，不构成对
上游实现质量的负面判断。他们的代码在他们的评测集上是**真满分**；我们的 v2 是一个
他们没见过的盲测集，用它去量任何人都能量出低于 1.0 的数——**包括我们自己**
（我方 v2 也只有 24/32，宏 P 0.7742、R 0.7500，且 `F17` 已登记 v2 三条棘轮里两条
余量为 0）。这一节真正说的是：「**8 对 golden 不足以判别任何实现，包括我们的**」。
谁把它读成「我们赢了」，谁就读反了。

### 提交前手工扫描

**为什么要手工扫描**：`g0_secrets.py` 的 `SCAN_DIRS` 是 `src/`、`acceptance/`、
`tasks/`、`docs/`、`vendor/`，**不含 `evidence/`**——本文件与卷宗所在的目录，密钥
闸门**根本不扫**（卷宗条目 22 的盲区之一）。补偿控制就是这一节：用仓库外的
`<scratch>/scan_precommit.py`（17 条泄漏类探针 P01–P17 ＋ 2 条哈希类探针）手工扫。

**探针集为什么不能照抄闸门那四个 needle**：`g0_environment.py` 第 44 行的路径
needle 有**双重转义**缺陷（发现清单「双重转义」那条），4 个路径 needle 里 **2 个
实际不工作**，常规盘符硬编码路径会漏检；再加上第 45 行对 `acceptance/` 的整体豁免。
照抄它就会继承它的漏检。所以本仓侧自补了闸门根本不管的模式：Linux 家目录前缀、
macOS 每用户临时目录前缀、本地登录名（带词边界）、仓库绝对路径（P01/P02/P05/P06/
P07/P08 一组）。

**本轮扫描结果**（收敛后那一轮；**探针字面样式一律不印出**，命中令牌一律记号化，
理由见 `F21`）：

| 目标 | 行数 | 泄漏类命中 | 收紧判据下的 commit 类 |
|---|---:|---:|---:|
| `evidence/task_b_gate_objections.md`（已入库定稿） | 1780 | 12 | 0 |
| `evidence/ADVERSARIAL_REVIEW.md`（本文件） | 1100 | 1 | 2 |
| `src/memory_store.py` | 260 | 0 | 0 |
| `<scratch>/commit6_msg.txt`（序数 45 的 message） | 65 | 0 | 0 |
| `<scratch>/commit7_msg.txt`（本格的 message，已定稿） | 61 | 0 | 0 |
| **合计** | | **13** | **2** |

扫描器退出码 = **1**（退出条件就是「泄漏类合计 > 0」，逐条裁定见下）。**扫描器的目标集其实有 6 项**，第 6 项是再下一格的 message 文件（`<scratch>/commit8_msg.txt`）；本批到本格为止没有第 8 格，所以报告里那一行印的是「缺」，**不计入上表也不计入合计**——上表 5 行与合计都是按在盘的 5 个目标算的。

逐条核对本文件自己的要求：

- **真实绝对路径 = 0**（本文件）。全文只用记号：`<repo>`、
  `<scratch>`、`<tmp>`、`<home-prefix>/`、`<win-drive>:\`、`<linux-home-prefix>/`，
  与卷宗第 20–32 行的原始定义同一套。
- **密钥样式串 = 1**（本文件，P09–P16 全组）——**没有一处真的是密钥**：
  它是 P09 对任务标识符的子串误命中（结构见 New-7，此处同样不贴字面，
  贴了就新增命中），**语义上的密钥样式串是 0**。
- **那枚已被要求吊销的 GitHub PAT：P12 命中 0 处**（两种前缀样式都扫）。
  这一条单独列出来，因为它是本项目唯一一枚真实存在过、且已被要求吊销的凭据。
  **本文件不写出它的前缀字面量**——写出来就是 `F21`。
- **上游 author 个人邮箱形态：P17 命中 0 处。** 本文件唯一需要提到提交身份的
  地方（§终态锚点 的验全表输出）已把邮箱记号化。
- **AI 套话 = 0**：这一项扫描器不管，靠人工。判据是「删掉这句话信息量是否减少」；
  本文件逐段过了一遍，凡是不通过这一判据的句子都删了。

**卷宗那 12 处命中的完整裁定**（这是对第 262 行「卷宗里有 6 处命中」那句
的补全，即 New-4）：

| 探针 | 命中数 | 行号 | 性质裁定 |
|---|---:|---|---|
| P07（本地登录名，带词边界） | 6 | `28`、`1105`、`1117`、`1127`、`1695`、`1771` | **误命中。** 命中的是本仓自己的**消毒记号**——那个 macOS 每用户临时目录前缀记号，不是真实路径。根因：P07 的词边界字符类只排除字母数字与下划线，**不排除连字符与尖括号**，于是记号字面里那段登录名被判成独立词。修法是把词边界类扩到排除 `-`/`<`/`>`；探针在仓库外脚本里，本轮铁律禁改其它文件，故只登记（New-4）。**本文件因此不写那个记号的字面**，只用中文描述它 |
| P09（厂商 API key 前缀，两种样式） | 5 | `1129`、`1130`、`1141`、`1696`、`1697` | **真正的 F21 型自指展示。** 卷宗为了论证「密钥闸门扫不到 `evidence/`」而必须展示被扫的形态；展示即命中 |
| P10（赋值形式的凭据关键字） | 1 | `1141` | 同上，与 P09 有一行重叠 |
| P09（同一探针，但命中在**本文件**） | 1 | `724` | **误命中，机制与卷宗那 5 处完全不同。** 卷宗那几处是把探针正则的字面写进文档（真 F21）；本文件这 1 处是**逐字引用上游 commit subject**——subject 里含任务标识符，而任务标识符的后半正好是那个前缀（结构描述见 New-7，此处不贴字面，贴了就新增命中）。自己的概述性提及已全部改成中文，命中从 4 压到这 1 处 |

所以第 262 行说的「6 处」= P09 的 5 处 ＋ P10 的 1 处，**对那个子集是
正确的**；但卷宗泄漏类**总数是 12**，另 6 处是探针误命中。本文件
不回改第 262 行——那句话在其上下文里指的正是「为了证明不含某形态而必须展示该形态」
那一类，语义上就是 P09＋P10；在此补全总数与逐条裁定。

**哈希类（Nick 的收紧判据，即 Nick-N4）**：判据 = 命中串必须 `git cat-file -e`
存在**且** `git cat-file -t` 为 `commit`；十进制小数不算、blob/tree 不算、内容
sha256 不算。本文件 40 位十六进制串出现 **10** 次 / 去重 **7** 个 → 按类型 **tree 3、blob 2、commit 2**；7 位短串 **0** 次；**扫描器不探的两档短串在此手工补齐**（兑现开头第 16 行那句话）：12 位短串 **6** 次 / 去重 **5** 个——第 294、295 行那 2 次是同一个串，就地标签「author 改写前的旧 HEAD，短串仅作定位、已失效」；第 819–820 行那 4 次是两个闸门文件的我方 blob 与上游 blob，就地标签「blob 哈希」；8 位短串 **3** 次——第 295 行 2 次（`ORIG_HEAD` 与 author 改写前的 HEAD，均已注明失效）、第 1028 行 1 次（序数 46 的 tree，由所在表格的行名标注）。**这两档一律不指代本仓的某一格**；十进制小数形态（会被朴素判据误命中）**1** 处，按收紧判据已全部排除；其中按收紧判据算作 commit 的 = **2 个**，
逐个裁定：**两个都不是「用 hash 指代本仓的某一格」**：① 改写前的 `ORIG_HEAD` 值，在 `Nick-N2` 那行，已注明改写后失效、只作历史记录；② **上游基线**，在 §终态锚点 与全文所有 count / diff 口径里作左端点，它不在本仓三次改写的任何范围内，是永久有效的锚点，本文件用它而不用移动引用 `origin/main`。另 tree 3 个是序数 44 / 45 / 46 的时点主锚点（§终态锚点），blob 2 个在 `Daniel-2` 那段、已就地标注「内容哈希，非 commit」；1 处十进制小数是评测输出里的长浮点，按 Nick-N4 的收紧判据排除。全部 7 个串逐个带类别标签，无一裸奔

**收敛判定**：**已按「连跑多轮 ＋ 归一化 diff」验证，不是单轮为 0 就宣布收敛。** 本轮在 scratch 里连跑四轮扫描报告（`<scratch>/scan_ra.log`、`scan_rb.log`、`scan_rc.log`、`scan_rd.log`，第一轮在批量回填（33 个不同占位符、共 43 处）之前、后三轮在之后），四轮两两 `diff`（去掉首行时间戳）在**归一化后逐字相同**（退出码 **0**）。归一化只做一件事：屏蔽报告里「按类型 {…}」那一行的**键值对打印顺序**——那是扫描器把 Python dict 直接字符串化的结果，而 Python 对字符串的哈希每个进程都随机化，于是同一份文档在不同轮次里这一行的三个键会以不同顺序出现。**这不是文档变了**：四轮排序后的键值对完全一致（blob 2、commit 2、tree 3），四轮的所有计数也完全一致。另把哈希种子固定（`PYTHONHASHSEED=0`）连跑两轮（`<scratch>/scan_se0a.log`、`scan_se0b.log`），**去掉时间戳行后逐字节相同**（退出码 **0**）——这就把「唯一的轮间不稳定来源是扫描器自己的 dict 打印顺序」从推断变成了实测。**本段自己写完之后又连跑了两轮**（`<scratch>/scan_re.log`、`scan_rf.log`）作为不动点验证：它们与前面四轮在归一化后同样逐字相同，也就是「写下这段结论」这个动作没有改变任何命中。**此后每改本文件一次就重复同一动作**（改一次 → 连跑两轮 → 归一化比对），本轮最后一次等行补正之后又这样跑了一对，结论相同。**那一对日志的文件名不写在这里**：写它就得再改一次本文件、再跑两轮，序号永远追不上——这与 `F21` 定的「不用轮次序号」是同一条理由，也是 §终态锚点 讲的自指环在扫描这件事上的具体形态。**终止条件是可判的、且不依赖序号**：① 最后一对日志与它之前那一对归一化后逐字相同；② 最后一次改动是等行的（总行数不变）且不引入新的十六进制串与探针形态。这两条都由命令断言，不由人声明。

**如实说明一处判据偏离，不用「已收敛」这个词含糊过去。** `F21` 定的收敛判据是
「最后连续两轮除时间戳行外逐字相同、**且两轮退出码均为 0**」。本轮**退出码不可能
是 0**：扫描器的逻辑是「泄漏类合计 > 0 则退出码 1」，而合计里那 6 处真
F21 命中位于**已入库定稿的卷宗**，本轮铁律禁改其它 evidence 文件，所以它们只能留在
那里。**这不是「没收敛」，是「判据的后一半在本轮不可满足」。** 本轮实际采用的收敛
判据是三条：① 最后连续两轮报告除时间戳行外**逐字相同**（`diff` 退出码 0）；
② **本文件自身**的泄漏类命中已降到 **1** 处，且该处逐条裁定为探针
误命中（P09 无词边界，New-7），语义上的真实泄漏为 **0**；③ 命中集合（探针 ×
文件 × 行号）逐轮不变。**回填这批占位符的动作本身也遵守不动点原则**，所以「收敛」不是靠「不再改文档」换来的：全部等行替换（总行数 1100 → 1100，因为文档里有对自身行号的自引用，见开头第 4 行），只写入十进制计数、行号与报告文件名，不引入任何新的十六进制串、不引入任何探针触发形态。回填后重扫，本文件的 40 位十六进制串仍是 **10** 次 / 去重 **7** 个、泄漏类仍是 **1** 处，与回填前逐字一致——即改动本身可证明不改变命中集合。

---

## 终态锚点

**这一节超出模板。加它的理由**（文件开头第 4 行承诺过，此处兑现）：本文件是这一批
的**最后一格 commit**，于是它落入一个自指环——它想记录的「终态」恰好会被它自己的
入库动作改变。任何写在它里面的「最终 commit 数 / 最终 tracked 文件数 / 最终 tree 哈希 /
`run_*.json` 计数」都在写下的那一刻就过期了。前五节记的都是**已经定死的事实**（谁的
哪条发现、哪一路变异打出什么分），只有「终态」这件事没有落点，所以单开一节，把
**哪些量能引、哪些不能引**一次说清，环就断了：读者不必再去猜某个数字是不是终态值，
因为本节把所有量分成了三类，并给出把时点量换算成当前值的命令。

### 三类量

**第一类：不变量。可以放心引用，任何时点复测都是同一个值。**

| 量 | 值 | 为什么不变 |
|---|---|---|
| 8 闸门退出码 | `0/0/0/0/0/2/2/0` | 两个 2 是 `g1_permissions` 与 `g1_tools` 的**恒 PENDING**，由闸门自身设计决定，与工作树内容无关；其余 6 个在本批所有格上都实测为 0 |
| 单测总数与结果 | `Ran 254 tests` · `OK` | 本文件是 `evidence/` 下的文档，不进 `tests/`，不影响用例数（用例数从 252 到 254 的那次变化发生在序数 39，早已定稿） |
| 5 个冻结件 sha256 与 `acceptance/MANIFEST.json` 的匹配关系 | `5/5 MATCH` | 冻结区在本批全程零触碰（§范围 有两条独立证据：端到端 diff 为空 ＋ 逐格累加为 0） |
| golden 集指标 | 8/8 · P 1.0000 · R 1.0000 | 语料内联在 `acceptance/gates/g1_memory.py`（冻结区），实现在 `src/memory_ranker.py`，两者本批之后都没再动 |
| v1（留出集）指标 | 12/12 · P 1.0000 · R 1.0000 | 同上 |
| v2（反过拟合留出集）指标 | 24/32 · acc 0.7500 · 宏 P 0.7742 · R 0.7500 | 同上 |
| v2 语料数据 digest | `201970d578e6760890c30ce7094c8c9c3cbcebe4d7f47663e2de39b9423490da` | 32 对语料的 sha256（对 `json.dumps(..., sort_keys=True)` 的结果取哈希），数据锁 ＋ 文件字节锁双保险 |
| v1 语料数据 digest | `561f17ba423dfa024ba9a940632e5d6a8399ea5638ec5b56119e72c6c9b72619` | 同上，12 对 |
| `src/memory_store.py` 内容 sha256 | `3faf8d3fe0ba5a5a11dc034fb7e92ce6fefb492b08e1b147a660b53198e6f962` | 260 行；序数 45 补头之后就没再动 |
| 冻结区端到端 diff | 空 | `git diff --name-only <上游基线 commit>..HEAD -- vendor acceptance tasks tests/test_workbench.py .gitattributes` 输出 0 行 |

（以上 4 个 64 位十六进制串都是**内容 sha256**，不是 git 对象名，也不是 commit。）

**第二类：时点锚点。值是死的、永久可核，但只在标注的那个格上成立。**

| 锚点 | 值 | 类型 |
|---|---|---|
| 序数 44 时点主锚点（Nick 固化的那个） | `1ceaf1df5cf6c5bdca262f48efa5f42085cd408b` | **tree** |
| 序数 45 时点 | `0cec2d49ffc9a13db5b809928a0d24240a6ac08e` | **tree** |
| 序数 46 时点（本文件**开始写**时的 HEAD） | `4a2a8b991e62ea22efb51394ffe0a9bb424a7dfa` | **tree** |
| 上游基线（所有 count/diff 口径的左端点） | `10c05d116e58886f3a9366c99cbdc214e9bdfae4` | **commit**（永久有效：它不在本仓三次历史改写的任何范围内） |

三个 tree 哈希是**长期锚点**——tree 只由内容决定，reword / rebase / author 改写都不会
改它。这正是本文件「用 subject ＋ 序数指代 commit、用 tree/blob 指代内容」这条纪律的
技术根据：commit 哈希在本仓已经失效过三次，tree 一次都没有。

**第三类：时点量。会随每一格 commit 改变，本文件写下的值必然过期，只能配命令读。**

`count`（`<上游基线 commit>..HEAD`）、`tracked`、`tree`、`cd_uniq`、`status`、
`run_*.json` 计数、`behind`、`ahead`、`diff --stat`。

### 一条命令验全表

复现指令（脚本在仓库外的 `<scratch>/verify_all.sh`，只读、不改任何东西；下面把 19 个
量各自的取值命令列全，读者不必依赖那个脚本也能逐条重跑）。在 `<repo>` 目录下：

```
B=10c05d116e58886f3a9366c99cbdc214e9bdfae4      # 上游基线 commit
P=./.venv/bin/python                            # 3.14.7

git rev-list --count $B..HEAD                                        # count
git log -1 --format='%s'                                             # HEAD_subject
git rev-parse 'HEAD^{tree}'                                          # tree
git log -1 --format='%an <%ae>'                                      # author
git log -1 --format='%cn <%ce>'                                      # committer
git log $B..HEAD --format='%an <%ae>' | sort -u | wc -l               # author_uniq
shasum -a 256 evidence/task_b_gate_objections.md | cut -d' ' -f1      # sha_dossier
shasum -a 256 src/memory_store.py | cut -d' ' -f1                     # sha_store
$P -c '<对 HOLDOUT_GOLDEN 取 json 规范化后 sha256>'                    # sha_v1
$P -c '<对 HOLDOUT_V2 取 json 规范化后 sha256>'                        # sha_v2
git log $B..HEAD --format='%cd' | sort -u | wc -l                     # cd_uniq
git diff --name-only $B..HEAD -- vendor acceptance tasks \
    tests/test_workbench.py .gitattributes | wc -l                    # frozen_diff
git rev-list --count HEAD..origin/main                                # behind
git status --porcelain -uall | wc -l                                  # status
git ls-files | wc -l                                                  # tracked
ls evidence/run_*.json | wc -l                                        # runjson
$P -c '<逐个比对 MANIFEST 里 5 个冻结件的 sha256>'                     # frozen_match
for g in g0_environment g0_freeze g0_secrets g1_contract g1_memory \
         g1_permissions g1_tools g3_simulate; do
    $P acceptance/gates/$g.py >/dev/null 2>&1; printf '%s/' $?
done | sed 's:/$::'                                                   # gates
$P -m unittest discover -s tests -p 'test_*.py' -t tests              # unittest
```

**期望输出——序数 46 时点实测**（由命令生成，不是手抄；这就是任务书里说的「已过期
的 44 格版本」的重跑结果）：

```
count        = 46
HEAD_subject = docs(evidence): 提交上游闸门异议卷宗（十章 27 条 + 集成期条目 A–F）
tree         = 4a2a8b991e62ea22efb51394ffe0a9bb424a7dfa
author       = SummerTianYi <<personal-email>>
committer    = SummerTianYi <<personal-email>>
author_uniq  = 1
sha_dossier  = 9fdd151de37e195709d3f60e8a4ad8aa983bff94f676087aa565bcf0999feadf
sha_store    = 3faf8d3fe0ba5a5a11dc034fb7e92ce6fefb492b08e1b147a660b53198e6f962
sha_v1       = 561f17ba423dfa024ba9a940632e5d6a8399ea5638ec5b56119e72c6c9b72619
sha_v2       = 201970d578e6760890c30ce7094c8c9c3cbcebe4d7f47663e2de39b9423490da
cd_uniq      = 18
frozen_diff  = 0
behind       = 6
status       = 1
tracked      = 76
runjson      = 66
frozen_match = 5/5 MATCH
gates        = 0/0/0/0/0/2/2/0
unittest     = Ran 254 tests in 0.318s  OK
```

三处读数说明：① `author`/`committer` 两行的邮箱已**记号化**为 `<personal-email>`
（扫描器 P17 探针管这个形态，本文件不印字面）；② `unittest` 那行的**耗时每次不同**，
比对时只看 `Ran 254 tests` 与 `OK`；③ `status = 1` 的那 1 项就是本文件自己
（`?? evidence/ADVERSARIAL_REVIEW.md`），本文件入库后应变 **0**。

**序数 47（本文件那一格）之后必然改变的 6 行**，预先写死，免得下一个人以为对不上：

| 量 | 46 格 | 47 格 | 为什么 |
|---|---:|---:|---|
| `count` | 46 | **47** | 本文件自己入库 |
| `HEAD_subject` | 卷宗那条 | **本格的 subject**（`docs(evidence):` 前缀） | 同上 |
| `tree` | `4a2a8b99…` | **一个新 tree** | 多了一个文件 |
| `status` | 1 | **0** | 唯一的未跟踪项被提交 |
| `tracked` | 76 | **77** | 同上 |
| `cd_uniq` | 18 | **18 或 19** | 取决于本格是否落在一个新日期上（New-3 已证明它是时点量，每多一格 ＋1 或 ＋0） |

其余 13 行**应当逐字不变**，包括 `sha_dossier`、`sha_store`、`sha_v1`、`sha_v2`、
`frozen_diff = 0`、`frozen_match = 5/5 MATCH`、`gates = 0/0/0/0/0/2/2/0`、
`Ran 254 tests`、`runjson = 66`、`behind = 6`。任何一行变了都说明本格的改动越界了
（本轮铁律只准动本文件一个）。

### `behind = 6`，以及它为什么把「快进」这件事推翻了

`behind` 在本轮**早先**实测为 0，本节重跑时已是 **6**（New-5 的完整证据在那一行）。
`origin/main` 是**移动引用**，本文件写作期间被并行 fetch 推进了 6 格，其中包含上游
那版任务 B 的实现。后果是：

- 实测 `merge-base(origin/main, HEAD)` = `<上游基线 commit>`，即两条历史的**共同祖先
  就是上游基线**；而 `origin/main` **不是** HEAD 的祖先、HEAD 也不是 `origin/main`
  的祖先（`git merge-base --is-ancestor` 两个方向都为假）⇒ **两条历史已分叉**
  （我方一侧 46 格、他们一侧 6 格）。
- 所以「把我方这一格快进推到 `origin/main`」在**当前引用状态下不成立**：快进要求
  目标是对方历史的祖先，这里不满足。要么先把上游那 6 格集成进来（rebase / merge，
  本轮铁律禁止），要么推到一个新分支。
- 本文件不处置它（禁 fetch / rebase / merge / push），**只把口径改掉**：本节以及
  §范围 之后所有 count / diff 一律用 **`<上游基线 commit>..HEAD`**，不用
  `origin/main`——前者是永久锚点，后者每次 fetch 都可能动。
- 稳定口径下的实测：序数 46 时点
  `git diff --stat <上游基线 commit>..HEAD` = **`41 files changed, 13753 insertions(+),
  10 deletions(-)`**。§范围 开头那个 `40 files / 11973 / 10` 是**当时用
  `origin/main..HEAD` 测的**，那时 `origin/main` 还等于上游基线，两个口径重合；
  现在不重合了，所以那一行**已不可复现**，以本节这一行为准。

`origin/main` 的当前值本节不写全（它是移动引用，写全也立刻过期，还会多一个 commit
类哈希）；要核对分叉点，跑 `git rev-parse origin/main` 与
`git merge-base origin/main HEAD`，前者应与后者的差为 6 格。

### 已提交取证文档里那些计数，是时点值不是终态值

这一条是写给**读已入库文档的人**的，因为那些文档定稿了、本轮禁改，里面的数字不会
再更新：

| 文档里的数字 | 它是什么时点的值 | 现在怎么对齐 |
|---|---|---|
| 「44 格」 | 序数 44 那一格的 `count` | `git rev-list --count <上游基线 commit>..HEAD`，本格之后应为 47 |
| 「75 tracked」 | 序数 44 / 45 时点 | `git ls-files \| wc -l`；序数 46 = 76、47 = 77 |
| 「66 个 `run_*.json`」 | 本批全程未变（本文件不是 `run_*.json`） | `ls evidence/run_*.json \| wc -l`，仍是 66 |
| 「13345 行」（`task_b_blob_manifest.md` 第 384 行的合计） | 该文档成文时点，74 个文件 | 序数 45 给 `src/memory_store.py` 补了 1 行头，同口径重算应为 **13346**；本文件入库后若把它计入则是另一个值 |
| 「252（原 3 ＋ 新增 249）」（`task_b_integration.md` 第 124 行） | 该文档成文时点 | 序数 39 加了 N1 两个变异体用例 ⇒ 实测 **254**（差异已登记为 `Daniel-1` 的核实差异） |
| 「`%cd` 去重 16」（Nick-N3） | 序数 44 时点 | 44 = 16、45 = 17、46 = 18（New-3 逐格复测过） |

**这不是失真，是自指的必然结果。** 一份文档只能记录它被写下那一刻的世界；如果它记录的
是「包含它自己在内的世界」，那记录动作本身就会让记录过期。可选项只有三个：不记、
记一个必然过期的值、或者把过期这件事本身写清楚。本节选第三个。读任何已入库取证文档
时，**先用 `git rev-list --count <上游基线 commit>..HEAD` 定位自己站在第几格**，再按
上表换算，所有数字都能对上。

### 本文件不能包含自己的最终哈希

同一件事的最尖锐形式：本文件的 sha256 / blob 哈希**不可能写在本文件里**（写进去就
改变了它）。要核本文件的完整性，在入库**之后**跑：

```
shasum -a 256 <repo>/evidence/ADVERSARIAL_REVIEW.md      # 内容 sha256
git ls-tree HEAD evidence/ADVERSARIAL_REVIEW.md          # 本格 tree 里的 blob
git log -1 --format='%s' -- evidence/ADVERSARIAL_REVIEW.md
```

前两条必须指向**同一份字节**（`git hash-object` 的结果应与 `git ls-tree` 给出的 blob
相同）；不同就说明工作树在入库之后又被改过。

写到这里为止，本文件引用的所有量都已经被分成三类、并各自给了对齐命令。自指环在此
切断：**本文件不声称记录终态，它记录的是「终态为什么无法被记录」以及「怎么自己算
出终态」。**
