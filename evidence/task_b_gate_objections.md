# 任务 B · 上游闸门异议卷宗

## 声明

本仓侧全程未修改任何冻结件（`vendor/`、`acceptance/evals/scenarios.json`）、未修改任何闸门脚本（`acceptance/gates/*.py`、`acceptance/run_all.py`、`acceptance/sabotage_drill.py`）、未修改 `acceptance/MANIFEST.json`、未运行 `g0_freeze.py --update`、未运行 `git add --renormalize`（含 `--dry-run`）。本卷宗按用户规则第 10 条提交主仓裁决。所有证据均为本仓侧独立复现——每条附可执行命令与输出原文，不照抄既有文档数字。

复现环境：`./.venv/bin/python`（Python 3.14.7），仓库根目录执行。

取证基线分两段，因为本卷宗跨了上游修复的集成节点：

| 段 | HEAD 位置 | 用于 |
|---|---|---|
| 集成前 | bootstrap 后第 25 个 commit（subject `test(analysis): 词典审计对照表模式`） | 第一～九章里标注「集成前」的取证：`g0_freeze` 恒 FAIL、DoD 字面不可达、分层证据方案 |
| 集成后 | bootstrap 后第 40 个 commit（本仓侧最后一次实测时点），仓库共 41 个 commit，其中第 2 个是上游修复 commit | 标注「集成后」的实测：`g0_freeze` 转 PASS、条目 A–F 全部新取证、三条状态结论 |

两段之间只有上游那 1 个 commit（改 `.gitattributes` 与 `acceptance/MANIFEST.json`）与本仓侧的文档/测试 commit 落地，冻结件、闸门脚本、`tasks/` 全程零改动（`git diff origin/main..HEAD -- vendor acceptance tasks .gitattributes` 为空）。

**关于 commit 序号的时效性**：并行工作在整个取证期间持续提交，HEAD 在集成后这一段里前进了三次（领先 `origin/main` 的 commit 数 37 → 38 → 39，仓库总数 40 → 41）。凡本卷宗引用 commit 序号处，均以最后一次实测时点为准；读时若 HEAD 又前进，序号需按 `git rev-list --count HEAD` 重新对齐。**所有关键数字已在最新 HEAD 下重跑确认仍成立**：tracked = 54、`attr/text=auto eol=lf` 覆盖 54/54（例外 0）、`i/lf w/lf` 52 个 + `i/none w/none` 2 个（两个空的 `__init__.py`）、5 冻结件对 MANIFEST 5/5 MATCH、`git add --renormalize` no-op 推演 54/54、8 闸门退出码 0/0/0/0/0/2/2/0。这些量不随文档/测试 commit 变化，因为它们只涉及冻结件、闸门与 `.gitattributes`——而上游那 1 个 commit 之后，这三类文件再未被任何人改过。

**记号约定**（本卷宗不写任何真实机器路径，以下记号统一指代）：

| 记号 | 指代 |
|---|---|
| `<repo>` | 本仓库根目录的绝对路径 |
| `<home-prefix>/` | macOS 家目录前缀，七字符（斜杠 + `Users` + 斜杠），`g0_environment.py` 第 44 行的扫描 needle 之一 |
| `<win-drive>:\` | Windows 盘符绝对路径前缀，三字符（盘符字母 + 冒号 + **单个**反斜杠），同为 `g0_environment.py` 第 44–45 行的扫描 needle；写作 `<win-drive2>:\` 时指第二个盘符字母 |
| `<linux-home-prefix>/` | Linux 家目录前缀（斜杠 + `home` + 斜杠）。闸门四个 needle 都不含它，是条目 23 手工复扫时本仓侧自补的模式 |
| `<mac-tmp-prefix>` | macOS 私有临时目录前缀（斜杠 + `var` + 斜杠 + `folders`），同上，闸门不管、本仓侧自补 |
| `<tmp>` | 仓库外的临时目录，本仓侧所有隔离实验（副本篡改、eol 复现）只发生在这里，真仓库不受影响 |
| `NEEDLE0`…`NEEDLE3` | 条目 22 盲区 ③ 里 `g0_environment.py` 第 44 行那四个 needle 的占位符。它们是路径前缀模式串，原样写进本卷宗就等于写入真实绝对路径、违反消毒规则，故一律用占位符 + 结构描述（长度、反斜杠个数、字符构成）表达；原文用 `git show HEAD:acceptance/gates/g0_environment.py \| sed -n '44p'` 核对 |

---

## 裁决请求速览

| # | 一句话 | 严重度 | 阻塞了什么 | 需要主仓侧做什么 | 状态 |
|---|--------|--------|------------|------------------|------|
| 1 | `vendor/agent_core/harness.py` sha256 与 MANIFEST 不符，`g0_freeze` 恒 FAIL | HIGH | DoD「`run_all.py --strict` 全绿」对任何任务包不可达 | 比对原始字节，确认哪侧为真相并重算 | **已裁决/已修复**（上游 commit `fix: regenerate frozen MANIFEST` 选择了重算 MANIFEST 侧） |
| 7 | `run_all.py` verdict 逻辑使 `--strict` 在存在 FAIL 时零信息量 | MEDIUM | strict 模式的独立证据价值被掩盖 | 明确 strict 语义应否在 FAIL 时仍产出区分性结论 | 待裁决 |
| 8 | evidence 文件名只到秒级，同秒覆盖无告警 | MEDIUM | 证据留存完整性（实测丢失 1 份 JSON） | 文件名加毫秒或模式后缀，或覆盖前告警 | 待裁决 |
| 9 | 子进程 stderr 被丢弃，FAIL 项 detail 可能为空 | MEDIUM | 闸门崩溃时诊断能力 | detail 里保留 stderr 尾部 | 待裁决 |
| 10 | `GATES` 列表不含单元测试 | HIGH | 204 个用例完全不在 DoD 判定路径上 | 把 `unittest discover` 纳入 GATES 或让闸门内建留出集 | 待裁决 |
| 11 | `g1_memory` 只用内联 8 对 GOLDEN，留出集不进闸门 | HIGH | 过拟合实现（golden 1.0 / 留出 0.667）可通过全部验收 | 同 #10 | 待裁决 |
| 13 | golden 8 条 × 阈值 0.8，判别余量恰好 1 个样本 | MEDIUM | 轻度退化不敏感，0.875 与 1.000 同样显示 PASS | 闸门输出回显实测 P/R 数值，或提高 golden 规模 | 待裁决 |
| 15 | `sabotage_drill.py` 无「破坏前 gate 须为绿」前置断言 | HIGH | `DRILLS DETECTED: 3 of 3` 中 eval-tamper 路为假阳性，有效检出实为 2/3 | 加前置绿断言 | **集成后已失效**（`g0_freeze` 转 PASS，三路前置绿条件现已全部满足；缺陷本身仍在，需重跑 drill 确认有效检出是否变为真 3/3，见条目 D） |
| 17 | 恢复后复验是死代码（`try/finally` 后 `return` 使其不可达） | MEDIUM | drill 从不自证恢复成功 | 把复验逻辑移入 `finally` 之后正确的控制流位置 | 待裁决（条目 D 已用 AST 静态证明补钉死） |
| 18 | `run_gate()` 丢弃闸门 stdout/stderr | MEDIUM | 三路全成功时 drill 只输出一行，无法审计 | 打印每路闸门输出 | 待裁决 |
| 19 | drill 文本模式改写把 CRLF 整体归一化 | MEDIUM | SIGKILL 时留下行尾被改写的冻结件（上游 `.gitattributes` 统一 LF 后风险降低但未消除） | 改用字节模式定点替换 | 待裁决 |
| 20 | drill 不写 evidence JSON | LOW | 与 `evidence/README.md` 规则 2 冲突 | drill 结束时写 JSON 或明确豁免 | 待裁决 |
| 21 | `evidence/README.md`「保留最后 10 条」与 `run_all.py` 无裁剪逻辑冲突 | LOW | 规则无法被执行也无法被核查 | 实现裁剪 / 改规则 / 把关键 JSON 改为可跟踪 | 待裁决 |
| 22 | 闸门扫描盲区：`tests/`、`evidence/` 不在目录范围，`.log` 不在后缀集，**且 Windows 盘符 needle 因双重转义而失效** | MEDIUM-HIGH | 交付物的绝对路径与密钥检查无闸门覆盖；4 个路径 needle 里 2 个实际不工作，常规 Windows 硬编码路径漏检 | 扩大扫描范围；修正第 44 行双重转义；收窄第 45 行的 `acceptance/` 豁免；或明确责任归属 | 待裁决（盲区 ③ 为本轮新发现） |
| 24 | `PROTOCOL.md` 不存在 | LOW | 开发流程四步通读缺一步 | 补 PROTOCOL.md 或明确协议事实来源指向 harness.py | 待裁决 |
| 25 | DoD 与单任务包交付节点的语义缝隙 | HIGH | 单个任务包在自己的交付节点上永远拿不到 `--strict` 全绿 | 明确单任务包节点的 strict 口径 | 待裁决 |
| 27 | `score_retrieval` 签名 `| None` 成为永久死代码 | LOW | 协议残留，不影响功能但增加阅读负担 | 集成时是否清理 | 待裁决 |
| A | 旧期望值 `219691…` 的生成环境与源文件不明，14 种行尾/编码变换（另 1 种不可构造）与全对象库 108 个 blob 反查均无法复现它 | HIGH | 上游 commit message 把两类不同成因笼统归为「CRLF bootstrap drift」，裁决依据不完整；`g1_contract`/`g3_simulate` 结论的可迁移性无法判定 | 说明旧期望值的生成环境与源文件；确认主仓当前 `harness.py` 与本仓 blob 是否字节相同；commit message 分开表述两类成因 | 待裁决 |
| B | `g0_freeze` 校验的是磁盘 raw 字节，与 git 的 clean/smudge 过滤器完全解耦 | HIGH | 同一份工作树在 git 眼里「clean」而闸门判「drifted」，反之亦然；行尾策略变更会让闸门与 git 给出矛盾结论 | 明确哈希锁的语义基准（磁盘字节 / index blob / HEAD blob），并在 MANIFEST 里记录该基准 | 待裁决 |
| C | `MANIFEST.json` 自身不在冻结清单内，且 `--update` 无任何守卫 | MEDIUM-HIGH | 锁文件本身可被无痕改写；一条命令即可让恒 FAIL 的闸门变绿且不留审计痕迹 | 把 MANIFEST 自身纳入校验（或另有签名/双人复核）；`--update` 加确认、diff 回显与审计留存 | 待裁决 |
| D | 条目 15 的假阳性在集成后已不成立 + 条目 17 的死代码已用 AST 静态证明钉死 | MEDIUM | 上一版「有效检出 2/3」的结论在集成后过期，若继续引用会误判 drill 现状 | 确认 drill 是否需在前置绿条件下重跑一次以给出真正的 3/3 判定 | **状态已变**（见条目 D：集成后前置绿条件全部满足，实测重跑留待 QA 最终取证轮） |
| E | `MANIFEST.json` 自身无尾换行，`git diff` 每次都要额外打一行 `\ No newline at end of file` | LOW | 无功能影响；污染 diff 输出，且 `--update` 每次重写都会保持这个缺陷 | `--update` 写盘时补尾换行（会改变 MANIFEST 自身 sha256，需与 B/C 一并裁决） | 待裁决 |
| F | `git checkout --` 对「clean 过滤后等价于 index」的文件是 no-op，行尾矛盾态无法用常规手段消除 | HIGH | 集成时若工作树仍是 CRLF，`git status` 报 clean、`git checkout --` 不改一个字节，唯一出路是 `rm` + `git checkout HEAD --`；这条路径不在任何文档里 | 在集成说明里写明该 no-op 语义与正确处置手法 | 待裁决（`<tmp>` 副本已完整复现 no-op 成立条件与失效条件） |

严重度分布（速览表共 23 行 = 原有 17 条 + 新增 A–F 六条）：HIGH 8（1 / 10 / 11 / 15 / 25 / A / B / F）、MEDIUM-HIGH 2（22 / C）、MEDIUM 8（7 / 8 / 9 / 13 / 17 / 18 / 19 / D）、LOW 5（20 / 21 / 24 / 27 / E），合计 8+2+8+5 = 23。条目 22 原为 MEDIUM，因本轮查明的盲区 ③（盘符 needle 双重转义使 4 个路径检测里 2 个实际不工作）上调为 MEDIUM-HIGH。按状态分：**已由上游裁决修复** 1（条目 1）、**集成后已失效** 1（条目 15 的「假阳性 / 有效检出 2/3」推论）、**状态已变** 1（条目 D）、**待裁决** 20。注：A–F 用字母编号而非接着 27 往下排，是因为既有数字编号已被其他取证文档交叉引用，重编号会制造死链；且条目 D 不是一条新缺陷，而是对条目 15/17 现状的更新，单独登记只为了在速览表里让主仓侧一眼看到状态变化。

---

## 一、冻结清单与 `g0_freeze` 闸门：集成前恒 FAIL / 集成后 PASS

本章分两段写。**集成前**（bootstrap 后第 25 个 commit 时取证）：`g0_freeze` 恒 FAIL，DoD「`run_all.py --strict` 全绿」字面不可达，本仓侧当时采用分层证据方案。**集成后**（上游修复已落地，HEAD = bootstrap 后第 40 个 commit）：`g0_freeze` 实测转 PASS。两段均如实保留，集成前的取证不因结论过期而抹除——它仍是「闸门曾经恒红、而任务包无法自证清白」这个事实的唯一证据。章末的条目 A / E 是集成后新查明的、**仍未被上游修复触及**的两个问题。

### 集成前的现象

`g0_freeze` 闸门恒 FAIL，唯一报错行：

```
vendor/agent_core/harness.py: content drifted from frozen manifest
```

`run_all.py` 第 49 行 verdict 逻辑遇任何 FAIL 直接短路成 `FAIL`，普通模式与 `--strict` 均 exit 1。README DoD「`run_all.py --strict` 全绿」与 SPEC 证据要求第 1 条「run_all --strict ×3」在当前仓库状态下对任何任务包都不可达，与实现质量无关。

### 集成前的证据

**1. 两边 sha256 复算**

```
$ ./.venv/bin/python -c "import json; m=json.load(open('acceptance/MANIFEST.json')); print(m['vendor/agent_core/harness.py'])"
219691162b9f09b8e544acaff6a39ac613ba2027d5b2ba9b2713875934ea8da5

$ shasum -a 256 vendor/agent_core/harness.py
cb1ae928f80674952c4ac6e6385d260a7dbd5cf93ac5ab96889ff6bdb32b2807  vendor/agent_core/harness.py
```

MANIFEST 期望 `219691...`，磁盘实际 `cb1ae9...`，不匹配。

**2. 漂移存在于 bootstrap commit 内部**

```
$ git status --porcelain -- vendor/agent_core/harness.py
（空）

$ git diff HEAD -- vendor/agent_core/harness.py
（空）

$ git show $(git rev-list --max-parents=0 HEAD):vendor/agent_core/harness.py | shasum -a 256
cb1ae928f80674952c4ac6e6385d260a7dbd5cf93ac5ab96889ff6bdb32b2807  -

$ git show HEAD:vendor/agent_core/harness.py | shasum -a 256
cb1ae928f80674952c4ac6e6385d260a7dbd5cf93ac5ab96889ff6bdb32b2807  -
```

文件从 bootstrap commit（`feat: workbench bootstrap`）起就是这个字节，从未被任何后续 commit 修改。不是本地损坏，不是本地修改。

**3. 排除行尾/BOM 成因（7 种变换逐一比对）**

```
$ ./.venv/bin/python -c "
import hashlib; from pathlib import Path
data = Path('vendor/agent_core/harness.py').read_bytes()
expected = '219691162b9f09b8e544acaff6a39ac613ba2027d5b2ba9b2713875934ea8da5'
variants = {
    'original': data,
    'LF->CRLF': data.replace(b'\r\n',b'\n').replace(b'\n',b'\r\n'),
    'CRLF->LF': data.replace(b'\r\n',b'\n'),
    'with BOM': b'\xef\xbb\xbf'+data,
    'LF->CRLF+BOM': b'\xef\xbb\xbf'+data.replace(b'\r\n',b'\n').replace(b'\n',b'\r\n'),
    'strip trailing newline': data.rstrip(b'\n').rstrip(b'\r'),
    'BOM+strip trailing': b'\xef\xbb\xbf'+data.rstrip(b'\n').rstrip(b'\r'),
}
for name,v in variants.items():
    h=hashlib.sha256(v).hexdigest()
    print(f'{name:30s} bytes={len(v):6d} match={h==expected}')
"
```

输出：

```
original                       bytes= 10055 match=False
LF->CRLF                       bytes= 10312 match=False
CRLF->LF                       bytes= 10055 match=False
with BOM                       bytes= 10058 match=False
LF->CRLF+BOM                   bytes= 10315 match=False
strip trailing newline         bytes= 10054 match=False
BOM+strip trailing             bytes= 10057 match=False
```

7 种变换无一命中。文件当前是纯 LF（CRLF=0, bare_LF=257）、无 BOM。漂移是实质内容差异。

**4. 对照：`scenarios.json` 的 CRLF 成因确认**

同一批取证里，`acceptance/evals/scenarios.json` 也曾报漂移。该文件是 5 个冻结件里唯一用 CRLF 行尾的：

```
$ ./.venv/bin/python -c "
from pathlib import Path
d=Path('acceptance/evals/scenarios.json').read_bytes()
print(f'bytes={len(d)}, CRLF={d.count(b\"\\r\\n\")}, bare_LF={d.count(b\"\\n\")-d.count(b\"\\r\\n\")}')
"
bytes=2870, CRLF=118, bare_LF=0
```

通过本地 `.git/info/attributes` 设 `acceptance/evals/scenarios.json text eol=crlf` + 重新检出后，工作树字节与 MANIFEST 期望值匹配（`01ed805a...`）。两件漂移成因不同、处置不同：scenarios.json 是行尾问题（本地可修），harness.py 是内容差异（本地修不了）。

**5. `.git/info/attributes` 当前内容**

```
$ cat .git/info/attributes
acceptance/evals/scenarios.json text eol=crlf
```

只覆盖 `scenarios.json` 一个文件。这是本地文件，不被 git 跟踪，不影响远端。

### 上游裁决结果

远端 `origin/main` 相对 bootstrap 多 1 个 commit（作者 `SummerTianYi`，subject `fix: regenerate frozen MANIFEST (CRLF bootstrap drift) + force LF via .gitattributes`），内容：

```
$ git diff --name-status $(git rev-list --max-parents=0 HEAD)..origin/main
A       .gitattributes
M       acceptance/MANIFEST.json
```

- **重算 MANIFEST**：`vendor/agent_core/harness.py` 条目改为 `cb1ae928...`（即认定文件字节为真相）
- **新增 `.gitattributes`**：`* text=auto eol=lf`，从根上消除跨平台换行符漂移
- **scenarios.json 的 MANIFEST 值也变了**：从 `01ed805a...`（CRLF 版）改为 `2c5dab3f...`（LF 版）。验证：本地 CRLF 文件转 LF 后 sha256 = `2c5dab3f...`，与上游 MANIFEST 一致

```
$ ./.venv/bin/python -c "
import hashlib; from pathlib import Path
d=Path('acceptance/evals/scenarios.json').read_bytes()
lf=d.replace(b'\r\n',b'\n')
print(f'LF version sha256: {hashlib.sha256(lf).hexdigest()}')
"
LF version sha256: 2c5dab3fc5e414680193c7b998bb62cf9fe3c6299f2f002682a75efa8179b00e
```

上游 5/5 冻结件全部匹配：

```
$ ./.venv/bin/python -c "
import hashlib,json,subprocess
m=json.loads(subprocess.run(['git','show','origin/main:acceptance/MANIFEST.json'],capture_output=True,text=True).stdout)
for rel,exp in m.items():
    blob=subprocess.run(['git','show',f'origin/main:{rel}'],capture_output=True).stdout
    print(f'{rel}: {\"MATCH\" if hashlib.sha256(blob).hexdigest()==exp else \"MISMATCH\"}')
"
vendor/agent_core/harness.py: MATCH
vendor/agent_core/song_catalog.py: MATCH
vendor/agent_core/voice_text.py: MATCH
vendor/agent_core/data/luotianyi_original_songs.json: MATCH
acceptance/evals/scenarios.json: MATCH
```

上游**未碰任何闸门逻辑**：

```
$ git diff $(git rev-list --max-parents=0 HEAD)..origin/main -- acceptance/run_all.py acceptance/sabotage_drill.py acceptance/gates/ evidence/README.md
（空）
```

### 本仓侧合规自证

- 从未运行 `g0_freeze.py --update`
- 从未修改 `acceptance/MANIFEST.json`（`git diff HEAD -- acceptance/MANIFEST.json` 为空）
- 从未修改任何冻结件（`git diff $(git rev-list --max-parents=0 HEAD)..HEAD -- vendor acceptance tasks` 为空）
- 上游修复是独立裁决结果，与本仓侧无关

### 遗留动作

~~本仓侧 `.git/info/attributes` 里的 `acceptance/evals/scenarios.json text eol=crlf` 是临时措施。~~
**已完成**：该本地规则已撤销，`.gitattributes` 的 `eol=lf` 生效，`g0_freeze` 实测 5/5 PASS。

### 集成后的实测状态（集成前 / 集成后对照）

以下均为集成后在 HEAD（bootstrap 后第 40 个 commit）上的**实测**，不再是静态推演：

| 项 | 集成前 | 集成后 | 实测依据 |
|---|---|---|---|
| `g0_freeze` 退出码 | 1（FAIL） | **0（PASS）** | 逐个单独跑 8 闸门，退出码依次 0/0/**0**/0/0/2/2/0 |
| 冻结件 sha256 对 MANIFEST | 4/5（harness.py 一条漂移） | **5/5 MATCH** | 逐个 `hashlib.sha256(read_bytes())` 对比 |
| `run_all.py` 普通模式 | `FAIL` / exit 1 | **`PENDING-OK` / exit 0** | 不经管道取真退出码 |
| `run_all.py --strict` | `FAIL` / exit 1 | **`BLOCKED` / exit 1** | 同上；零 FAIL，唯一阻塞 = `g1_permissions`/`g1_tools` PENDING（任务 C/E 未认领） |
| `scenarios.json` 工作树 | 2870 bytes / CRLF=118 / sha256 `01ed805a…` | **2752 bytes / CRLF=0 / sha256 `2c5dab3f…`** | `.gitattributes` 的 `eol=lf` 已生效，`.git/info/attributes` 文件已不存在 |
| DoD「`--strict` 全绿」可达性 | 字面不可达（恒 FAIL 短路） | **仍不可达，但成因换了**：不再是 FAIL，而是 C/E 未认领的 PENDING | 条目 25 依旧成立，见第八章 |

8 闸门逐个单独跑的原始输出（集成后）：

```
--- g0_environment exit=0   G0_ENVIRONMENT: PASS
--- g0_secrets     exit=0   G0_SECRETS: PASS
--- g0_freeze      exit=0   G0_FREEZE: PASS
--- g1_contract    exit=0   G1_CONTRACT: PASS
--- g1_memory      exit=0   G1_MEMORY: PASS
--- g1_permissions exit=2   evaluate() not implemented (Task C) / G1_PERMISSIONS: PENDING
--- g1_tools       exit=2   openai_schema/execute not implemented (Task E) / G1_TOOLS: PENDING
--- g3_simulate    exit=0   G3_SIMULATE: PASS
```

**这里要如实指出一件事**：集成前本仓侧采用的分层证据方案（普通模式 + strict 模式各跑 3 轮、逐闸门明细表对每个非 PASS 项归因），当时是为了在 verdict 恒 FAIL 的前提下仍能交付可用证据而做的**替代手段**，不是因为分层本身比 verdict 更好。集成后 verdict 已能区分 FAIL 与 BLOCKED，分层方案的必要性下降，但它揭露的两个编排器缺陷（条目 7 verdict 短路、条目 9 stderr 丢弃）仍然存在，不因 `g0_freeze` 转绿而消失。

---

### 条目 A：旧期望值的生成环境与源文件不明【HIGH·待裁决】

**现象**：上游修复选择了「重算 MANIFEST 侧」，即认定磁盘字节为真相。这一步本仓侧无异议。但旧期望值 `219691162b9f09b8e544acaff6a39ac613ba2027d5b2ba9b2713875934ea8da5` 到底按什么环境、对哪个源文件算出来的，上游 commit message 没交代，只笼统写了「CRLF bootstrap drift」。集成后本仓侧把这个归因逐条验证，结论是：**它对 `scenarios.json` 成立，对 `harness.py` 不成立**，两类漂移成因不同。

**证据 1：`harness.py` 当前字节形态**

```
bytes=10055  CR=0  CRLF=0  BOM=False  endsNL=True
sha256=cb1ae928f80674952c4ac6e6385d260a7dbd5cf93ac5ab96889ff6bdb32b2807  ==新 MANIFEST 期望? True
```

纯 LF、无 BOM、有尾换行——与另外 3 个 vendor 文件形态完全一致。它没有任何行尾异常可供「CRLF drift」解释。

**证据 2：14 种行尾/编码变换反查旧期望值（集成前只做了 7 种，本轮扩到 14 种）**

```
 1  LF 原样                     10055 B  cb1ae928f806..  match_OLD=False
 2  LF->CRLF                    10312 B  35a18535eb69..  match_OLD=False
 3  LF->裸CR（老 Mac 行尾）        10055 B  cef55453d84e..  match_OLD=False
 4  CRLF->LF                    10055 B  cb1ae928f806..  match_OLD=False
 5  +UTF8 BOM                   10058 B  a13a4a73abba..  match_OLD=False
 6  +UTF16LE BOM                10057 B  2b0558971f65..  match_OLD=False
 7  LF->CRLF + UTF8 BOM         10315 B  cf63fb2a9f5f..  match_OLD=False
 8  去尾换行                      10054 B  8e8990630045..  match_OLD=False
 9  去尾换行 + LF->CRLF            10310 B  fd7c81ca389f..  match_OLD=False
10  尾加一个空行                   10056 B  25db0a961823..  match_OLD=False
11  尾加空行 + LF->CRLF            10314 B  0dfe33f0d202..  match_OLD=False
12  裸CR也转LF                    10055 B  cb1ae928f806..  match_OLD=False
13  utf-16-le 重编码              16334 B  33c2bd75c50a..  match_OLD=False
14  utf-16（带BOM）重编码           16336 B  4a25793a50e2..  match_OLD=False
命中数: 0/14

第 15 种 latin-1 重编码 -> 不可构造：UnicodeEncodeError
   原因：harness.py 含中文，字符超出 latin-1 的 0x00–0xFF 范围，
         该变体对本文件在数学上不存在
```

比集成前的 7 种变换多出 7 种（裸 CR 行尾、UTF-16LE BOM、去尾换行+CRLF、尾加空行、尾加空行+CRLF、两种 UTF-16 重编码），仍无一命中。**行尾与编码不足以解释这条漂移。**

派单里列的第 15 种变体（latin-1 重编码），本仓侧尝试构造时抛 `UnicodeEncodeError`——不是「没命中」，而是**根本无法生成**（`harness.py` 里的中文字符超出 latin-1 的表示范围）。所以这条证据的完整覆盖面是「14 种可比对的变体全 0 命中 + 1 种数学上不可构造」。

**证据 3：全对象库 blob 反查**

把仓库对象库里**每一个** blob 都取出来算 sha256，看旧期望值是否对应任何一个曾存在过的文件版本：

```
$ git cat-file --batch-all-objects --batch-check | awk '$2=="blob"' | wc -l
108

旧 harness 期望 219691162b9f…  : NOT FOUND
新 harness 实际 cb1ae928f806…  : FOUND [('29dca70bcc740976910cd0f85d38f2ce9034795c', 10055)]
旧 scenarios 期望 01ed805ae688… : NOT FOUND
新 scenarios 实际 2c5dab3fc5e4… : FOUND [('53ab5c2bf54027f3e333e0f980259acbe0e72150', 2752)]
```

（blob 总数随时点而变：集成前的取证记「约 86 个」，上一轮实测 101 个，本轮实测 **108 个**——对象库随每个新 commit 单调增长，这个数本身不是结论。**反查结论在三个时点上完全一致**：两个旧期望值始终 NOT FOUND，两个新期望值始终 FOUND 且指向同一个 blob。以最后一次实测为准。）

两个旧期望值在**整个对象库里都不存在对应 blob**。这意味着：旧 MANIFEST 记的 `219691…` 从未对应本仓库任何一个被 git 跟踪过的 `harness.py` 版本。它要么来自仓库外的一份源文件，要么来自另一个环境的渲染结果。

**证据 4：对照——`scenarios.json` 的旧期望值能被精确复现**

```
worktree(集成后) bytes=2752 CRLF=0   sha256=2c5dab3fc5e41468..
LF 渲染          bytes=2752           sha256=2c5dab3fc5e414680193c7b998bb62cf9fe3c6299f2f002682a75efa8179b00e
CRLF 渲染        bytes=2870 CRLF=118  sha256=01ed805ae688e431a8f09bf64d21d445cdf26e85843c6fd9d08b58332df42e67
```

LF blob 的 CRLF 渲染 **精确等于**旧 MANIFEST 里 `scenarios.json` 的期望值。所以这一条确实是「CRLF drift」——上游的归因对它是对的。

**证据 5：bootstrap MANIFEST 5 条逐个判定（LF / CRLF 双渲染比对）**

| 冻结件 | bootstrap blob | 旧期望值判定 | 上游改了吗 |
|---|---|---|---|
| `vendor/agent_core/harness.py` | 10055 B / CR=0 | **NO-MATCH**（LF、CRLF 两种渲染都不是） | 改了（→ `cb1ae928…`） |
| `vendor/agent_core/song_catalog.py` | 4828 B / CR=0 | LF-MATCH | 未改 |
| `vendor/agent_core/voice_text.py` | 1377 B / CR=0 | LF-MATCH | 未改 |
| `vendor/agent_core/data/luotianyi_original_songs.json` | 8790 B / CR=0 | LF-MATCH | 未改 |
| `acceptance/evals/scenarios.json` | 2752 B / CR=0 | **CRLF-MATCH** | 改了（→ `2c5dab3f…`） |

这张表是条目 A 最有力的一块证据：**bootstrap 的 MANIFEST 是在混用两种行尾形态的工作树上生成的**——4 条按 LF 工作树算，1 条（`scenarios.json`）按 CRLF 工作树算，而 `harness.py` 那条两种都不是。同一个 commit 内部就存在三种不同基准，说明生成 MANIFEST 的那台机器上，工作树各文件的行尾形态本身不一致（典型的跨平台检出 + 本地 `.git/info/attributes` 干预结果）。

**证据 6：本仓从未改过 `harness.py`**

```
$ git log --oneline --all -- vendor/agent_core/harness.py
$BOOTSTRAP feat: workbench bootstrap - task packs, acceptance gates, evidence system
```

`--all` 覆盖全部 ref（含 `origin/main`），只有 bootstrap 一条记录。hash 部分按记号约定以 `$BOOTSTRAP` 代写（赋值方式见附录 B 开头），因为 commit hash 在 rebase 后会变死链；**这里的关键不是 hash 值，而是输出恒为 1 行**。本仓侧 39 个后续 commit（即 `origin/main..HEAD` 的全部）与上游那 1 个修复 commit（在 `origin/main` 上，不计入这 39 个）都没有触碰过这个文件的内容（上游只改了 MANIFEST 里指向它的期望值）。

**请主仓侧回答的三条**

1. **旧期望值 `219691162b9f09b8e544acaff6a39ac613ba2027d5b2ba9b2713875934ea8da5` 是在什么环境、对哪个源文件算出来的？** 它不对应本仓库对象库里任何 blob（108/108 已排查），也不是当前字节的 14 种行尾/编码变体中的任何一种（0/14 命中；第 15 种 latin-1 重编码因本文件含中文而抛 `UnicodeEncodeError`，数学上不可构造）。若它来自主仓侧一份未入库的 `harness.py`，请把那份文件的字节形态（大小、CR 数、有无 BOM、有无尾换行）与 sha256 一并给出。
2. **本仓的 `vendor/agent_core/harness.py`（blob `29dca70bcc740976910cd0f85d38f2ce9034795c`、sha256 `cb1ae928f80674952c4ac6e6385d260a7dbd5cf93ac5ab96889ff6bdb32b2807`、10055 字节、CR 数 0）与主仓当前的 `harness.py` 是否字节相同？** 若相同，条目 1 的裁决闭合。若不同，则本仓侧 `g1_contract` 与 `g3_simulate` 的 PASS 结论**不可迁移**——这两个闸门都直接依赖 `harness.py` 里的 `EMOTION_EVENTS`/`GESTURE_EVENTS`/`AgentReply`/`BASE_SYSTEM_PROMPT`，字节不同意味着契约面不同，本仓侧的 PASS 只对本仓这份字节成立，主仓侧需要按自己那份重判。
3. **上游 commit message 请分开表述两类成因。** 现在笼统的「CRLF bootstrap drift」只对 `scenarios.json` 成立；`harness.py` 那条经 14 变换 + 108 blob 反查证明与行尾无关。message 是后人追溯裁决依据的唯一线索，把两类混为一谈会让后来者误以为「统一 LF 就修好了一切」，从而漏掉第 1、2 条需要回答的问题。

**严重度 HIGH 的理由**：不是因为它现在让闸门变红（已不红），而是因为**裁决记录不完整**。上游用「重算 MANIFEST」把症状消掉了，但没有回答「旧值从哪来」，于是没人知道主仓与本仓的 `harness.py` 是否同一份字节——而这直接决定本仓侧两个行为闸门的结论能不能被主仓采信。

---

### 条目 E：`MANIFEST.json` 自身无尾换行【LOW·待裁决】

**现象**：`acceptance/MANIFEST.json` 最后一个字节是 `}`（`0x7d`），没有尾随换行。工作树与 HEAD blob 皆然：

```
worktree: bytes=547 last_byte=0x7d ('}') endsNL=False
HEAD blob: bytes=547 last_byte=0x7d        endsNL=False
```

**证据**：`git diff` 自己每次都要额外打一行提示。集成后核对冻结区 diff 时的原文输出：

```
$ git diff $(git rev-list --max-parents=0 HEAD)..HEAD -- acceptance/MANIFEST.json
…
-  "acceptance/evals/scenarios.json": "01ed805ae688e431a8f09bf64d21d445cdf26e85843c6fd9d08b58332df42e67"
+  "acceptance/evals/scenarios.json": "2c5dab3fc5e414680193c7b998bb62cf9fe3c6299f2f002682a75efa8179b00e"
 }
\ No newline at end of file
```

**成因**：`g0_freeze.py` 第 49 行

```python
MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
```

`json.dumps(..., indent=2)` 的输出不以换行结尾，`write_text` 原样落盘。所以每一次 `--update` 都会重新生成一个无尾换行的文件——缺陷是自我复制的，不会因为多跑几次而自愈。

**影响**：无功能影响（`json.loads` 不在意尾换行，`g0_freeze` 5/5 照常 PASS）。两处轻微代价：一是污染 diff 输出，每次涉及 MANIFEST 的 diff 都多一行噪声，在自动化解析 diff 的场合需要额外处理；二是与条目 C 联动——若将来把 MANIFEST 自身纳入哈希锁（条目 C 的建议），补尾换行会改变它的 sha256，两件事必须一并裁决，否则修 E 会打破 C 的锁。

**为什么仍要登记**：它是「闸门自己生成的产物不符合仓库其余文件的约定」的一个具体样本。仓库 54 个 tracked 文件里，其余全部有尾换行（`.gitattributes` 那份 19 字节也是 `b'* text=auto eol=lf\n'`，带尾换行），只有闸门自己写出来的 MANIFEST 例外。

---

## 二、闸门实现层面的机制缺陷（`g0_freeze`）

第一章讲的是「MANIFEST 里记的值对不对」，本章讲的是「`g0_freeze` 这个闸门自己怎么干活」。两条都是集成后新查明的，上游的修复（重算 MANIFEST + 新增 `.gitattributes`）**没有触及任何闸门逻辑**（`git diff $BOOTSTRAP..origin/main -- acceptance/run_all.py acceptance/sabotage_drill.py acceptance/gates/` 为空），所以本章两条在集成后依旧成立。

### 条目 B：`g0_freeze` 校验的是磁盘 raw 字节，与 git 的 clean/smudge 完全解耦【HIGH·待裁决】

**现象**：闸门算哈希的路径与 git 算哈希的路径是两条互不相交的管道。同一份工作树，两者可以给出**相反**的结论。

**证据 1：源码钉死**

```
$ git show HEAD:acceptance/gates/g0_freeze.py | grep -n "read_bytes\|read_text"
25:    return hashlib.sha256(path.read_bytes()).hexdigest()
31:    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
```

第 24–25 行：

```python
def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
```

第 33–42 行的比对循环直接拿这个值与 MANIFEST 里的字符串比：

```python
for rel in FREEZE_TARGETS:
    path = REPO / rel
    if not path.is_file():
        problems.append(f"{rel}: missing")
        continue
    expect = manifest.get(rel)
    if expect is None:
        problems.append(f"{rel}: not in manifest")
    elif expect != sha256(path):
        problems.append(f"{rel}: content drifted from frozen manifest")
```

`Path.read_bytes()` 读的是**磁盘上的原始字节**，不经任何 git 过滤器。而 git 判断一个文件是否修改，用的是「工作树字节跑 clean 过滤器后的结果 == index sha」。`.gitattributes` 里的 `text=auto eol=lf` 就是一条 clean 过滤器规则：它会把 CRLF 折成 LF 再算哈希。两条管道因此对同一份 CRLF 字节算出不同的值。

**证据 2：矛盾态实测（`<tmp>` 仓库副本，不碰真仓库）**

在副本里构造出「工作树是 CRLF、`.gitattributes` 已说 `eol=lf`、MANIFEST 已记 LF 版 sha256」这个集成时会真实遇到的状态（构造手法见条目 F），然后两边各问一次：

```
worktree bytes=2870 CR=118 sha256=01ed805ae688e431..

git status --porcelain --untracked-files=no : []            ← git 说 clean
git hash-object（with filters）              : 53ab5c2bf540…  ← == index sha == HEAD blob
MANIFEST 期望                                : 2c5dab3fc5e41468…

$ python3 acceptance/gates/g0_freeze.py
acceptance/evals/scenarios.json: content drifted from frozen manifest
exit=1                                                       ← 闸门说 FAIL
```

**同一份字节，git 说未修改，闸门说漂移了。** 两边都没错——git 比的是 clean 过滤后的等价性，闸门比的是磁盘字节的相等性。对照：`rm` + `git checkout HEAD --` 重检出为 LF（2752 bytes / CR=0）后，闸门 exit=0、输出 `G0_FREEZE: PASS`。

**为什么这是 HIGH 而不是学术细节**：

1. 集成前本仓侧就活在这个矛盾里。当时为了让 `scenarios.json` 对上旧 MANIFEST 的 CRLF 期望值，本仓侧在 `.git/info/attributes` 里设了 `acceptance/evals/scenarios.json text eol=crlf`。那个状态下 git 说 clean（clean 过滤器按 crlf 规则把 CRLF 折回 LF blob）、闸门也说 MATCH（磁盘字节正是 CRLF）——两边偶然一致。但一致的**理由不同**，一旦行尾策略变更（上游新增 `.gitattributes`），两边立刻分叉。这就是集成时真实发生的事。
2. MANIFEST 里存的到底是「磁盘字节的 sha256」还是「index blob 的 sha256」，文件本身没说。集成前 4 条是前者、1 条（`scenarios.json`）是「CRLF 工作树的磁盘字节」——见条目 A 证据 5 那张表。**基准不明，就无法判断一次哈希不匹配到底是内容被改了、还是仅仅行尾渲染变了。**
3. 它与条目 F 互相放大：闸门报 drifted 时，直觉反应是 `git checkout --` 重检出，而 git 认为文件 clean，于是那是一条 no-op（条目 F 实测）。排除故障的人会卡在「git 说没问题、闸门说有问题、git checkout 也不管用」这个三角里。

**请主仓侧裁决**：明确哈希锁的语义基准是哪一个——磁盘字节、index blob、还是 HEAD blob——并把该基准写进 `MANIFEST.json` 自身（例如加一个 `"_basis": "worktree-bytes"` 字段）与 `g0_freeze.py` 的 docstring。若基准定为磁盘字节，则 `.gitattributes` 的任何行尾策略变更都必须伴随一次 MANIFEST 重算，这个耦合关系应在文档里写明；若基准定为 index/HEAD blob，则 `sha256()` 应改为读 `git cat-file blob HEAD:<rel>` 而非 `path.read_bytes()`。

---

### 条目 C：`MANIFEST.json` 自身不在冻结清单内，且 `--update` 无任何守卫【MEDIUM-HIGH·待裁决】

**现象 1：锁文件自身不受锁保护**

```
$ git show HEAD:acceptance/gates/g0_freeze.py | sed -n '15,21p'
FREEZE_TARGETS = [
    "vendor/agent_core/harness.py",
    "vendor/agent_core/song_catalog.py",
    "vendor/agent_core/voice_text.py",
    "vendor/agent_core/data/luotianyi_original_songs.json",
    "acceptance/evals/scenarios.json",
]

$ git show HEAD:acceptance/gates/g0_freeze.py | sed -n '15,21p' | grep -c "MANIFEST.json"
0
```

`acceptance/MANIFEST.json` 不在 `FREEZE_TARGETS` 里。第 14 行只把它当成读取路径常量：

```python
MANIFEST = REPO / "acceptance" / "MANIFEST.json"
```

后果：改写 MANIFEST 本身不会触发任何闸门。把 `harness.py` 那条期望值直接改成磁盘实际值，`g0_freeze` 立刻 PASS，而闸门无法分辨这是「主仓侧裁决后的合法重算」还是「任务方为了让自己的闸门变绿而偷改锁文件」——两者字节层面完全等价。

这正是本仓侧规则第 10 条要防的动作（「改闸门让自己的任务变绿 = 直接拒收」）。本仓侧全程没做，但**闸门本身没有任何机制阻止别人做**，只能靠人的自觉与事后 `git diff` 复核。

**现象 2：`--update` 零摩擦、零守卫**

```
$ git show HEAD:acceptance/gates/g0_freeze.py | grep -n "confirm\|input(\|--dry\|backup\|diff\|audit\|permission\|getpass"
47:    if "--update" in sys.argv:
```

全文件只命中 `--update` 这个字符串本身，没有任何确认、备份、审计、权限相关代码。第 47–51 行全文：

```python
if "--update" in sys.argv:
    manifest = {rel: sha256(REPO / rel) for rel in FREEZE_TARGETS if (REPO / rel).is_file()}
    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("MANIFEST updated:", len(manifest), "entries")
    sys.exit(0)
```

四行代码，五个缺失：

| 缺失 | 后果 |
|---|---|
| 无确认提示 | 一条命令即生效，没有「你确定要重算冻结基准吗」这一步 |
| 无 diff 回显 | 只 `print("MANIFEST updated:", N, "entries")`，不告诉调用者**哪几条变了、从什么变成什么**。集成前那次漂移如果被人顺手 `--update`，他根本不会知道自己刚刚把 `219691…` 换成了 `cb1ae928…` |
| 无备份 | 旧 MANIFEST 直接丢失。虽然 git 能找回，但这依赖仓库是干净的且调用者知道去查 |
| 无审计留存 | 不写 evidence JSON、不记时间戳、不记调用者。`run_all.py` 会写 `evidence/run_*.json`，`--update` 什么都不写 |
| 无权限校验 | 任何能跑 Python 的人都能重算冻结基准，与「只能由主仓侧裁决」的流程要求脱节 |

**现象 3：校验路径与更新路径对「文件丢失」的处理不一致**

第 48 行的 `if (REPO / rel).is_file()` 是字典推导里的静默过滤器：某个冻结件从磁盘上消失时，`--update` 会**把它从 MANIFEST 里剔除**，然后照常 `sys.exit(0)`、照常打印条目数（只是数字变小）。

而校验路径第 35–37 行对同一情形的处理是报错：

```python
if not path.is_file():
    problems.append(f"{rel}: missing")
```

于是出现一个自我削弱的循环：删掉一个冻结件 → 跑 `--update` → 该条目从 MANIFEST 消失 → 再跑校验，`for rel in FREEZE_TARGETS` 仍会遍历到它并报 `missing`（因为 FREEZE_TARGETS 是硬编码的），**但如果同时改的正是 FREEZE_TARGETS 本身**（它也不在任何锁里），冻结面就能无声缩小。`acceptance/gates/g0_freeze.py` 既不在 FREEZE_TARGETS 里，也不在 MANIFEST 里——**闸门自己和自己的清单都不受自己保护**。

**请主仓侧裁决**：

1. 把 `acceptance/MANIFEST.json` 与 `acceptance/gates/g0_freeze.py` 纳入某种完整性校验。直接把它们加进 `FREEZE_TARGETS` 会自指（MANIFEST 无法记自己的 sha256），可行做法是另建一份 `acceptance/MANIFEST.lock`（记 MANIFEST 与各闸门脚本的 sha256，自身不记），或引入签名 / 双人复核。
2. `--update` 至少补三样：改动前的 diff 回显（哪几条从什么变成什么）、旧文件备份、一条审计记录（时间戳 + 当前 commit + 变更条目）。这三样都不改变闸门判定逻辑，只是让「重算冻结基准」这个动作留下可追溯痕迹。
3. 第 48 行的静默剔除改为显式失败：`--update` 时若某个 `FREEZE_TARGETS` 条目在磁盘上不存在，应报错退出而不是把它从清单里删掉。

---

## 三、eol 与 git 语义裂缝

### 条目 F：`git checkout --` 对「clean 过滤后等价于 index」的文件是 no-op【HIGH·待裁决】

**现象**：当工作树字节的行尾形态与 index blob 不同、但经 clean 过滤器折算后与 index blob 相同时，git 认定该文件未修改。此时 `git checkout -- <path>` 退出码 0、**不改写一个字节**，行尾矛盾态无法用常规手段消除。

**证据：`<tmp>` 仓库副本上的完整复现**

副本由 `git clone --local <repo> <tmp>/eol_noop_exp2` 得来，真仓库全程未被写入。实验对象是 `acceptance/evals/scenarios.json`（5 个冻结件里唯一曾经用 CRLF 的那一个）。

```
=== 步骤0 副本基线 ===
HEAD=（集成后 HEAD）  worktree bytes=2752  CR=0
git status --porcelain --untracked-files=no: []

=== 步骤1 复现集成前状态：本地 attributes 强制 eol=crlf 后重检出 ===
$ printf '%s text eol=crlf\n' acceptance/evals/scenarios.json > .git/info/attributes
$ rm -f $P; git checkout HEAD -- $P
worktree bytes=2870  CR=118  sha256=01ed805ae688e431..
git status --porcelain: []                      ← clean
git ls-files --eol: i/lf  w/crlf  attr/text eol=crlf

=== 步骤2 撤销本地规则（模拟集成后 .gitattributes 的 eol=lf 生效） ===
$ rm -f .git/info/attributes
git status --porcelain: []                      ← 仍 clean
git ls-files --eol: i/lf  w/crlf  attr/text=auto eol=lf   ← 矛盾态
worktree 仍是 CRLF: bytes=2870 CR=118

=== 步骤3 关键实验：git checkout -- 是否 no-op ===
$ git checkout -- acceptance/evals/scenarios.json
exit=0
before=01ed805ae688e431a8f09bf64d21d445cdf26e85843c6fd9d08b58332df42e67
after =01ed805ae688e431a8f09bf64d21d445cdf26e85843c6fd9d08b58332df42e67
字节变化=NO（no-op 成立）
after: bytes=2870 CR=118                        ← 一个字节都没动

=== 步骤4 对照：rm + git checkout HEAD -- ===
$ rm -f $P; git checkout HEAD -- $P
bytes=2752 CR=0 sha256=2c5dab3fc5e41468..       ← 这才真重检出为 LF
```

`git ls-files --eol` 在步骤 2 之后打出的 `i/lf w/crlf attr/text=auto eol=lf` 就是这个矛盾态的完整刻画：index 是 LF、工作树是 CRLF、而属性要求 LF。git 自己把矛盾显示出来了，却仍认为文件 clean、`git checkout --` 仍不动它。

**机制解释**

```
=== 步骤5 hash-object 双向对照 ===
with filters   : 53ab5c2bf54027f3e333e0f980259acbe0e72150
--no-filters   : 76b7280d793bd18c614e6ad2e838f1983d842019
index sha      : 53ab5c2bf54027f3e333e0f980259acbe0e72150
HEAD blob sha  : 53ab5c2bf54027f3e333e0f980259acbe0e72150
git status     : []
```

`git hash-object`（默认走 clean 过滤器）算出 `53ab5c2b…`，与 index sha、HEAD blob sha 三者全等；`--no-filters`（直接算磁盘字节）算出 `76b7280d…`，与 blob 不等。git 的「是否修改」判据用的是**前者**，所以它认定 clean。`git checkout --` 的语义是「把 index 里的内容检出到工作树，用于丢弃本地修改」，既然 git 认定没有本地修改，它就没有理由重写文件——no-op 是语义自洽的结果，不是 bug。

**本仓侧必须如实交代的一处偏差**

上一轮取证第一次做这个实验时用错了触发方式：直接用 Python 往工作树写 CRLF 字节，得到的结果与上述**相反**——`git status --porcelain` 报了 ` M acceptance/evals/scenarios.json`，`git checkout --` exit=0 且**成功重检出为 LF**（2870 → 2752 bytes，CR 118 → 0）。本轮改用正确触发方式（先设 `.git/info/attributes` 再 `rm` + `git checkout HEAD --`，让 git 自己写入文件并更新 index 的 stat 缓存）后，no-op 完整复现。

两种结果的差别精确界定了 no-op 的成立条件：

| 触发方式 | index stat 缓存 | `git status` | `git checkout --` |
|---|---|---|---|
| 由 git 自己写入（checkout / 改 attributes 后重检出） | 有效（mtime/size/ino 与 index 记录一致） | clean | **no-op**（矛盾态无法消除） |
| 由外部程序写入（Python `write_bytes`、编辑器保存、脚本改行尾） | 失效（mtime 变了） | ` M` | 真重检出（矛盾态被消除） |

所以准确的表述是：**`git checkout --` 对「git 认定 clean」的文件是 no-op，而 eol 属性会让「磁盘字节 ≠ index 字节」的文件仍被认定为 clean**。这个 no-op 只在 stat 缓存有效时成立；一旦有外部程序碰过文件（哪怕写回同样字节但改了 mtime），git 就会重新比对——但重新比对用的仍是 clean 过滤后的值，所以结论依旧是 clean，`git checkout --` 依旧 no-op。上表第二行之所以能真重检出，是因为那次实验里 git 在 ` M` 状态下比对的是「clean 过滤后 = index」但**旧属性规则仍在缓存里**的组合，属于特例；把它当成通用结论会误导排除故障的人。集成时真正会遇到的是第一行。

**危害**

1. 与条目 B 联动成死角：闸门报 `scenarios.json: content drifted`，而 `git status` 说 clean、`git checkout --` 不管用。排除故障的人若不知道要 `rm` + `git checkout HEAD --`，会一直卡在「闸门红、git 绿」的矛盾里，最省事的出路恰好是规则第 10 条禁止的那条——跑 `g0_freeze.py --update` 把 MANIFEST 改成磁盘现状（条目 C 说明这一步零摩擦）。
2. 这条正确处置手法（`rm` + `git checkout HEAD -- <path>`）**不在任何文档里**。`INTEGRATION.md`、`evidence/README.md`、`.gitattributes` 的注释都没有提到 eol 策略变更后需要强制重检出。
3. 集成后真仓库已不在矛盾态里（`scenarios.json` 现为 2752 bytes / CR=0，`i/lf w/lf attr/text=auto eol=lf`，`.git/info/attributes` 文件已不存在），所以**这一条现在不阻塞任何事**。它登记的是「下一次行尾策略变更时会重现的坑」，以及在别的机器上做同样 rebase 的人此刻可能正卡在里面。

**请主仓侧裁决**：在集成说明（`INTEGRATION.md` 或 `.gitattributes` 旁的注释）里写明：变更 eol 属性后，`git status` 报 clean 不代表工作树字节已符合新属性，`git checkout -- <path>` 在此情形下是 no-op，必须 `rm <path>` 后 `git checkout HEAD -- <path>` 才会按新属性重检出；并给出用 `git ls-files --eol` 的 `i/` 与 `w/` 两列自检矛盾态的方法。

---

## 四、`run_all.py` 编排器缺陷

### 条目 7：verdict 逻辑使 `--strict` 在存在 FAIL 时零信息量

**现象**：普通模式与 `--strict` 输出逐字节同构（闸门状态、verdict、exit code 全部相同），`--strict` 的差异化分支（BLOCKED）永不触发。

**证据**：源码第 49 行：

```python
verdict = "FAIL" if any(r["status"] == "FAIL" for r in results) else ("PENDING-OK" if not strict else ("PASS" if all(r["status"] == "PASS" for r in results) else "BLOCKED"))
```

第 63 行：

```python
return 1 if verdict == "FAIL" or (strict and verdict == "BLOCKED") else 0
```

真值表（用 `run_all.py` 第 49 行逻辑模拟）：

```
场景                              | 普通 verdict   | 普通 exit | strict verdict | strict exit
Current (g0_freeze FAIL)          | FAIL           | 1         | FAIL           | 1
After upstream fix (PENDING only) | PENDING-OK     | 0         | BLOCKED        | 1
All tasks complete                | PENDING-OK     | 0         | PASS           | 0
```

实测验证（当前仓库，两种模式闸门状态逐格相同）：

```
$ ./.venv/bin/python acceptance/run_all.py 2>&1 | grep -E "^(PASS|FAIL|PENDING)" | sort
FAIL     g0_freeze
PASS     g0_environment
PASS     g0_secrets
PASS     g1_contract
PASS     g1_memory
PASS     g3_simulate
PENDING  g1_permissions
PENDING  g1_tools

$ ./.venv/bin/python acceptance/run_all.py --strict 2>&1 | grep -E "^(PASS|FAIL|PENDING)" | sort
（逐行相同）
```

**影响**：strict 模式的独立证据价值只在「无 FAIL 有 PENDING」状态下才体现。当存在 FAIL 时，跑 `--strict` 与不跑完全等价，DoD 里要求「strict 全绿」的可达性被非本任务包控制的闸门绑架。

**建议裁决**：明确 strict 的语义应否在存在 FAIL 时仍产出区分性结论（例如 verdict 改为 `FAIL+BLOCKED` 或在输出里标注哪些 PENDING 是 strict 独有的阻塞项）。

### 条目 8：evidence 文件名只到秒级、同秒覆盖无告警

**现象**：同一秒内先后跑普通模式与 `--strict`，第一份 JSON 被静默覆盖。

**证据**：源码第 59 行：

```python
evidence = evidence_dir / f"run_{time.strftime('%Y%m%d_%H%M%S')}.json"
```

粒度只到秒。第 60 行 `evidence.write_text(...)` 无冲突检测、无覆盖告警。

既有取证实测（`evidence/task_b_gate_matrix.md` 第 2 节）：R1 普通模式与 strict 在同一秒（17:41:56）完成，落盘只有 1 个 JSON（`"strict": true`），普通模式那份已不存在。

**影响**：证据留存不完整。派单预期「3 轮 × 2 模式 = 6 个 JSON」实际落盘 5 个。

**建议裁决**：文件名加毫秒（`%H%M%S_%f`）或模式后缀（`_strict`），或覆盖前检测并告警。

### 条目 9：子进程 stderr 被丢弃

**现象**：闸门崩溃时 evidence JSON 里 FAIL 项的 detail 是空字符串。

**证据**：源码第 42–44 行：

```python
proc = subprocess.run([sys.executable, REPO / rel], cwd=REPO, capture_output=True, text=True, timeout=120, env=env)
status = "PASS" if proc.returncode == 0 else "PENDING" if proc.returncode == 2 else "FAIL"
results.append({"gate": name, "status": status, "detail": proc.stdout.strip()[-400:]})
```

`capture_output=True` 捕获了 stderr，但 `detail` 只取 `proc.stdout.strip()[-400:]`。`proc.stderr` 从未被使用。

**影响**：若闸门因 Python 异常崩溃（traceback 走 stderr），evidence JSON 的 detail 为空，诊断必须逐个单独跑闸门才能看到 traceback。

**建议裁决**：detail 里保留 stderr 尾部（例如 `proc.stdout[-200:] + proc.stderr[-200:]`）。

### 条目 10：`GATES` 列表不含单元测试

**现象**：`tests/` 下的 204 个用例完全不在 DoD 判定路径上。

**证据**：源码第 17–26 行：

```python
GATES = [
    ("g0_environment", "acceptance/gates/g0_environment.py"),
    ("g0_secrets", "acceptance/gates/g0_secrets.py"),
    ("g0_freeze", "acceptance/gates/g0_freeze.py"),
    ("g1_contract", "acceptance/gates/g1_contract.py"),
    ("g1_memory", "acceptance/gates/g1_memory.py"),
    ("g1_permissions", "acceptance/gates/g1_permissions.py"),
    ("g1_tools", "acceptance/gates/g1_tools.py"),
    ("g3_simulate", "acceptance/gates/g3_simulate.py"),
]
```

8 个条目，无 `unittest discover`。README 第 19 行把 `python -m unittest discover -s tests` 列为快速开始的第三步，但它不参与 verdict 计算。

**影响**：与条目 11 合起来构成最严重的 Goodhart 敞口——反过拟合的唯一防线（留出集 + 结构测试）不在 DoD 判定路径上。

**建议裁决**：把 `unittest discover` 纳入 GATES（exit 0 = PASS, 非 0 = FAIL），或让 `g1_memory` 内建留出集切分。

---

## 五、评测体系的反 Goodhart 敞口

### 条目 11：`g1_memory` 只用内联 8 对 GOLDEN，留出集不进闸门

**现象**：`g1_memory.py` 第 18–27 行内联 8 对 GOLDEN，第 51 行调 `score_retrieval(GOLDEN)`，第 55 行判 `precision < 0.8 or recall < 0.8`。从不引用 `tests/holdout_v2.py` 或 `tests/test_memory_retrieval.py` 里的留出集。

**证据**：源码第 51–56 行：

```python
result = score_retrieval(GOLDEN)
if result is None:
    pending.append("retrieval quality: score_retrieval() not implemented (Task B)")
else:
    if result.get("precision", 0) < 0.8 or result.get("recall", 0) < 0.8:
        problems.append(f"retrieval quality below 0.8: {result}")
```

### 条目 12：实测证据——清空概念词典后闸门仍 PASS

在仓库外副本（`<tmp>`）里做隔离实验，真仓库一个字节未动。

**手法**：把 `src/memory_lexicon.py` 里 8 个概念类的 `member=(...)` 全部替换为 `member=()`（保留类名与 head），等价于摘掉 L3 的 member 级桥接。

```
$ ./.venv/bin/python -c "
import re; from pathlib import Path
p=Path('src/memory_lexicon.py'); text=p.read_text()
result=re.sub(r'member=\([^)]*\)','member=()',text,flags=re.DOTALL)
p.write_text(result)
print(f'Replaced 8 member tuples')
"
```

**结果**：

```
$ ./.venv/bin/python acceptance/gates/g1_memory.py
G1_MEMORY: PASS
EXIT=0

$ ./.venv/bin/python -c "
import sys; sys.path.insert(0,'.')
from src.memory_store import score_retrieval
GOLDEN=[...8 对，同 g1_memory.py 第 18-27 行...]
print(score_retrieval(GOLDEN))
"
{'precision': 1.0, 'recall': 1.0}

$ ./.venv/bin/python -m unittest tests.test_memory_retrieval 2>&1 | tail -5
AssertionError: 0.6666666666666666 not greater than or equal to 0.8
Ran 86 tests in 0.254s
FAILED (failures=7)

$ ./.venv/bin/python -m unittest discover -s tests 2>&1 | grep -E "^(Ran|FAILED)"
Ran 204 tests in 0.155s
FAILED (failures=24)

$ ./.venv/bin/python acceptance/run_all.py 2>&1 | grep -E "^(PASS|FAIL|PENDING)"
（8 闸门状态与基线逐格相同，g1_memory 仍 PASS）
```

**结论**：一个 golden 1.000 / 留出集 0.667 的过拟合实现可以通过全部 8 个验收闸门。24 个单测失败，但单测不在 GATES 里。

### 条目 13：阈值判别力

golden 8 条 × 阈值 0.8：

- 错 0 条 = 1.000 PASS
- 错 1 条 = 0.875 PASS（7/8 = 0.875 ≥ 0.8）
- 错 2 条 = 0.750 FAIL（6/8 = 0.75 < 0.8）

判别余量恰好 1 个样本。且 0.875 与 1.000 在闸门输出里同样只显示 `G1_MEMORY: PASS`，看不出已丢一条。

实测佐证：上述清空词典实验里 golden 仍拿 1.000（当前实现的其它层足以覆盖 golden 8 对），但留出集掉到 0.667。golden 对这种退化完全不敏感。

**建议裁决**：闸门输出应打印实际 P/R 数值（例如 `G1_MEMORY: PASS precision=1.000 recall=1.000`），或提高 golden 规模使判别余量 > 1。

### 条目 14：建议裁决方向

- 把 `unittest discover` 纳入 `run_all.py` 的 GATES
- 或让 `g1_memory` 内建一个留出集切分（从 `tests/holdout_v2.py` import）
- 闸门输出回显实测 P/R 数值而不只是 PASS/FAIL

---

## 六、`sabotage_drill.py` 的缺陷

### 条目 15：无「破坏前 gate 须为绿」的前置断言

**现象**：`drill()` 的判据只是"破坏后返回码 != 0"。若目标 gate 因别的原因已经是红的，恒判"检出"。

**证据**：源码第 24–35 行：

```python
def drill(name: str, target: Path, old: str, new: str, gate: str) -> bool:
    original = target.read_bytes()
    try:
        text = original.decode("utf-8")
        if old not in text:
            print(f"DRILL {name}: SKIP (anchor not found)")
            return False
        target.write_bytes(text.replace(old, new).encode("utf-8"))
        if run_gate(gate) == 0:
            print(f"DRILL {name}: NOT DETECTED - gates have no teeth")
            return False
        return True
    finally:
        target.write_bytes(original)
```

无任何一行在破坏之前先跑 gate 确认它是绿的。

**假阳性实例**：第 3 路 `eval-tamper` 检的是 `g0_freeze`，而 `g0_freeze` 因 harness.py 漂移在 drill 之前就已经是 FAIL/1。即使 `scenarios.json` 一个字节都没改，`run_gate("acceptance/gates/g0_freeze.py") != 0` 恒成立，drill 恒返回 True。

```
$ ./.venv/bin/python acceptance/sabotage_drill.py
DRILLS DETECTED: 3 of 3
EXIT=0
```

`3 of 3` 的有效检出实际是 **2/3**（prompt-fact-sabotage / g1_contract 与 memory-sabotage / g1_memory 两路目标闸门破坏前为 PASS/0，归因成立；eval-tamper 路不可归因）。

> **⚠ 集成后状态变化（必读）**：以上「假阳性 / 有效检出 2/3」是**集成前的结论，现已不再成立**。上游修复落地后 `g0_freeze` 实测转 PASS（退出码 0），三路的前置绿条件现在全部满足。缺陷（无前置断言）本身仍在源码里，但它当下不再产生假阳性。详见本章末的**条目 D**。

### 条目 16：仓库外副本隔离实验——证明 g0_freeze 对 scenarios.json 确有牙齿

在 `<tmp>` 副本里：把 MANIFEST 的 harness.py 期望值改成实际值使 `g0_freeze` 变绿 → 字节级篡改 scenarios.json 一个 id → 观察 g0_freeze 翻红 → 恢复后回绿。

```
Step A: Fix MANIFEST → g0_freeze PASS (exit 0)
  Old MANIFEST value: 219691162b9f09b8e544acaff6a39ac613ba2027d5b2ba9b2713875934ea8da5
  Actual file hash:   cb1ae928f80674952c4ac6e6385d260a7dbd5cf93ac5ab96889ff6bdb32b2807
  G0_FREEZE: PASS / EXIT=0

Step B: Byte-level tamper "identity-01" → "identity-01x" (+1 byte)
  Before: 2870 bytes / After: 2871 bytes
  acceptance/evals/scenarios.json: content drifted from frozen manifest / EXIT=1

Step C: git checkout -- acceptance/evals/scenarios.json
  G0_FREEZE: PASS / EXIT=0
```

结论：g0_freeze 对 scenarios.json 篡改确有牙齿，只是 drill 的编排（无前置绿断言 + g0_freeze 本来就红）无法展示这一点。

### 条目 17：恢复后复验是死代码

**现象**：`RESTORE FAILED` 分支在任何输入下都不可能打印。

**证据**：源码第 36–43 行：

```python
    finally:
        target.write_bytes(original)
    for cache in [REPO / "vendor/agent_core/__pycache__", ...]:
        shutil.rmtree(cache, ignore_errors=True)
    if run_gate(gate) != 0:
        print(f"DRILL {name}: RESTORE FAILED - gate still red after restore")
        return False
    return True
```

`try` 块内第 35 行 `return True`（或第 30/34 行 `return False`）先触发 `finally`（第 37 行恢复字节），然后直接把值返回给调用方。Python 语义：`finally` 之后的语句（第 38–43 行）永不执行。

**集成后补钉死的证据（条目 D 的一部分）：用 AST 静态分析而非口头推断**

上一版只用 Python 语义口头论证，本轮把 `drill()` 的语法树解析出来，逐行确认控制流：

```
$ ./.venv/bin/python -c "…ast.parse(git show HEAD:acceptance/sabotage_drill.py)…"
drill() 行范围: 24-43
try 块行范围: 26-35
finally 行范围: 37-37
try 之后的兄弟语句（即 finally 之后的顶层语句）: [(38, 39, 'For'), (40, 42, 'If'), (43, 43, 'Return')]
try 块内 return 行号: [35, 30, 34]
finally 块内 return 行号: []  (空=finally 不 return)
try body 是否所有分支都以 return 收尾: True
=> finally 之后的第 38-43 行在 Python 语义下不可达: True
```

三个判据全部成立：① `try` body 的每条分支都以 `return` 收尾（第 30 行 SKIP、第 34 行 NOT DETECTED、第 35 行成功）；② `finally` 块内没有 `return`（若有，它会覆盖 `try` 的返回值并改变控制流）；③ 第 38–43 行在语法树上是 `try` 语句的**兄弟节点**（`For` / `If` / `Return`），位于其后。三者合起来意味着：函数在到达第 38 行之前已经返回，这 6 行在任何输入下都不执行。

**运行时旁证**：`RESTORE FAILED` 这个字符串在全仓库的命中全部是源码本身与取证文档对它的引用，**没有任何一处是 drill 的实际输出**：

```
$ grep -rn "RESTORE FAILED" .
./acceptance/sabotage_drill.py:41:        print(f"DRILL {name}: RESTORE FAILED - …")   ← 源码本体
./evidence/task_b_sabotage_drill.md:88,92                                            ← 取证文档引用
./evidence/task_b_final_selfcheck.md:140                                           ← 发现清单引用
./evidence/task_b_gate_objections.md:…                                             ← 本卷宗引用
```

`evidence/task_b_sabotage_drill.log`（drill 本体的完整 stdout 留存）里没有这个字符串——它只有一行 `DRILLS DETECTED: 3 of 3`。这与静态分析的结论一致。

**影响**：drill 的 docstring 声称 "restores the original bytes, requires green again"，后半句从未被执行。"恢复后回绿"必须由人工另行验证。

**建议裁决**：把复验逻辑移入正确的控制流位置（例如在 `finally` 块内恢复后紧接复跑，或重构为非 try/finally 结构）。

### 条目 18：`run_gate()` 丢弃闸门 stdout/stderr

**证据**：源码第 19–21 行：

```python
def run_gate(rel: str) -> int:
    proc = subprocess.run([PY, REPO / rel], cwd=REPO, capture_output=True, text=True, timeout=120)
    return proc.returncode
```

`capture_output=True` 捕获了 stdout 与 stderr，但只返回 returncode，两个流都不打印。加上 `drill()` 只在 SKIP / NOT DETECTED / RESTORE FAILED 三种失败情形下才 print，三路全部"成功"时整个 drill 的 stdout 只有：

```
DRILLS DETECTED: 3 of 3
```

无法审计跑了哪几路、每路闸门红在哪一行、红的原因是不是预期的那条。

**建议裁决**：每路打印闸门输出（至少 stdout 首行），或写入 evidence JSON。

### 条目 19：drill 用文本模式改写目标文件，CRLF 归一化风险

**现象**：`acceptance/evals/scenarios.json` 是 CRLF 文件（118 处 CRLF，2870 字节）。drill 第 27 行 `original.decode("utf-8")` 后第 31 行 `text.replace(...).encode("utf-8")` 写回——Python 的 `str.encode` 不会自动恢复 CRLF，篡改期间文件从 2870 字节变成 2753 字节（−118 行尾 +1 锚点字符 = −117）。

**上游 `.gitattributes` 统一 LF 后的风险变化**：

- **降低的部分**：rebase 集成后 scenarios.json 将以 LF 检出（`.gitattributes` 的 `* text=auto eol=lf`），不再有 CRLF→LF 的整体改写。篡改期间的字节变化将真正只是"改了一个 id"（+1 字节）。
- **未消除的部分**：若 drill 进程在破坏窗口内被 SIGKILL，`finally` 不执行，仓库会留下一个半破坏的冻结件（锚点已改但未恢复）。此后 `g0_freeze` 永久 FAIL 且极难归因（因为 drill 不打印闸门输出、不写 evidence）。这个风险与行尾无关。

**建议裁决**：drill 改用字节模式做定点替换（`original.replace(old_bytes, new_bytes)` 而非 decode→replace→encode），并在破坏前写一份 `.bak` 到仓库外。

### 条目 20：drill 不写 evidence JSON

`evidence/README.md` 规则 2：「演练（sabotage_drill.py）输出证据必须留存」。但 drill 只打印 stdout，不写任何 JSON 文件。留存只能靠人工 `tee`。

*建议裁决**：drill 结束时写一份 JSON（含三路各自的闸门输出、returncode、时间戳），或在 `evidence/README.md` 里明确豁免 drill 的 JSON 要求。

---

### 条目 D：集成后的状态更新——假阳性结论已失效，死代码已静态钉死【MEDIUM·状态已变】

本条目不是一条新缺陷，而是对条目 15 与条目 17 的**现状更新**。单独登记是为了防止旧结论被继续引用。

#### D-1：条目 15 的假阳性推论在集成后已不成立

**集成前的事实链**（当时的结论，现已过期）：

| 环节 | 集成前实测 |
|---|---|
| `g0_freeze` 退出码 | 1（FAIL，因 harness.py 漂移） |
| drill 第 3 路的目标闸门 | `g0_freeze` |
| 破坏前该闸门是否绿 | **否**（本来就红） |
| 结论 | `run_gate(g0_freeze) != 0` 恒成立 ⇒ eval-tamper 路是假阳性 ⇒ 有效检出 2/3 |

**集成后的事实链**（本轮实测）：

| 环节 | 集成后实测 |
|---|---|
| `g0_freeze` 退出码 | **0（PASS）**，5/5 冻结件 sha256 匹配 MANIFEST |
| `g1_contract` 退出码 | 0（PASS） |
| `g1_memory` 退出码 | 0（PASS） |
| 三路目标闸门破坏前是否全绿 | **是，三路全部满足** |
| 结论 | 假阳性的**触发条件已消失**。若现在重跑 drill，三路的「检出」都可归因于破坏本身 |

**必须严格区分两件事**：

1. **缺陷仍在**。`drill()` 第 24–35 行依旧没有任何一行在破坏之前先跑 gate 确认它是绿的（源码未动，`git diff $BOOTSTRAP..HEAD -- acceptance/sabotage_drill.py` 为空）。只要将来任何一个目标闸门因其他原因变红，假阳性会立即重现。条目 15 的裁决请求（加前置绿断言）**依旧有效，不应因集成而关闭**。
2. **结论已过期**。「`DRILLS DETECTED: 3 of 3` 里 eval-tamper 是假阳性、有效检出实为 2/3」这句话描述的是集成前那次 drill 跑的具体结果，对当前仓库状态**不再成立**。引用它时必须带时间限定。

**本轮不重跑 drill 的理由**：`sabotage_drill.py` 会临时改写冻结件（第 31 行 `target.write_bytes(...)`），仅在 `finally` 里恢复。当前有并行工作正在改 `src/`、`tests/` 与 `evidence/` 下的其他文档，drill 的破坏窗口（即使只有几百毫秒）若与并行写入重叠，会造成无法归因的互相污染；且条目 17 已证明「恢复后复验」是死代码，drill 自己不会告诉我恢复是否真的成功。因此：

> **集成后需重跑 drill 以确认有效检出是否变为真正的 3/3，实测留待 QA 的最终取证轮。** 重跑时应同时记录：三路各自的目标闸门在破坏前的退出码（补上 drill 缺失的前置断言，用外部快照代替）、drill 前后 5 个冻结件的 sha256 对照、以及 `git status --porcelain --untracked-files=no` 是否为空。

#### D-2：条目 17 的死代码已用 AST 静态证明钉死

见条目 17 内新增的「集成后补钉死的证据」一段：语法树分析给出三个判据（`try` body 全分支以 `return` 收尾、`finally` 不 `return`、第 38–43 行是 `try` 的兄弟节点），结论 `不可达: True`；运行时旁证是全仓库无任何一处 `RESTORE FAILED` 的实际输出。

这一部分与集成无关（源码未动），属于**证据强度提升**：从「按 Python 语义推断」变成「语法树静态判定 + 历史输出旁证」。

#### D-3：一个附带发现：`__pycache__` 清理也一并失效

第 38–39 行清理三个 `__pycache__` 目录的意图随不可达而失效。实测这一路不影响结论：Python 的 .pyc 失效判据是源文件 mtime+size，drill 三路破坏都改变了文件字节数（harness.py −3、memory_store.py +5、scenarios.json −117），不存在同秒同尺寸导致读到陈旧 .pyc 的窗口；且 `scenarios.json` 是被 `read_text` 读的数据文件，根本不走 import 缓存。但若将来 drill 改成「不改字节数的破坏」（例如把 `True` 改成 `1`），这个失效就会变成真风险。

**请主仓侧裁决**：确认 drill 是否需在前置绿条件下重跑一次以给出真正的 3/3 判定；若重跑，建议同时把前置绿断言补进 `drill()`（即使只补这一行，也能让本次重跑的结果自证有效）。

---

## 七、证据体系自身的规则冲突

### 条目 21：「保留最后 10 条」规则与实现冲突

**现象**：`evidence/README.md` 规则 3 要求「提交前删除过期运行记录，保留最后 10 条」，但 `run_all.py` 无任何裁剪逻辑，且 `run_*.json` 被 `.gitignore` 忽略。

**证据**：

```
$ cat evidence/README.md
规则：
1. `run_all.py --strict` 的证据必须留存（DoD 必需）
2. 演练（sabotage_drill.py）输出证据必须留存
3. 提交前删除过期运行记录，保留最后 10 条

$ cat .gitignore
.venv*/
__pycache__/
*.pyc
evidence/run_*.json

$ ls evidence/run_*.json | wc -l
52
```

当前 52 个 `run_*.json`（本轮最后一次实测时点）。集成前那次取证记的是 20 个，这个数**只增不减**——`run_all.py` 每跑一次就多落一个，而裁剪逻辑一行都没有，52 已经是「保留最后 10 条」上限的 5 倍以上。但它们被 `.gitignore` 忽略，不会进入 commit，对主仓侧根本不可见——"保留"这个规则既无法被执行（没有裁剪代码），也无法被核查（push 后远端看不到这些文件）。**从 20 涨到 52 这个过程本身就是条目 21 最直接的证据**：中间没有任何一个环节做过裁剪或告警。

**影响**：规则本身是空文。若主仓侧需要审计运行历史，必须另行约定可跟踪的证据格式。

**建议裁决**：三选一——① 在 `run_all.py` 里实现裁剪（写完后删旧的）；② 改 `evidence/README.md` 的规则（删除第 3 条或改为"本地保留，不入库"）；③ 把关键运行的 JSON 改为可跟踪（从 `.gitignore` 里排除特定前缀）。

### 条目 22：闸门扫描盲区

**现象**：`tests/` 与 `evidence/` 两个目录不在任何闸门的扫描范围内，而这两个目录下有要 push 的交付物。

**证据**：

`g0_environment.py` 第 10 行：
```python
SCAN_DIRS = ["src", "acceptance", "tasks"]
```

`g0_secrets.py` 第 9 行与第 17 行：
```python
SCAN_DIRS = ["src", "acceptance", "tasks", "docs", "vendor"]
SCAN_SUFFIXES = {".py", ".json", ".md", ".txt", ".cfg", ".toml"}
```

盲区 ①：`tests/` 与 `evidence/` 都不在 `SCAN_DIRS` 里。这两个目录下的交付物会被 push 到公开仓库，但绝对路径检查与密钥检查对它们完全不覆盖。集成后重测的规模（并行工作拆分过测试文件，数字比集成前变大）：

```
$ git ls-files tests | wc -l            → 15 个 tracked 文件
$ git ls-files tests | xargs wc -l      → 5494 行合计
$ git ls-files evidence | wc -l         → 3 个 tracked（README.md、task_b_integration.md、task_b_retrieval_analysis.md）
$ ls -1 evidence/*.md | wc -l           → 9 个（含 untracked 取证文档）
$ ls -1 evidence/*.log | wc -l          → 13 个（全部 untracked）
```

（上一版写的是「`tests/` 9 个 tracked 文件、合计 3307 行」与「`evidence/` 21 个 .md/.log」，那是集成前的数字；并行工作把一个大测试文件拆成了三个，并新增了取证文档。以本轮实测为准。）

盲区 ②：`g0_secrets` 的 `SCAN_SUFFIXES` 不含 `.log`，而 `evidence/` 下有 13 个 `.log` 文件。即使把 `evidence/` 加入 SCAN_DIRS，.log 文件仍会被后缀过滤跳过。

盲区 ③（**本轮新发现，不在上一版里**）：`g0_environment.py` 第 44 行的 Windows 盘符 needle **因双重转义而基本失效**。

源码结构（第 43–46 行；四个 needle 按记号约定写作 `NEEDLE0`…`NEEDLE3`，原文用 `git show HEAD:acceptance/gates/g0_environment.py | sed -n '43,46p'` 核对）：

```python
        problems.append(f"{rel}: file exceeds 800 lines")
    for needle in (NEEDLE0, NEEDLE1, NEEDLE2, NEEDLE3):
        if needle in text and "acceptance" not in rel:
            problems.append(f"{rel}: hard-coded absolute path {needle!r}")
```

用 `ast` 解析出 needle 元组的**真实字符串值**，但**不打印字面量本身**，只打印每个值的长度、反斜杠个数与字符构成（打印字面量就会把真实路径前缀写进本卷宗）；再拿五类样本逐个试：

```
needle 元组结构（ast 解析结果）:
  NEEDLE0  长度=4  反斜杠数=2  构成 = 盘符字母 + 冒号 + 反斜杠×2   ← 问题在这里
  NEEDLE1  长度=4  反斜杠数=2  构成 = 盘符字母 + 冒号 + 反斜杠×2   ← 问题在这里
  NEEDLE2  长度=7  反斜杠数=0  构成 = <home-prefix>/
  NEEDLE3  长度=8  反斜杠数=0  构成 = 盘符字母 + 冒号 + 正斜杠 + Users

样本                                命中 needle            结果
真实 Windows 路径（单反斜杠）      []                     漏检
JSON/正则里的双反斜杠             [NEEDLE0]              检出
macOS 家目录 <home-prefix>/…      [NEEDLE2]              检出
盘符 + 冒号 + 正斜杠 + Users…     [NEEDLE2, NEEDLE3]     检出
```

根因：作者想匹配 `<win-drive>:\`（盘符 + 冒号 + **一个**反斜杠），在 Python 源码里应写**两个**反斜杠的转义形式（其值 = 单反斜杠），但实际写了**四个**（其值 = 双反斜杠）——多转了一层。后果：`open(r"<win-drive>:\data\x.json")` 这类**常规 Windows 硬编码路径完全检不到**，只有源码里字面写了双反斜杠的罕见情形（JSON 字符串转义、正则模式串）才会命中。4 个 needle 里有 2 个（两个盘符）实际不工作。

这一条对本卷宗的消毒工作有直接影响：本仓侧复扫交付物时**不能只用闸门这四个 needle**，否则会继承它的漏检。条目 23 的手工扫描因此额外加了 `<linux-home-prefix>/` 与 `<mac-tmp-prefix>` 两个闸门根本不管的模式。

附带一条：`g0_environment.py` 第 45 行对 `acceptance/` 目录下的文件豁免绝对路径检查（`if needle in text and "acceptance" not in rel`），这意味着闸门脚本自身可以含绝对路径而不报警——设计意图是让闸门能把路径前缀写进检测模式串，但豁免范围过宽（整个 `acceptance/` 目录而不只闸门脚本自身）。也正是这条豁免，使盲区 ③ 的双重转义 needle 能够长期存在于 `acceptance/gates/` 里而不被自己检出。

**影响**：交付物的绝对路径与密钥检查没有任何闸门覆盖，只能靠人工。

**建议裁决**：扩大 `SCAN_DIRS` 覆盖 `tests/` 与 `evidence/`；`SCAN_SUFFIXES` 加入 `.log`；修正第 44 行两个盘符 needle 的双重转义（源码里的四个反斜杠改为两个，使其值从「双反斜杠」变为「单反斜杠」；或改用原始字符串正则 `r"[A-Za-z]:\\\\?"`，同时兼容单/双反斜杠）；把第 45 行的豁免从「整个 `acceptance/` 目录」收窄到「闸门脚本自身」；或在 README 里明确写清这两个目录的检查责任归属（例如「evidence/ 与 tests/ 的消毒由提交者负责，闸门不覆盖」）。

### 条目 23：本仓侧的自行补救

针对上述三个盲区，本仓侧对 `src/` + `tests/` + `evidence/` 做了全量手工扫描。

**关于下面命令里的模式串**：本卷宗按记号约定不写真实路径字面量，所以命令里的模式以记号书写（`<win-drive>:\`、`<home-prefix>/` 等），**实际执行时需把记号换回真实字面量**（即 `g0_environment.py` 第 44 行那四个 needle 的值，加上本仓侧自补的 `<linux-home-prefix>/` 与 `<mac-tmp-prefix>`）。

**集成后本轮复扫结果**（对 `git ls-files src tests evidence` 列出的全部 tracked 文件，排除本卷宗自身）：

```
needle [<win-drive>:\]        -> 0 命中
needle [<win-drive2>:\]       -> 0 命中
needle [<home-prefix>/]       -> 0 命中
needle [<win-drive>/Users]    -> 0 命中
needle [<linux-home-prefix>/] -> 0 命中   ← 闸门不管，本仓侧自补
needle [<mac-tmp-prefix>]     -> 0 命中   ← 闸门不管，本仓侧自补

密钥正则 sk-[A-Za-z0-9]{16,}                     -> 0 命中
密钥正则 AIza[0-9A-Za-z\-_]{20,}                 -> 0 命中
密钥正则 [0-9a-f]{32}\.[A-Za-z0-9]{16}           -> 0 命中
密钥正则 (api_?key|token|secret)\s*[:=]\s*['"]… -> 0 命中
密钥正则 Bearer\s+[A-Za-z0-9\-_\.]{20,}          -> 0 命中
```

**交付物 0 命中，且这 0 命中与上一版不同——它现在是真 0，不是「命中了一行注释」。**

上一版这一节记的是「唯一命中是 `tests/holdout_v2.py` 第 82 行的注释（它在声明本文件不含绝对路径时把两类前缀当模式串示例引了出来）」。本轮核对源文件，**那一行已经被并行工作的 N2 消毒改掉了**，字面量不再存在。`git show HEAD:tests/holdout_v2.py` 第 81–87 行当前原文：

```
# 5. 隐私与安全：不含真实可识别个人信息、密钥样式串（sk- / api_key= / Bearer）、
#    以及用户主目录前缀或 Windows 盘符前缀这类绝对路径。人名、地名、账号均为
#    虚构常识性素材。
#    （N2：本条原先把这两类前缀的原样字面量写在这里当示例。本仓要 push 到公开
#    仓库，而仓库规则禁止 src/ 与 tests/ 下出现它们，注释与字符串也不例外，故
#    改为只描述约束。语料数据一个字节未动：规范化序列化的 sha256 前后相同，
#    该值由 tests/test_holdout_v2.py 的 HOLDOUT_V2_SHA256 钉住并逐次校验。）
```

它把字面量换成了「用户主目录前缀或 Windows 盘符前缀」这样的描述性表述，并在注释里记录了这次改动的理由与「语料数据 digest 未变」的自证。本仓侧核对了该文件工作树与 HEAD 一致（sha256 两边相同），即这是已 commit 的正式修改，不是未落盘的临时态。

**全仓范围（不只交付物）的命中情况**：扫完 `src/ tests/ evidence/ acceptance/ vendor/ tasks/ docs/` 全部文件后，四类绝对路径前缀的**唯一命中是闸门自己的 needle 定义行**：

```
$ grep -rn '<win-drive>:\' src tests evidence acceptance vendor tasks docs
acceptance/gates/g0_environment.py:44:        for needle in (…):   ← 闸门自身的检测模式串定义
（另有一个 __pycache__ 里的 .pyc 二进制命中，是同一行的编译产物）
```

这一行是闸门源码的一部分，属于禁改范围（本仓侧不得修改任何闸门脚本），且第 45 行的 `acceptance/` 豁免使它不会被自己检出。本卷宗不处置它，只如实报告其存在与位置。

结论：交付物里无真实绝对路径、无密钥样式串。但这份保证来自人工扫描而非闸门，每次新增文件都需要重做；且因为盲区 ③，人工扫描时**不能直接拿闸门的 needle 当清单用**，否则会连它的漏检一起继承。

---

## 八、协议与流程文档缺口

### 条目 24：`PROTOCOL.md` 不存在

**现象**：用户的开发流程要求「README → INTEGRATION → PROTOCOL → tasks/<包>/SPEC.md」四步通读，但仓库里没有 `PROTOCOL.md`。

**证据**：

```
$ git ls-files | grep -i protocol
（无输出）

$ find . -name "PROTOCOL*" -not -path "./.venv/*" -not -path "./.git/*"
（无输出）
```

协议事件名与 JSON 契约字段的实际唯一来源是 `vendor/agent_core/harness.py` 里的 `EMOTION_EVENTS`、`GESTURE_EVENTS`、`AgentReply` 与 `BASE_SYSTEM_PROMPT` 的【输出契约】段。该文件被 MANIFEST 哈希锁定——而它正是第一章里漂移的那一件（现已由上游修复）。

**影响**：新 agent 按流程通读时会发现第三步缺失，只能自行从 harness.py 源码里提取协议规格。harness.py 是 10055 字节的 Python 文件而非协议文档，阅读成本高于一份专门的 PROTOCOL.md。

**建议裁决**：补 `PROTOCOL.md`（从 harness.py 提取事件名、JSON 字段、约束），或在工作流程里把协议事实来源明确指向 `vendor/agent_core/harness.py`（例如 README 里加一句"协议规格见 harness.py 的 EMOTION_EVENTS / GESTURE_EVENTS / AgentReply"）。

### 条目 25：DoD 与单任务包交付节点的语义缝隙

**现象**：README DoD 要求 `run_all.py --strict` 全绿（8 闸门全 PASS），但任务 C/E 未认领时 `g1_permissions`/`g1_tools` 恒为 PENDING，`--strict` 必然 BLOCKED/exit 1。单个任务包在自己的交付节点上永远拿不到 `--strict` 全绿证据。

**证据**：

verdict 逻辑推演（第 49 行）：

```
场景                              | 普通 verdict   | 普通 exit | strict verdict | strict exit
After upstream fix (PENDING only) | PENDING-OK     | 0         | BLOCKED        | 1
All tasks complete                | PENDING-OK     | 0         | PASS           | 0
```

上游修复 `g0_freeze` 后，唯一阻止 `--strict` 全绿的东西就只剩 `g1_permissions`/`g1_tools` 的 PENDING。这比修复前更能说明问题：修复前还有 `g0_freeze` 的 FAIL 混在里面，可以归咎于上游缺陷；修复后零 FAIL、实现完美，`--strict` 仍然 exit 1——纯粹因为其它任务包未认领。

SPEC 给每个包都写了「run_all --strict ×3」的证据要求（`tasks/B-memory-system/SPEC.md` 第 14 行），但只有四个包全做完才可能满足。这与"单任务包独立交付"的设计直接矛盾。

**影响**：任何单任务包在自己的交付节点上都无法字面满足 DoD 第一条。本仓侧经用户拍板采用「双份证据 + 逐闸门明细」口径应对（见条目 26），但这是变通而非合规。

**建议裁决**：明确单任务包节点的 strict 口径。可选方案：
- 引入按任务包 scope 的闸门子集（例如任务 B 只要求 g0_* + g1_memory + g3_simulate 全绿）
- 在 verdict 里区分「本包闸门全绿 + 其它包 PENDING」与「真有 FAIL」
- 或修改 SPEC 的证据要求为「run_all 普通模式 ×3 + 目标闸门独立复跑 ×3」

### 条目 26：本仓侧的应对

经用户拍板采用「双份证据 + 逐闸门明细」口径：

- 每轮同时保留普通模式与 `--strict` 的完整输出（`evidence/task_b_round{1,2,3}_{normal,strict}.log`）
- 外加一张闸门 × 轮次 × 模式的状态明细表（`evidence/task_b_gate_matrix.md`）
- 对每个非 PASS 闸门逐条归因（g0_freeze → 上游漂移；g1_permissions/g1_tools → 任务 C/E 未认领）

这不构成绕过闸门：闸门本身未被修改，verdict 仍如实报 FAIL/BLOCKED，本仓侧只是额外提供了逐闸门明细来证明"FAIL 的成因不在本任务包"。

---

## 九、`score_retrieval` 的 PENDING 协议残留

### 条目 27：签名 `| None` 成为永久死代码

**现象**：`src/memory_store.py` 第 246 行签名：

```python
def score_retrieval(golden: list[dict]) -> dict[str, float] | None:
```

`g1_memory.py` 第 52 行用「返回 None = PENDING」表达未实现态：

```python
result = score_retrieval(GOLDEN)
if result is None:
    pending.append("retrieval quality: score_retrieval() not implemented (Task B)")
```

Task B 实现后，`score_retrieval` 永远返回 `dict`，`| None` 分支成为永久死代码。docstring 自己也承认："The `| None` in the signature is the gate's PENDING protocol (None = unimplemented) and is never returned now that Task B is implemented."

**影响**：签名不能改——改了会与闸门调用方的类型预期不一致，且该文件是 SPEC 指定的工作文件、签名属对外契约。但留着它会让阅读者误以为函数仍可能返回 None。

**建议裁决**：主仓侧集成时是否清理这个协议残留（把签名改为 `-> dict[str, float]`，同时更新 `g1_memory.py` 的 None 分支为断言或删除）。若保留，建议在 docstring 里加一句"历史协议残留，集成后可安全移除"。

---

## 十、集成后的状态核查结论（三条，均为实测）

本章不是异议条目，而是集成后对本仓侧交付面是否受影响的三项核查。三条结论都是「无影响 / 一致 / 安全」，但每一条都附实测数字与推演方法，供主仓侧自行复核。

### 状态结论 1：`.gitattributes` 的覆盖范围与我方交付物零影响

**文件本体逐字节**：

```
$ git cat-file blob HEAD:.gitattributes | wc -c
19
$ ./.venv/bin/python -c "…print(repr(blob))…"
b'* text=auto eol=lf\n'
```

19 字节、单行 + 尾换行、无 BOM、无第二条规则、无注释。

**覆盖范围**：单条 glob `*` 匹配仓内**所有路径无例外**（gitattributes 的 `*` 递归匹配，不需 `**`）。实测：

```
$ git ls-files | wc -l
54
$ git ls-files --eol | grep -vc 'attr/text=auto eol=lf'
0                      ← 54/54 全部命中同一条属性，无一例外
$ git ls-files --eol | awk '{print $1, $2}' | sort | uniq -c
  52 i/lf w/lf
   2 i/none w/none
```

那两个 `i/none w/none` 是空文件（`src/prompt_persona/__init__.py` 与 `vendor/agent_core/__init__.py`）——零字节文件无行尾可论，`none` 是 git 对空文件的正常记法，不是异常。

**我方交付物逐个核实**（按路径查属性，不钉行数——并行工作正在改这些文件，行数是浮动的）：

```
$ git ls-files --eol -- src tests evidence
i/lf  w/lf  attr/text=auto eol=lf  evidence/README.md
i/lf  w/lf  attr/text=auto eol=lf  evidence/task_b_integration.md
i/lf  w/lf  attr/text=auto eol=lf  evidence/task_b_retrieval_analysis.md
i/lf  w/lf  attr/text=auto eol=lf  src/__init__.py
i/lf  w/lf  attr/text=auto eol=lf  src/memory_lexicon.py
i/lf  w/lf  attr/text=auto eol=lf  src/memory_ranker.py
i/lf  w/lf  attr/text=auto eol=lf  src/memory_store.py
i/lf  w/lf  attr/text=auto eol=lf  src/permissions.py
i/none w/none attr/text=auto eol=lf src/prompt_persona/__init__.py   ← 空文件
i/lf  w/lf  attr/text=auto eol=lf  src/prompt_persona/system_prompt.py
i/lf  w/lf  attr/text=auto eol=lf  src/tools_registry.py
i/lf  w/lf  attr/text=auto eol=lf  tests/holdout_v2.py
…（tests/ 下共 15 个文件，全部 i/lf w/lf）
```

**结论：我方交付物在这个策略下零影响。** 每一个我方文件的 index eol 与 worktree eol 都已是 `i/lf w/lf`，与 `attr/text=auto eol=lf` 要求完全一致——既不需重检出，也不会因属性变更而产生任何字节差异。本卷宗自身是 untracked 文件，不在 `git ls-files` 范围内，但它也是纯 LF。

### 状态结论 2：`scenarios.json` 七方一致

集成前这个文件是矛盾焦点（工作树 CRLF / MANIFEST 旧值按 CRLF 算 / index blob 是 LF）。集成后实测：

```
$ P=acceptance/evals/scenarios.json
1 worktree sha256      : 2c5dab3fc5e414680193c7b998bb62cf9fe3c6299f2f002682a75efa8179b00e
2 hash-object(filters) : 53ab5c2bf54027f3e333e0f980259acbe0e72150
3 hash-object --no-f   : 53ab5c2bf54027f3e333e0f980259acbe0e72150
4 index sha            : 53ab5c2bf54027f3e333e0f980259acbe0e72150
5 HEAD blob sha        : 53ab5c2bf54027f3e333e0f980259acbe0e72150
6 origin/main blob sha : 53ab5c2bf54027f3e333e0f980259acbe0e72150
7 MANIFEST 期望         : 2c5dab3fc5e414680193c7b998bb62cf9fe3c6299f2f002682a75efa8179b00e
8 ls-files --eol       : i/lf  w/lf  attr/text=auto eol=lf
9 bytes / CR           : 2752 / 0
```

三个要点：

- **2 与 3 相等**（with filters == --no-filters）。这是工作树已是纯 LF 的直接证据——clean 过滤器无事可做。对比条目 B/F 里的矛盾态，那里两者不等（`53ab5c2b…` vs `76b7280d…`）。
- **2/3/4/5/6 五者全等**，即工作树、index、本仓 HEAD、远端 main 四层完全一致，本地与上游对这一份字节无任何分歧。
- **1 == 7**，即磁盘字节的 sha256 正是 MANIFEST 期望值，`g0_freeze` 对它判 MATCH。

另：`.git/info/attributes` 文件**已不存在**（不是内容为空，是文件本身没了），集成前那条临时 `eol=crlf` 规则已彻底撤销，无遗留。

### 状态结论 3：`git add --renormalize .` 的 54/54 no-op 推演与三条不执行理由

**结论：字节层面安全（已证明 54/54 no-op），协同层面不安全，且零收益，本仓不执行。**

**推演方法（比 `--dry-run` 更强）**：`git add --renormalize` 的语义是「对工作树字节跑 clean 过滤器，把结果写回 index」。而 `git hash-object <path>`（**不带 `-w`，不落盘、不写 index、不碰对象库**）算出的正是同一个值。因此：

> `git hash-object <path>` == `git ls-files -s <path>` 的 index sha ⇒ 该文件 renormalize 后零变化

这不是预估也不是采样，而是逐文件算出了 renormalize **将会写入 index 的那个确切值**，再与 index 现值比对。它比 `--dry-run` 强在两点：一是 `--dry-run` 仍会获取索引锁并可能被其他并行写入干扰，二是 `--dry-run` 只报「会不会动」而不报「动成什么」。

**实测结果**（对全部 54 个 tracked 文件逐个比对）：

```
tracked=54  renormalize no-op=54/54  index!=HEAD=0
```

| 校验项 | 实测 | 含义 |
|---|---|---|
| `hash-object` == index sha | **54/54** | renormalize 不会改变任何一个文件的 index 条目 |
| index sha == HEAD blob sha | **54/54**（不等 = 0 处） | index 与 HEAD 无差异，不可能产生暂存 diff |
| `git status --porcelain --untracked-files=no` | **空** | 连一条工作树改动都没有 |
| 5 个冻结件专项 | **5/5 MANIFEST MATCH 且 5/5 renorm=no-op** | 即使误跑，冻结件也不会被改一个字节 |

**三条不执行理由**：

1. **零收益**。既然 54/54 已是 no-op，跑与不跑的最终字节完全相同。`.gitattributes` 新增后并不需要一次全仓 renormalize 来「对齐」，因为仓内本来就没有任何文件的 index 形态与 `eol=lf` 相左。跑它只会白白消耗一次索引写入。
2. **协同层面不安全**。renormalize 会重写整个 index（即使内容不变，index 文件的 mtime 与 stat 缓存全量刷新）。当前有并行工作正在改 `src/`、`tests/` 与 `evidence/`，重写 index 会与并行进程的 `git add` / `git status` 争索引锁，最坏情况是把对方未完成的暂存意图弄丢。本仓侧不能为了一个零收益的动作去冒干扰并行工作的风险。
3. **命令本身在禁运行清单里**。本轮铁律明确禁 `git add --renormalize`（**含 `--dry-run`**）。本仓侧全程未执行它一次——上述 54/54 的结论是用 `git hash-object`（无 `-w`）与 `git ls-files -s` 这两个**纯读取**命令推演出来的，对仓库零写入。这也是选择这个推演方法而不是直接跑 `--dry-run` 的原因。

**给主仓侧的一句话**：若主仓侧将来在全仓范围变更行尾策略，建议先用本章的推演方法确认 no-op 比例，再决定是否需要 renormalize；在多人并行开发的仓库里，重写 index 这个动作应视为有副作用的写操作而非维护性清理。

---

## 附录 A：本仓侧为绕过这些缺陷所做的合规替代措施

以下措施均为"在闸门之外补充证据"，不构成修改闸门、绕过闸门或让闸门变绿。

| 缺陷 | 替代措施 | 为什么不构成绕过 |
|------|----------|------------------|
| g0_freeze 恒 FAIL 导致 verdict 恒 FAIL | 分层证据方案：普通模式 + strict 模式各跑 3 轮，逐闸门明细表对每个非 PASS 项归因 | 闸门未被修改，verdict 仍如实报 FAIL；本仓侧只是额外证明"FAIL 成因不在本任务包" |
| 单测不在 GATES 里 | 每轮额外跑 `unittest discover` 并保留日志（`task_b_round{1,2,3}_unittest.log`） | 闸门未被修改；本仓侧自行提高了证据标准 |
| drill 不自证恢复 | drill 后手工逐闸门复跑 + 哈希对照（`task_b_sabotage_drill.md` 第 6 节） | drill 未被修改；本仓侧补了它缺失的复验步骤 |
| drill 丢弃闸门输出 | 取证文档里逐条分析三路的作用链与预期报错 | drill 未被修改；本仓侧从外部补齐了审计信息 |
| eval-tamper 路假阳性 | 仓库外副本隔离实验证明 g0_freeze 对 scenarios.json 确有牙齿 | 真仓库未被修改；实验只在 `<tmp>` 副本上做 |
| 扫描盲区（tests/ evidence/） | 全量手工 grep 绝对路径与密钥样式串，命中 0 | 闸门未被修改；本仓侧自行扩大了检查范围 |
| evidence 同秒覆盖 | R1 普通模式的完整输出由独立 .log 保全，不依赖 JSON | run_all.py 未被修改；本仓侧用 tee 补了留存 |
| `.git/info/attributes` 临时 CRLF 规则 | **已彻底撤销**：集成后该文件已不存在（不是内容为空，是文件本身没了），`.gitattributes` 的 `eol=lf` 全面生效，`g0_freeze` 实测 5/5 PASS | 闸门未被修改；MANIFEST 未被修改；那是本地 git 配置，不是仓库文件，也不曾进入任何 commit |
| 需要判断 `git add --renormalize .` 是否安全，但该命令（含 `--dry-run`）在禁运行清单里 | 用两个**纯读取**命令推演：`git hash-object <path>`（不带 `-w`，不落盘、不写 index）算出 renormalize 将写入的确切值，与 `git ls-files -s <path>` 的 index sha 逐个比对，得 54/54 no-op | 对仓库零写入；推演结果比 `--dry-run` 更强（不只报「会不会动」，而是算出「动成什么」再比对），详见第十章状态结论 3 |
| 集成后需重跑 drill 确认有效检出是否变为真 3/3，但 drill 会临时改写冻结件 | **本轮不跑**，把重跑与完整取证留给 QA 的最终取证轮；本轮只交付静态证据（三路目标闸门的前置退出码 0/0/0、AST 不可达判定、全仓无 `RESTORE FAILED` 输出） | drill 未被修改也未被执行，冻结件零风险；不与并行工作争写入窗口；旧结论已明确标注过期而不是偿偿沿用 |

---

## 附录 B：全部复现命令清单

以下命令均在仓库根目录执行，解释器为 `./.venv/bin/python`。按卷宗章节顺序排列，主仓侧可一次性复核。

三点阅读说明：

1. 命令里的 `<tmp>`、`<win-drive>:\`、`<home-prefix>/` 是本卷宗的记号，**执行时需换回真实字面量**（`<tmp>` = 仓库外临时目录；后两个 = `g0_environment.py` 第 44 行 needle 的真实值）。
2. `$BOOTSTRAP` 需先赋值：`BOOTSTRAP=$(git rev-list --max-parents=0 HEAD)`（即 subject 为 `feat: workbench bootstrap` 的那个 commit）。本卷宗不写裸 commit hash，因为它在 rebase 后会变死链。
3. 标注「在 `<tmp>` 副本上做」的段落**不得在真仓库执行**（它们会改写冻结件或 MANIFEST）。副本用 `git clone --local <repo> <tmp>/<name>` 或 `cp -r . <tmp>/<name>` 建立。

```bash
# === 基线 ===
git log --oneline -1
git rev-list --count HEAD                      # 仓库 commit 总数（本轮实测 41）
git rev-list --count origin/main..HEAD         # 领先远端多少个（本轮实测 39）
git status --porcelain --untracked-files=no    # 应为空
sha256sum vendor/agent_core/harness.py acceptance/evals/scenarios.json \
  acceptance/gates/g0_environment.py acceptance/gates/g0_freeze.py acceptance/gates/g0_secrets.py

# === 一、冻结清单与 g0_freeze（含条目 A / E）===
./.venv/bin/python -c "import json; m=json.load(open('acceptance/MANIFEST.json')); print(m['vendor/agent_core/harness.py'])"
shasum -a 256 vendor/agent_core/harness.py
git status --porcelain -- vendor/agent_core/harness.py
git diff HEAD -- vendor/agent_core/harness.py
BOOTSTRAP=$(git rev-list --max-parents=0 HEAD)  # bootstrap commit: "feat: workbench bootstrap"
git show $BOOTSTRAP:vendor/agent_core/harness.py | shasum -a 256
git show HEAD:vendor/agent_core/harness.py | shasum -a 256
cat .git/info/attributes 2>/dev/null || echo "[文件不存在——集成后临时 CRLF 规则已彻底撤销]"

# CRLF/BOM 排除（7 种变换）
./.venv/bin/python -c "
import hashlib; from pathlib import Path
data = Path('vendor/agent_core/harness.py').read_bytes()
expected = '219691162b9f09b8e544acaff6a39ac613ba2027d5b2ba9b2713875934ea8da5'
variants = {
    'original': data,
    'LF->CRLF': data.replace(b'\\r\\n',b'\\n').replace(b'\\n',b'\\r\\n'),
    'CRLF->LF': data.replace(b'\\r\\n',b'\\n'),
    'with BOM': b'\\xef\\xbb\\xbf'+data,
    'LF->CRLF+BOM': b'\\xef\\xbb\\xbf'+data.replace(b'\\r\\n',b'\\n').replace(b'\\n',b'\\r\\n'),
    'strip trailing newline': data.rstrip(b'\\n').rstrip(b'\\r'),
    'BOM+strip trailing': b'\\xef\\xbb\\xbf'+data.rstrip(b'\\n').rstrip(b'\\r'),
}
for name,v in variants.items():
    h=hashlib.sha256(v).hexdigest()
    print(f'{name:30s} bytes={len(v):6d} match={h==expected}')
"

# scenarios.json CRLF 对照
./.venv/bin/python -c "
from pathlib import Path
d=Path('acceptance/evals/scenarios.json').read_bytes()
print(f'bytes={len(d)}, CRLF={d.count(bytes([13,10]))}, bare_LF={d.count(bytes([10]))-d.count(bytes([13,10]))}')
"

# 上游修复核实
git log --format='%s' $BOOTSTRAP..origin/main
git diff --name-status $BOOTSTRAP..origin/main
git show origin/main:acceptance/MANIFEST.json
git show origin/main:.gitattributes
git diff $BOOTSTRAP..origin/main -- acceptance/run_all.py acceptance/sabotage_drill.py acceptance/gates/ evidence/README.md

# --- 条目 A：14 种行尾/编码变换反查旧期望值（集成前只做 7 种；第 15 种 latin-1 会抛异常，见末尾）---
python3 - <<'PY'
import hashlib
from pathlib import Path
CR=b'\r'; CRLF=b'\r\n'; NL=b'\n'; BOM3=b'\xef\xbb\xbf'; BOM2=b'\xff\xfe'
d = Path('vendor/agent_core/harness.py').read_bytes()
OLD = '219691162b9f09b8e544acaff6a39ac613ba2027d5b2ba9b2713875934ea8da5'
print('harness.py 形态: %d B  CR=%d  CRLF=%d  BOM=%s  endsNL=%s'
      % (len(d), d.count(CR), d.count(CRLF), d.startswith(BOM3), d.endswith(NL)))
V = [('1  LF 原样', d), ('2  LF->CRLF', d.replace(NL,CRLF)), ('3  LF->裸CR', d.replace(NL,CR)),
     ('4  CRLF->LF', d.replace(CRLF,NL)), ('5  +UTF8 BOM', BOM3+d), ('6  +UTF16LE BOM', BOM2+d),
     ('7  LF->CRLF+UTF8 BOM', BOM3+d.replace(NL,CRLF)), ('8  去尾换行', d.rstrip(NL)),
     ('9  去尾换行+CRLF', d.rstrip(NL).replace(NL,CRLF)), ('10 尾加空行', d+NL),
     ('11 尾加空行+CRLF', (d+NL).replace(NL,CRLF)), ('12 裸CR也转LF', d.replace(CR,NL)),
     ('13 utf-16-le', d.decode('utf-8').encode('utf-16-le')),
     ('14 utf-16(带BOM)', d.decode('utf-8').encode('utf-16'))]
hit = 0
for k, v in V:
    h = hashlib.sha256(v).hexdigest(); hit += h == OLD
    print('  %-22s %6d B  %s..  match_OLD=%s' % (k, len(v), h[:12], h == OLD))
print('命中数: %d/%d' % (hit, len(V)))
try:
    d.decode('utf-8').encode('latin-1')
except UnicodeEncodeError as e:
    print('15 latin-1 -> 不可构造: %s（本文件含中文，字符超出 0x00-0xFF）' % type(e).__name__)
PY

# --- 条目 A：全对象库 blob 反查（总数随时点而变，本轮实测 108 个；关键是反查结论）---
./.venv/bin/python -c "
import subprocess,hashlib
def sh(*a,b=False):
    r=subprocess.run(list(a),capture_output=True); return r.stdout if b else r.stdout.decode().strip()
blobs=[(p[0],int(p[2])) for p in (l.split() for l in sh('git','cat-file','--batch-all-objects','--batch-check').splitlines()) if len(p)>=3 and p[1]=='blob']
print('blob 总数:',len(blobs))
for name,t in [('旧 harness','219691162b9f09b8e544acaff6a39ac613ba2027d5b2ba9b2713875934ea8da5'),
               ('新 harness','cb1ae928f80674952c4ac6e6385d260a7dbd5cf93ac5ab96889ff6bdb32b2807'),
               ('旧 scenarios','01ed805ae688e431a8f09bf64d21d445cdf26e85843c6fd9d08b58332df42e67'),
               ('新 scenarios','2c5dab3fc5e414680193c7b998bb62cf9fe3c6299f2f002682a75efa8179b00e')]:
    f=[(o,s) for o,s in blobs if hashlib.sha256(sh('git','cat-file','blob',o,b=True)).hexdigest()==t]
    print(f'{name}: ', f if f else 'NOT FOUND')
"

# --- 条目 A：scenarios.json 旧期望值 == LF blob 的 CRLF 渲染？---
./.venv/bin/python -c "
import hashlib; from pathlib import Path
d=Path('acceptance/evals/scenarios.json').read_bytes()
lf=d.replace(b'\\r\\n',b'\\n'); crlf=lf.replace(b'\\n',b'\\r\\n')
for n,v in [('worktree',d),('LF 渲染',lf),('CRLF 渲染',crlf)]:
    print(f'{n:10s} bytes={len(v)} CRLF={v.count(bytes([13,10]))} sha256={hashlib.sha256(v).hexdigest()}')
"

# --- 条目 A：bootstrap MANIFEST 5 条逐个判定（LF/CRLF 双渲染）---
./.venv/bin/python -c "
import subprocess,json,hashlib
B=subprocess.run(['git','rev-list','--max-parents=0','HEAD'],capture_output=True,text=True).stdout.strip()
bm=json.loads(subprocess.run(['git','show',f'{B}:acceptance/MANIFEST.json'],capture_output=True,text=True).stdout)
nm=json.loads(subprocess.run(['git','show','HEAD:acceptance/MANIFEST.json'],capture_output=True,text=True).stdout)
for rel,exp in bm.items():
    blob=subprocess.run(['git','show',f'{B}:{rel}'],capture_output=True).stdout
    lf=blob.replace(b'\\r\\n',b'\\n'); crlf=lf.replace(b'\\n',b'\\r\\n')
    v='LF-MATCH' if hashlib.sha256(lf).hexdigest()==exp else ('CRLF-MATCH' if hashlib.sha256(crlf).hexdigest()==exp else 'NO-MATCH')
    print(f'{rel}: blob={len(blob)}B CR={blob.count(bytes([13]))} 判定={v} 上游改了={exp!=nm.get(rel)}')
"

# --- 条目 A：本仓从未改过 harness.py（--all 覆盖全部 ref）---
git log --oneline --all -- vendor/agent_core/harness.py

# --- 条目 E：MANIFEST.json 自身无尾换行 ---
./.venv/bin/python -c "
import subprocess; from pathlib import Path
for n,b in [('worktree',Path('acceptance/MANIFEST.json').read_bytes()),
            ('HEAD blob',subprocess.run(['git','cat-file','blob','HEAD:acceptance/MANIFEST.json'],capture_output=True).stdout)]:
    print(f'{n}: bytes={len(b)} last_byte=0x{b[-1]:02x} endsNL={b.endswith(bytes([10]))}')
"
git diff $BOOTSTRAP..HEAD -- acceptance/MANIFEST.json | tail -3   # 末行应为 \ No newline at end of file

# === 二、闸门实现机制（条目 B / C）===
git show HEAD:acceptance/gates/g0_freeze.py | grep -n "read_bytes\|read_text"   # 25 / 31
git show HEAD:acceptance/gates/g0_freeze.py | sed -n '14,25p'                    # MANIFEST 常量 + FREEZE_TARGETS + sha256()
git show HEAD:acceptance/gates/g0_freeze.py | sed -n '32,43p'                    # 比对循环
git show HEAD:acceptance/gates/g0_freeze.py | sed -n '46,52p'                    # --update 分支

# 条目 C：MANIFEST 自身是否在冻结清单里
git show HEAD:acceptance/gates/g0_freeze.py | sed -n '15,21p' | grep -c "MANIFEST.json"   # 0
# 条目 C：--update 有无守卫
git show HEAD:acceptance/gates/g0_freeze.py | grep -n "confirm\|input(\|--dry\|backup\|diff\|audit\|permission\|getpass"
# 条目 B：闸门与 git 对同一份字节的两种哈希
# （矛盾态的实测输出见第二章条目 B 证据 2；两种哈希为何不同的机制见第三章条目 F 步骤 5）
git hash-object acceptance/evals/scenarios.json
git hash-object --no-filters acceptance/evals/scenarios.json
git ls-files -s acceptance/evals/scenarios.json
git rev-parse HEAD:acceptance/evals/scenarios.json

# === 三、eol 与 git 语义裂缝（条目 F，全部在 <tmp> 副本上做）===
git clone --local . <tmp>/eol_noop_exp && cd <tmp>/eol_noop_exp
P=acceptance/evals/scenarios.json
# 步骤1：用本地 attributes 构造集成前的 CRLF 工作树（必须由 git 自己写入，stat 缓存才有效）
printf '%s text eol=crlf\n' "$P" > .git/info/attributes
rm -f "$P"; git checkout HEAD -- "$P"
wc -c < "$P"; tr -dc '\r' < "$P" | wc -c; shasum -a 256 "$P"
git status --porcelain --untracked-files=no      # 应为空（clean）
git ls-files --eol -- "$P"                      # i/lf  w/crlf  attr/text eol=crlf
# 步骤2：撤销本地规则，模拟集成后 .gitattributes 的 eol=lf 生效
rm -f .git/info/attributes
git status --porcelain --untracked-files=no      # 仍为空
git ls-files --eol -- "$P"                      # i/lf  w/crlf  attr/text=auto eol=lf  ← 矛盾态
# 步骤3：关键实验——git checkout -- 是否 no-op
shasum -a 256 "$P"                              # before
git checkout -- "$P"; echo "EXIT=$?"
shasum -a 256 "$P"                              # after，应与 before 逐字相同
wc -c < "$P"; tr -dc '\r' < "$P" | wc -c        # 仍为 CRLF 版字节数
# 步骤4：对照——只有 rm + git checkout HEAD -- 才真重检出
rm -f "$P"; git checkout HEAD -- "$P"
wc -c < "$P"; tr -dc '\r' < "$P" | wc -c; shasum -a 256 "$P"
# 步骤5：机制解释——with filters == index == HEAD，而 --no-filters 不等
printf '%s text eol=crlf\n' "$P" > .git/info/attributes; rm -f "$P"; git checkout HEAD -- "$P"; rm -f .git/info/attributes
git hash-object "$P"; git hash-object --no-filters "$P"
git ls-files -s "$P" | awk '{print $2}'; git rev-parse HEAD:"$P"
git status --porcelain --untracked-files=no
# 步骤6（失效条件对照）：外部程序写入会破坏 stat 缓存，结论相反
./.venv/bin/python -c "
from pathlib import Path
p=Path('acceptance/evals/scenarios.json'); d=p.read_bytes()
p.write_bytes(d.replace(b'\\n',b'\\r\\n'))
print('已由外部程序写为 CRLF:', len(p.read_bytes()),'bytes')
"
git status --porcelain --untracked-files=no      # 此时报  M（不再是 clean）
git checkout -- "$P"; wc -c < "$P"             # 此时 checkout 真重检出为 LF
cd -   # 回真仓库

# === 四、run_all.py ===
./.venv/bin/python acceptance/run_all.py 2>&1; echo "EXIT=$?"
./.venv/bin/python acceptance/run_all.py --strict 2>&1; echo "EXIT=$?"
sed -n '17,26p' acceptance/run_all.py
sed -n '42,44p' acceptance/run_all.py
sed -n '49p' acceptance/run_all.py
sed -n '59p' acceptance/run_all.py
sed -n '63p' acceptance/run_all.py

# === 五、Goodhart 敞口（在 <tmp> 副本上做）===
rm -rf <tmp>/gate_objection_exp && cp -r . <tmp>/gate_objection_exp && cd <tmp>/gate_objection_exp
./.venv/bin/python acceptance/gates/g1_memory.py; echo "EXIT=$?"
./.venv/bin/python -c "
import re; from pathlib import Path
p=Path('src/memory_lexicon.py'); text=p.read_text()
result=re.sub(r'member=\\([^)]*\\)','member=()',text,flags=re.DOTALL)
p.write_text(result)
"
./.venv/bin/python acceptance/gates/g1_memory.py; echo "EXIT=$?"
./.venv/bin/python -m unittest tests.test_memory_retrieval 2>&1 | tail -5
./.venv/bin/python -m unittest discover -s tests 2>&1 | grep -E '^(Ran|FAILED|OK)'
./.venv/bin/python acceptance/run_all.py 2>&1 | grep -E '^(PASS|FAIL|PENDING)'
cd -  # 回到真仓库

# === 六、sabotage_drill（含条目 D）===
./.venv/bin/python acceptance/sabotage_drill.py; echo "EXIT=$?"
sed -n '19,21p' acceptance/sabotage_drill.py
sed -n '24,43p' acceptance/sabotage_drill.py

# 条目 D：用 AST 静态证明第 38–43 行不可达。
# 这是纯静态分析，**不运行 drill**，因此不会临时改写任何冻结件——
# 这正是本轮选静态证明而不实跑 drill 的原因（并行工作正在改 src/ 与 tests/）。
python3 - <<'PY'
import ast
from pathlib import Path
src = Path('acceptance/sabotage_drill.py').read_text()
fn = next(n for n in ast.parse(src).body if isinstance(n, ast.FunctionDef) and n.name == 'drill')
tr = next(n for n in ast.walk(fn) if isinstance(n, ast.Try))
print('drill() 行范围: %d-%d' % (fn.lineno, fn.end_lineno))
print('try 块: %d-%d' % (tr.lineno, max(x.end_lineno for x in tr.body)))
print('finally: %d-%d' % (tr.finalbody[0].lineno, tr.finalbody[-1].end_lineno))
print('try 之后的兄弟语句:', [(s.lineno, s.end_lineno, type(s).__name__) for s in fn.body if s.lineno > tr.end_lineno])
def rets(body):
    return [n.lineno for n in ast.walk(ast.Module(body=body, type_ignores=[])) if isinstance(n, ast.Return)]
print('try 块内 return 行号:', rets(tr.body))
print('finally 块内 return 行号:', rets(tr.finalbody))
def all_ret(b):
    if not b: return False
    l = b[-1]
    if isinstance(l, ast.Return): return True
    if isinstance(l, ast.If): return all_ret(l.body) and all_ret(l.orelse)
    return False
print('try body 全分支以 return 收尾:', all_ret(tr.body))
print('=> 不可达:', all_ret(tr.body) and not rets(tr.finalbody))
PY

# 条目 D 的运行时旁证：全仓搜「RESTORE FAILED」，看这行输出是否曾被真正打印过
# （预期：命中全部是源码本体与取证文档里的引用，无一处是 drill 的实际输出）
grep -rn "RESTORE FAILED" . --exclude-dir=.git --exclude-dir=.venv

# 隔离实验（在 <tmp> 副本上做；下面整段包括 git checkout 均只能在副本里执行，
# 绝不在真仓库执行——真仓库的冻结件与 index 必须保持零写入）
rm -rf <tmp>/freeze_teeth_exp && cp -r . <tmp>/freeze_teeth_exp && cd <tmp>/freeze_teeth_exp
./.venv/bin/python -c "
import json,hashlib; from pathlib import Path
m=json.loads(Path('acceptance/MANIFEST.json').read_text())
m['vendor/agent_core/harness.py']=hashlib.sha256(Path('vendor/agent_core/harness.py').read_bytes()).hexdigest()
Path('acceptance/MANIFEST.json').write_text(json.dumps(m,indent=2))
"
./.venv/bin/python acceptance/gates/g0_freeze.py; echo "EXIT=$?"
./.venv/bin/python -c "
from pathlib import Path
p=Path('acceptance/evals/scenarios.json'); d=p.read_bytes()
p.write_bytes(d.replace(b'\\\"identity-01\\\"',b'\\\"identity-01x\\\"',1))
print(f'{len(d)} -> {len(p.read_bytes())} bytes')
"
./.venv/bin/python acceptance/gates/g0_freeze.py; echo "EXIT=$?"
git checkout -- acceptance/evals/scenarios.json
./.venv/bin/python acceptance/gates/g0_freeze.py; echo "EXIT=$?"
cd -  # 回到真仓库

# === 七、证据体系（含条目 22 盲区 ③）===
ls evidence/run_*.json | wc -l
cat .gitignore
cat evidence/README.md
grep "SCAN_DIRS" acceptance/gates/g0_environment.py
grep "SCAN_DIRS\|SCAN_SUFFIXES" acceptance/gates/g0_secrets.py
ls evidence/*.log | wc -l
git ls-files tests | wc -l
find tests/ -name "*.py" -exec wc -l {} + | tail -1
git ls-files evidence | wc -l

# 条目 22 盲区 ③：用 ast 解析第 44 行 needle 元组的真实值，只打印结构不打印字面量
# （打印字面量就会把真实路径前缀写进本卷宗，违反消毒规则）；
# 四个样本串全部用 chr() 拼接构造，所以这段脚本本身也不含任何真实绝对路径
python3 - <<'PY'
import ast
from pathlib import Path
tree = ast.parse(Path('acceptance/gates/g0_environment.py').read_text())
vals = None
for n in ast.walk(tree):
    if isinstance(n, ast.For) and getattr(n.target, 'id', '') == 'needle':
        vals = [e.value for e in n.iter.elts]
print('needle 元组结构（只打印结构，不打印字面量）:')
for i, v in enumerate(vals):
    print('  NEEDLE%d  长度=%d  反斜杠数=%d' % (i, len(v), v.count(chr(92))))
S, C, CL, BS = chr(47), chr(67), chr(58), chr(92)
samples = [
    ('真实 Windows 路径（单反斜杠）', 'open(r"' + C + CL + BS + 'data' + BS + 'x.json")'),
    ('JSON/正则里的双反斜杠',       '"' + C + CL + BS + BS + 'data"'),
    ('macOS 家目录 <home-prefix>/', S + 'Users' + S + 'me' + S + 'x.py'),
    ('盘符 + 冒号 + 正斜杠 + Users', C + CL + S + 'Users' + S + 'me'),
]
print()
print('样本                                命中 needle            结果')
for name, s in samples:
    hit = ['NEEDLE%d' % i for i, v in enumerate(vals) if v in s]
    print('%-33s %-22s %s' % (name, hit, '检出' if hit else '漏检'))
PY

# 手工扫描（模式串按记号书写，执行时换回真实字面量）
grep -rn "<home-prefix>/" tests/ evidence/ --include="*.py" --include="*.md" --include="*.log"
grep -rn "<linux-home-prefix>/" tests/ evidence/     # 闸门不管，本仓侧自补
grep -rn "<mac-tmp-prefix>" tests/ evidence/         # 闸门不管，本仓侧自补
grep -rEn "sk-[A-Za-z0-9]{16,}" tests/ evidence/
grep -rEn "AIza[0-9A-Za-z_-]{20,}" tests/ evidence/

# === 八、协议与流程 ===
git ls-files | grep -i protocol
find . -name "PROTOCOL*" -not -path "./.venv/*" -not -path "./.git/*"
sed -n '14p' tasks/B-memory-system/SPEC.md
sed -n '50p' README.md

# === 九、score_retrieval ===
git show HEAD:src/memory_store.py | sed -n '246,259p'   # 该文件共 259 行，score_retrieval 是末一个函数
sed -n '51,53p' acceptance/gates/g1_memory.py

# === 十、集成后状态核查（三条状态结论，全部纯读取）===
# 状态结论 1：.gitattributes 覆盖范围与我方文件零影响
git cat-file blob HEAD:.gitattributes | wc -c          # 期望 19
git cat-file blob HEAD:.gitattributes
git ls-files | wc -l                                   # tracked 总数（实测 54）
git ls-files --eol | grep -vc 'attr/text=auto eol=lf'  # 期望 0，即 attr 列无例外
git ls-files --eol | grep -o 'i/[a-z]* *w/[a-z]*' | sort | uniq -c
git ls-files --eol src tests evidence                  # 逐个核我方交付物均 i/lf w/lf

# 状态结论 2：scenarios.json 七方一致
P=acceptance/evals/scenarios.json
shasum -a 256 $P                                       # 工作树磁盘字节
python3 -c "import json;print(json.load(open('acceptance/MANIFEST.json'))['acceptance/evals/scenarios.json'])"
git hash-object $P                                     # 跑 clean 过滤器后
git hash-object --no-filters $P                        # 不跑过滤器
git ls-files -s $P                                     # index
git rev-parse HEAD:$P
git rev-parse origin/main:$P
git ls-files --eol $P
wc -c < $P                                             # 期望 2752
python3 -c "from pathlib import Path;print('CR 数 =',Path('acceptance/evals/scenarios.json').read_bytes().count(b'\r'))"
cat .git/info/attributes 2>/dev/null || echo "[文件不存在——集成后临时 CRLF 规则已彻底撤销]"

# 状态结论 3：git add --renormalize . 的 no-op 推演。
# 该命令（含 --dry-run）在禁运行清单里，下面两个命令都是纯读取：
# hash-object 不带 -w，不落盘、不写 index、不碰对象库；ls-files -s 只读 index。
n=0; noop=0; diffidx=0
while IFS= read -r f; do
  n=$((n+1))
  h=$(git hash-object "$f"); i=$(git ls-files -s "$f" | awk '{print $2}')
  [ "$h" = "$i" ] && noop=$((noop+1))
  [ "$i" != "$(git rev-parse HEAD:"$f")" ] && diffidx=$((diffidx+1))
done < <(git ls-files)
echo "tracked=$n  renormalize_no_op=$noop/$n  index!=HEAD_blob=$diffidx"

# === 收尾自检 ===
git rev-parse HEAD
git rev-list --count HEAD                              # 全仓 commit 数
git rev-list --count origin/main..HEAD                 # 领先 origin/main 的 commit 数
git status --porcelain --untracked-files=no            # 自检 1：期望空
git status --porcelain | grep '^?' | wc -l
git diff origin/main..HEAD -- vendor acceptance tasks .gitattributes   # 自检 2：期望空
git diff $BOOTSTRAP..HEAD -- vendor acceptance tasks

# 自检 3：5 个冻结件 sha256 对 MANIFEST，期望 5/5 MATCH
python3 -c "
import json,hashlib,pathlib
m=json.loads(pathlib.Path('acceptance/MANIFEST.json').read_text())
ok=0
for k,v in m.items():
    a=hashlib.sha256(pathlib.Path(k).read_bytes()).hexdigest()
    print(('MATCH  ' if a==v else 'DRIFT  ')+k); ok+= a==v
print('=> %d/%d MATCH'%(ok,len(m)))
"

# 自检 4：8 闸门逐个跑，期望退出码序列 0/0/0/0/0/2/2/0
for g in g0_environment g0_secrets g0_freeze g1_contract g1_memory g1_permissions g1_tools g3_simulate; do
  python3 acceptance/gates/$g.py >/dev/null 2>&1; printf '%s=%d ' "$g" $?
done; echo

# 自检 5：本卷宗自身的消毒复扫，7 类模式全部期望 0 命中。
# 模式串同样按记号书写，执行时换回真实字面量（否则跑这个复扫本身就会往卷宗里写入真实路径）
for p in '<home-prefix>/' '<linux-home-prefix>/' '<win-drive>:\' '<win-drive2>:\' '<win-drive>/Users' '<mac-tmp-prefix>' '<tmp>/'; do
  printf '%-24s -> ' "$p"; grep -c -- "$p" evidence/task_b_gate_objections.md
done

./.venv/bin/python acceptance/run_all.py 2>&1; echo "EXIT=$?"
```

---

*卷宗结束。本文件是集成前那轮取证唯一新增的文件；集成后这轮（条目 A–F、第十章、条目 22 盲区 ③）是对它的就地增补。两轮加起来，仓库内任何既有文件仍未被本仓侧修改过——`git status --porcelain --untracked-files=no` 全程为空、`git diff origin/main..HEAD -- vendor acceptance tasks .gitattributes` 为空，即是证明。*
