# main-repo-target: services/agent-core/agent_core/memory_ranker.py
"""Lexicon-free retrieval ranking for Tianyi's long-term memory facts.

Five-layer scoring model over raw Chinese text (no tokenizer, stdlib only):

  L1 normalize          NFKC fold, casefold, strip whitespace + punctuation
  L2 bigram_similarity  character-bigram multiset cosine (dictionary-free)
  L3 concept_bridge     small concept lexicon bridges non-overlapping wordings
  L4 preference_bonus   explicit preference assertions ("喜欢 X") count as
                        stronger evidence for stable-attribute queries
  L5 transient_penalty  tense markers ("最近/今天") demote short-term states
                        when the query asks for a stable attribute

Layers are separate pure functions so each signal can be unit-tested and the
weight constants can be perturbed independently (sensitivity analysis lives
in evidence/task_b_retrieval_analysis.md).

Docstring 约定（审查发现 L11）：本模块与 memory_store 的每个函数 docstring
一律分两段：首段纯英文写契约（Contract: 输入 -> 输出、值域、边界约定），
设计理由另起一段用中文，两段之间空行分隔。英文契约段里不夹中文例词，需要
举中文例子时放进中文段——这样审阅者只读英文段就能拿到接口口径，中文段承担
「为何这么设计」的解释，两者不互相污染。例外：上面这张分层总览表里保留了
中文例词（「喜欢 X」「最近/今天」），因为那些词就是各层实际要比对的资料，
换成英文描述反而丢了信息；例外只适用于模块级总览，不适用于函数 docstring。

术语约定（审查发现 M19）：L5 的中文名一律用「时态降权」，L4 用「极性感知
偏好加分」；不混用「短期状态降权」「时态惩罚」等别名，以免文档与代码对不
上同一样东西。
"""
from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True, slots=True)
class ConceptClass:
    """One semantic class: head words name the concept, members are typical
    values / synonymous surface forms used to detect hits."""

    name: str
    head: tuple[str, ...]
    member: tuple[str, ...]


# 概念词典：每类 head 是概念名，member 是典型取值/同义表达。
# 反过拟合硬约束（tests 里机器可验证）：每类 ≥3 个 member 不在评测 golden
# 集任何位置出现，词典因此是通用概念知识而非答案换皮。member 用子串
# 命中，允许跨类重叠（如「老师」同属称呼与职业）：真实概念本就有交叠，
# 桥接强度由双侧命中数共同决定，单类重叠不会单独拉开分差。
# head 一律不用单字（审查发现 M1）：单字做子串命中会让「超市/角色/脸色/
# 色号」被误判成城市/颜色类提问，稳定属性门控随之误开、L5 反噬对题的近期
# 事实。golden 的 8 个查询全部含双字 head，去掉单字不影响评测。
#
# 外层用 MappingProxyType 包一层（审查发现 L6）：ConceptClass 是 frozen
# dataclass，但字典本身可写，运行期任何一处 CONCEPT_LEXICON["颜色"] = …
# 或 .pop() 都会静默改变打分语义，而这类变更不会让任何测试变红。包成只读
# 映射后，改词典只能整体替换模块属性（变异演练走的就是这条路），在 diff 与
# 运行时都看得见。
CONCEPT_LEXICON: Mapping[str, ConceptClass] = MappingProxyType({
    "颜色": ConceptClass(
        name="颜色",
        head=("颜色",),
        member=("红", "橙", "黄", "绿", "青", "蓝", "紫", "黑", "白", "灰", "粉", "棕", "金", "银"),
    ),
    "城市": ConceptClass(
        name="城市",
        head=("城市",),
        member=("北京", "上海", "广州", "深圳", "杭州", "南京", "成都", "武汉", "西安", "苏州", "天津", "重庆", "家乡", "籍贯"),
    ),
    "称呼": ConceptClass(
        name="称呼",
        head=("称呼", "名字", "姓名"),
        member=("叫", "昵称", "老板", "老师", "先生", "女士", "小姐", "同学"),
    ),
    "生日": ConceptClass(
        name="生日",
        head=("生日", "出生"),
        member=("月", "日", "号", "年龄", "岁", "星座"),
    ),
    "宠物": ConceptClass(
        name="宠物",
        head=("宠物",),
        member=("猫", "狗", "兔子", "仓鼠", "鹦鹉", "乌龟", "金鱼", "蜥蜴", "养"),
    ),
    "过敏": ConceptClass(
        name="过敏",
        head=("过敏",),
        member=("花粉", "海鲜", "芒果", "尘螨", "敏感", "忌口", "乳糖", "酒精", "药物"),
    ),
    "职业": ConceptClass(
        name="职业",
        head=("职业", "工作"),
        member=("上班", "公司", "工程师", "程序员", "老师", "教师", "医生", "护士", "设计师", "会计", "律师", "司机", "职员"),
    ),
    "爱好": ConceptClass(
        name="爱好",
        head=("爱好", "兴趣"),
        member=("喜欢", "热爱", "徒步", "登山", "跑步", "游泳", "骑车", "唱歌", "画画", "读书", "旅游", "摄影", "钓鱼", "健身", "运动"),
    ),
})

# L1 剥离集：ASCII 标点 + CJK 标点/全角符号区 + 通用标点区 + 各类空白。
# 宁可多剥：字面相似度层只关心内容字符，标点在全角/半角混写时本身就不稳定。
# 补上 \u2000-\u206f 与 \u00b7（审查发现 L4）：通用标点区里有中文排版常用的
# 破折号、弯引号、省略号与零宽空格（U+200B/200C/200D），\u00b7 是间隔号
# 「·」（外国人名与作品名常带）。这些字符不剥会直接进 bigram 多重集，把
# 「洛·天依」与「洛天依」算成不同内容；零宽空格更隐蔽，肉眼看不出差异
# 却能让字面相似度归零。NFKC 已先一步把上标/下标形式折成普通数字与字母，
# 所以 U+2070-209F 落在本区间里不会误剥内容字符。
_STRIP_RE = re.compile(
    "[\\s"
    "!-/:-@\\[-`{-~"
    "\u00b7"
    "\u2000-\u206f"
    "\u3000-\u303f"
    "\uff00-\uffef"
    "]+"
)


def normalize(text: str) -> str:
    """L1: fold to a comparison-safe form.

    Contract: any str in -> str out. NFKC (folds fullwidth ASCII to
    halfwidth), casefold, then strip whitespace and ASCII/CJK punctuation.
    CJK ideographs and digits survive; the result is what L2-L5 match on.

    用 casefold() 而不是 lower()（审查发现 L4）：lower() 不做完全大小写
    折叠，德语 ß、希腊_final sigma 与部分连字 ligature 在 lower() 下仍与
    对应形式不等，两侧归一化后字面相似度会假阴。docstring 一直写的就是
    casefold，实现却用 lower，属文档与代码不符。对 CJK 无影响，对拉丁
    专有名（歌名/软件名）才体现差别。
    """
    folded = unicodedata.normalize("NFKC", text).casefold()
    return _STRIP_RE.sub("", folded)


def _ngram_multiset(text: str, n: int) -> Counter[str]:
    return Counter(text[i : i + n] for i in range(len(text) - n + 1))


@dataclass(frozen=True, slots=True)
class _TextProfile:
    """Everything the layers need from one string, computed once.

    normalized 供 L3/L4/L5 的子串命中复用；bigrams 与 unigrams 两个阶都预先
    建好，因为退化规则要按「双侧长度的较小值」选 n，选哪个阶要到配对时才能
    决定。审查发现 M6：旧实现每条 candidate 都重建 query 的 Counter，一次
    rank 里 query 侧的字符串切片做了 O(candidates) 遍。
    """

    normalized: str
    bigrams: Counter[str]
    unigrams: Counter[str]


def _profile(text: str) -> _TextProfile:
    normalized = normalize(text)
    return _TextProfile(
        normalized=normalized,
        bigrams=_ngram_multiset(normalized, 2),
        unigrams=_ngram_multiset(normalized, 1),
    )


def _bigram_profile(a: _TextProfile, b: _TextProfile) -> float:
    if not a.normalized or not b.normalized:
        return 0.0
    n = 2 if min(len(a.normalized), len(b.normalized)) >= 2 else 1
    left, right = (a.bigrams, b.bigrams) if n == 2 else (a.unigrams, b.unigrams)
    return _cosine(left, right)


def _cosine(left: Counter[str], right: Counter[str]) -> float:
    if not left or not right:
        return 0.0
    if left == right:
        # 数学上恒为 1，但 sqrt 浮点误差会给出 0.9999999999999998；
        # 「多重集相同必为 1.0」是对外契约，短路保精确。
        return 1.0
    dot = sum(count * right[gram] for gram, count in left.items())
    if dot == 0:
        return 0.0
    norm_left = math.sqrt(sum(count * count for count in left.values()))
    norm_right = math.sqrt(sum(count * count for count in right.values()))
    return dot / (norm_left * norm_right)


def bigram_similarity(a: str, b: str) -> float:
    """L2: character-bigram multiset cosine over normalized text.

    Contract: two raw strings in -> float in [0.0, 1.0] out. 1.0 iff the two
    normalized n-gram multisets are proportional — that includes identical
    strings AND repetition-only variants, because cosine is scale-invariant.
    0.0 for disjoint gram sets or empty input.
    Degradation rule: if either side normalizes to fewer than 2 chars it has
    no bigrams, so BOTH sides fall back to unigram multisets (mixed n-gram
    orders would always intersect in zero and silently kill the signal).

    审查发现 M3 的处置：旧 docstring 声称「1.0 只给归一化后完全相同的字符
    串」，但余弦对成比例向量恒为 1（例如「哈哈」与「哈哈哈哈」得 1.0），
    契约与实现不符。两个修法里选「改契约」
    而不是「改实现」（在 _cosine 后乘 min(len)/max(len) 的长度阻尼）：阻尼会
    系统性惩罚「查询短、事实长」这一常态形态——golden 与留出集里的事实普遍
    长于查询——把 L2 从内容探测器变成长度探测器。成比例为 1 的语义是
    「n-gram 分布相同」，对重复型文本判为高度相似在检索语境里是可接受的：
    它们是同一个内容的重复，而不是不同内容。改实现会动所有 L2 数值、需重做
    全部权重敏感性与逐层消融，收益却是把一个诚实的性质藏起来。
    """
    return _bigram_profile(_profile(a), _profile(b))


def _masked_scan(text: str, words: tuple[str, ...]) -> list[str]:
    """Longest-first greedy scan over normalized text.

    Contract: normalized text + words in -> the matched words out, forming the
    largest non-overlapping subset the greedy finds; each word appears at most
    once in the result.

    最长优先贪心掩码（审查发现 M4）：`sum(1 for w in words if w in text)`
    对嵌套词重复计数——「颜色」会同时命中 head「颜色」与旧 head「色」，
    「生日」会同时命中「生日」与 member「日」。同样的证据强度只因该类词表
    存在嵌套关系就被抬高，跨类不可比，与 concept_bridge docstring「几何均值
    让单个弱命中不超过 head 级命中」的口径不符。贪心按词长降序取最大不重叠
    集合，是该问题的标准近似解；对本词表（最长 3 字）它给出的就是最优解。
    """
    used = bytearray(len(text))
    matched: list[str] = []
    for word in sorted(words, key=len, reverse=True):
        start = text.find(word)
        while start != -1:
            end = start + len(word)
            if not any(used[start:end]):
                used[start:end] = b"\x01" * len(word)
                matched.append(word)
                break
            start = text.find(word, start + 1)
    return matched


def _masked_hits(text: str, words: tuple[str, ...]) -> int:
    """Count the largest non-overlapping subset of `words` present in text."""
    return len(_masked_scan(text, words))


def _concept_hits(text: str, concept: ConceptClass) -> int:
    """Count head+member hits (substring, non-overlapping) in normalized text."""
    return _masked_hits(text, (*concept.head, *concept.member))


# query 侧预计算与长度上限（审查发现 M6）。真实查询是用户一句话，500 字符
# 已远超；不设上限则单条恶意超长 query 可拖垮每轮对话——recall_relevant 是
# 拼 prompt 的必经路径，而 rank()/score() 的开销与 query 长度成正比。
_MAX_QUERY_CHARS = 500


@dataclass(frozen=True, slots=True)
class _QueryContext:
    """Everything the four layers need from the query, computed once per rank.

    concept_hits 按 CONCEPT_LEXICON 的迭代序存放每类的 query 侧命中数，
    stable 是「查询含任一 head 词」的 L4/L5 门控，polarity 见 _query_polarity。
    """

    profile: _TextProfile
    concept_hits: tuple[int, ...]
    stable: bool
    polarity: int


def _stable_from_normalized(normalized: str) -> bool:
    return any(head in normalized for concept in CONCEPT_LEXICON.values() for head in concept.head)


def _polarity_from_normalized(normalized: str, stable: bool) -> int:
    """Query orientation: -1 negative, +1 positive, 0 silent (diagnosis RC-5).

    Contract: normalized query text + the stable-attribute flag in -> int out,
    always one of (-1, 0, 1). Negative markers are checked first and win.

    问句的极性决定答案该有的极性：「喜欢 X 吗」问的是正向偏好，「讨厌 X 吗」
    问的是负向约束。这与事实侧用 POSITIVE_MARKERS / NEGATIVE_MARKERS 判极性
    是同一条语言学事实——原实现已经在事实侧承认它，也在查询侧承认了**负向**
    （QUERY_NEGATIVE_MARKERS），唯独漏了查询侧的正向，于是「用户喜欢喝什么
    饮品」这类查询的 polarity 落到 0，L4 对它完全静默，否定事实不受任何惩罚。
    补上正向谓词检测是把已有的对称性补全，不是新增语义。

    stable 仍然单独保留为一条充分条件：含 head 词的查询（「用户的过敏原」）
    即使没有偏好谓词也在问稳定属性，L4 该生效。
    """
    if _masked_hits(normalized, QUERY_NEGATIVE_MARKERS):
        return -1
    if stable or _masked_hits(normalized, POSITIVE_MARKERS):
        return 1
    return 0


def _query_context(query: str) -> _QueryContext:
    """Precompute the query side once so per-candidate work stays O(fact).

    Contract: raw query in -> _QueryContext out; the query is truncated to
    _MAX_QUERY_CHARS before anything else is computed.

    rank() 里每条 candidate 都重算一遍 query 的归一化与 Counter 是纯浪费：
    旧实现 4 个层函数各自独立调 normalize(query)，合计每条 candidate 5 次
    归一化 + 4 次 Counter 重建。实测（本机，500 candidates）：短 query 下
    rank() 从 150.9 ms 降到 15.2 ms；query 拉到 100000 字符时旧实现要 72.70 s，
    已接近 run_all.py 的 120 秒硬超时，而 candidate 再涨一个量级就会撞穿；
    截断后三种 query 长度一律 15.8 ms，开销与 query 长度解耦。
    score(query, fact) 的公开双参签名不变，预计算走内部路径。
    """
    normalized = normalize(query[:_MAX_QUERY_CHARS])
    stable = _stable_from_normalized(normalized)
    return _QueryContext(
        profile=_TextProfile(
            normalized=normalized,
            bigrams=_ngram_multiset(normalized, 2),
            unigrams=_ngram_multiset(normalized, 1),
        ),
        concept_hits=tuple(_concept_hits(normalized, c) for c in CONCEPT_LEXICON.values()),
        stable=stable,
        polarity=_polarity_from_normalized(normalized, stable),
    )


def _concept_profile(context: _QueryContext, fact: _TextProfile) -> float:
    contributions: list[float] = []
    for qh, concept in zip(context.concept_hits, CONCEPT_LEXICON.values()):
        if qh == 0:
            continue
        fh = _concept_hits(fact.normalized, concept)
        if fh == 0:
            continue
        strength = math.sqrt(qh * fh)
        contributions.append(strength / (strength + 1.0))
    if not contributions:
        return 0.0
    return sum(contributions) / len(contributions)


def concept_bridge(query: str, fact: str) -> float:
    """L3: lexicon-bridged semantic affinity in [0.0, 1.0].

    Contract: two raw strings in -> float out. For every concept class hit by
    BOTH sides (head or member, substring match on normalized text), the
    class contributes sqrt(qh*fh) / (sqrt(qh*fh) + 1) where qh/fh are the
    per-side hit counts; the result is the mean over contributing classes.
    One-sided hits contribute nothing — a bridge needs both banks, otherwise
    every fact sharing a stock lead-in phrase with the query would collect
    noise points. The geometric mean keeps a lone weak member-level hit from
    outranking a solid head-level match.

    设计理由：单边命中不计分是必需的——真实记忆里几乎每条事实都以「用户」
    开头，若单边也算桥接，这个高频引导词会让所有事实彼此拿分，L3 退化成
    噪声源。取几何均值而不是命中数相加，是为了让「查询只提到一个偏好动词（它
    同时是爱好类的 member）」这种弱命中压不过「双侧都命中 head」的强命中。
    """
    return _concept_profile(_query_context(query), _profile(fact))


# 合成权重：全局常量，禁止按样例逐条调参；扰动敏感性分析见
# evidence/task_b_retrieval_analysis.md。
W_BIGRAM = 0.30
W_CONCEPT = 0.55
W_PREFERENCE = 0.10
W_TRANSIENT = 0.35


# 偏好/断言谓词，按极性分两组（审查发现 M2）。旧实现把肯定与否定谓词
# 混在一个 PREFERENCE_MARKERS 里且不辨查询极性，于是查询「用户的爱好」下
# 「用户讨厌运动」拿到与「用户周末喜欢徒步」同等的加分并排到 top-1——
# 注入 extra_system 即语义反转，LLM 会据此以为用户喜欢运动。
# NEGATIVE_MARKERS 收「过敏」而不只「过敏于」：「用户对海鲜过敏」是负面约束
# 断言最典型的表达形式，也是忌口类提问最对题的证据。
POSITIVE_MARKERS: tuple[str, ...] = (
    "最喜欢", "喜欢", "希望", "热爱", "偏好", "爱吃", "感兴趣", "只想",
)
NEGATIVE_MARKERS: tuple[str, ...] = (
    "不喜欢", "讨厌", "不吃", "受不了", "忌讳", "过敏",
)

# 查询侧的负面取向词：问「忌口/讨厌/不能吃」时，否定谓词才是对题证据。
QUERY_NEGATIVE_MARKERS: tuple[str, ...] = (
    "不喜欢", "讨厌", "忌口", "忌讳", "禁忌", "不能吃", "吃不了", "受不了", "过敏",
)

# 时态降权（L5）用的时态标记：短期状态/临时行为的信号词。
# 「刚」是单字，会误伤「刚才/金刚」类词——已知噪声，只在稳定属性
# 提问下生效，影响面可控，换双字词会漏掉「刚换/刚养」这类真实表达。
TRANSIENT_MARKERS: tuple[str, ...] = (
    "最近", "这几天", "今天", "昨天", "刚", "正在", "临时",
)


def _marker_count(text: str, markers: tuple[str, ...]) -> int:
    return sum(1 for marker in markers if marker in text)


def _is_stable_attribute_query(query: str) -> bool:
    """Gate for L5: does the query ask for a stable attribute?

    Contract: raw query in -> bool out. True iff the normalized query
    contains at least one CONCEPT_LEXICON head word.

    行为式提问（「周末一般干嘛」）不含 head 词，时态降权对它们保持静默；否则
    「用户最近喜欢吃辣」这种恰恰对题的回答会被误伤。RC-5 之后 L4 不再单独依赖
    本门控（查询侧偏好谓词也能开启 L4），但 L5 仍然只认 head 词：两层的门控
    语义不同——L4 问的是「这条查询有没有极性取向」，L5 问的是「这条查询是不是
    在问一个稳定属性」，后者为真时短期状态才是干扰项。不共用一个开关。
    """
    return _stable_from_normalized(normalize(query[:_MAX_QUERY_CHARS]))


def _query_polarity(query: str) -> int:
    """Classify the query's orientation: +1 positive, -1 negative, 0 silent.

    Contract: raw query in -> int out. -1 when the query itself asks for a
    negative orientation (dietary taboo, dislike, cannot eat, allergy); +1 when
    it asks for a stable attribute (normalized query contains a CONCEPT_LEXICON
    head word) OR carries a positive preference predicate; 0 otherwise, in which
    case L4 stays silent.

    负面判定优先于正面：「用户对花粉过敏」既含 head「过敏」也含负面取向词，此时
    它问的是负面约束，按 -1 处理才对题；「用户不喜欢什么」里含子串「喜欢」，也
    必须判 -1。

    正向有两条独立的开启路径（诊断编号 RC-5）：head 词在场，或 POSITIVE_MARKERS
    里的偏好谓词在场。原实现只有前者，于是「用户喜欢喝什么饮品」的 polarity 落到
    0，L4 对它完全静默，「用户不喝酒」这类否定事实不受任何惩罚，靠 L2 的短文本
    余弦优势抢到 top-1。事实侧早就同时认这两条（POSITIVE_MARKERS /
    NEGATIVE_MARKERS），查询侧只认了负向——补正向是把已有的对称性补全。

    中性（0）仍然保留：不含 head 词也不含偏好谓词的行为式提问（「周末一般干嘛」）
    让 L4 静默，否则闲聊查询也会被带偏好词的事实抢位。
    """
    normalized = normalize(query[:_MAX_QUERY_CHARS])
    return _polarity_from_normalized(normalized, _stable_from_normalized(normalized))


def _polarity_hits(text: str) -> tuple[int, int]:
    """Joint polarity scan over normalized text -> (positive, negative) hits.

    Contract: normalized text in -> (int, int) out, both >= 0.

    两组必须一起扫描并共享掩码：「不喜欢」含子串「喜欢」，分开扫描会让
    肯定词与否定词各计一次、极性互相抵消。
    """
    matched = _masked_scan(text, POSITIVE_MARKERS + NEGATIVE_MARKERS)
    positive = sum(1 for word in matched if word in POSITIVE_MARKERS)
    return positive, len(matched) - positive


def _preference_profile(context: _QueryContext, fact: _TextProfile) -> float:
    if context.polarity == 0:
        return 0.0
    positive, negative = _polarity_hits(fact.normalized)
    if context.polarity > 0:
        matched, opposed = positive, negative
    else:
        matched, opposed = negative, positive
    return min(matched, 2) / 2.0 - min(opposed, 2) / 2.0


def _transient_profile(context: _QueryContext, fact: _TextProfile) -> float:
    if not context.stable:
        return 0.0
    return min(_marker_count(fact.normalized, TRANSIENT_MARKERS), 2) / 2.0


def preference_bonus(query: str, fact: str) -> float:
    """L4: polarity-aware predicate evidence, signed.

    Contract: raw query+fact in -> float in [-1.0, 1.0] out. Non-zero only when
    the query carries an orientation (see _query_polarity); predicates matching
    that orientation add, opposing ones subtract. Each side saturates at
    min(count, 2) / 2.

    「喜欢 X」是对偏好的显式肯定断言，「讨厌 X」是否定断言，两者对同一个
    提问的证据价值符号相反；「在 X」只陈述行为，不带极性信号。旧实现只加分
    不辨极性，问「爱好」时否定事实与肯定事实同分甚至更高（审查发现 M2）。
    饱和计数保留：多个同向谓词叠加只小幅增信，防止堆词刷分。
    """
    return _preference_profile(_query_context(query), _profile(fact))


def transient_penalty(query: str, fact: str) -> float:
    """L5: tense demotion — short-term states yield to stable attributes.

    Contract: raw query+fact in -> float in [0.0, 1.0] out (subtracted from
    the final score by score()). Non-zero only when the query asks for a
    stable attribute AND the fact carries at least one tense marker.

    设计理由（L5 的中文名统一叫「时态降权」，审查发现 M19）：查询「用户的
    爱好/职业」问的是稳定属性，带时态标记（最近/今天/刚…）的事实是短期
    状态，不该抢占稳定属性的召回位；反之问「最近干嘛」时这些事实恰恰对题，
    所以门控必须双向生效。
    """
    return _transient_profile(_query_context(query), _profile(fact))


def _score_with_context(context: _QueryContext, fact: str) -> float:
    """Score one fact against an already-precomputed query context.

    Contract: _QueryContext + raw fact in -> float out, bit-for-bit equal to
    score(query, fact) for the query the context was built from.

    fact 的归一化与两个 n-gram Counter 也只算一次就交给四层复用，所以每条
    candidate 的归一化次数从 5 降到 1（审查发现 M6）。
    """
    profile = _profile(fact)
    return (
        W_BIGRAM * _bigram_profile(context.profile, profile)
        + W_CONCEPT * _concept_profile(context, profile)
        + W_PREFERENCE * _preference_profile(context, profile)
        - W_TRANSIENT * _transient_profile(context, profile)
    )


def score(query: str, fact: str) -> float:
    """Compose the five layers into one relevance score.

    Contract: raw query+fact in -> float out (may be negative when L5 fires
    hard). score = W_BIGRAM*L2 + W_CONCEPT*L3 + W_PREFERENCE*L4 -
    W_TRANSIENT*L5. The weights are module-level constants on purpose:
    per-example tuning would turn the lexicon into golden-set camouflage.
    """
    return _score_with_context(_query_context(query), fact)


def rank(query: str, candidates: list[str]) -> list[tuple[str, float]]:
    """Order candidates by relevance, keeping the full list.

    Contract: raw query + candidate facts in -> [(fact, score), ...] out,
    descending by score. Ties keep input order (list.sort is stable), so
    results are reproducible across runs. Callers wanting top-k slice the
    result themselves: score_retrieval always takes top-1 by protocol, while
    MemoryStore.recall_relevant takes top-`limit` — its default is 1 so the
    common path is top-1, but the parameter is genuinely top-k and the old
    wording here wrongly described both callers as top-1 (review finding L7).
    """
    context = _query_context(query)
    scored = [(candidate, _score_with_context(context, candidate)) for candidate in candidates]
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored


def rank_indices(query: str, payloads: list[str]) -> list[int]:
    """Order the indices of payloads by relevance, most relevant first.

    Contract: raw query + parallel payload list in -> list of indices out,
    same length as the input, descending by score, ties keeping input order.

    与 rank() 的差别是返回下标而不是（文本, 分数）对。MemoryStore 的 facts
    表无 UNIQUE 约束，同一文本可以合法地对应多行；按文本反查行会把多行归并
    成一行（审查发现 H1），所以排序层必须能把身份交回给调用方。query 上下文
    只算一次，开销与 rank() 同量级。
    """
    context = _query_context(query)
    scored = [
        (index, _score_with_context(context, payload)) for index, payload in enumerate(payloads)
    ]
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return [index for index, _ in scored]


def _as_text(value: object) -> str:
    """Coerce one golden-set field to str without inventing content.

    Contract: any value in -> str out; None yields "" rather than "None".

    审查发现 L3：str(item.get("query", "")) 只对「键缺失」给空串，键存在而
    值为 None 时会得到字面量 "None"——一个四字符的拉丁查询，会与任何含
    "none" 的事实产生虚假字面相似度，把脏评测数据伪装成检索结果。评测集
    出现 None 属于数据缺陷，这里的处置是降级成空字符串而不是造出一个能
    参与打分的词；空字符串经 rank() 后所有 candidate 同分，由同分保留输入序
    的约定给出确定结果。
    """
    return "" if value is None else str(value)


def score_retrieval(golden: list[dict]) -> dict[str, float]:
    """Evaluate top-1 retrieval quality against a golden set.

    Contract: list of {"query": str, "stored": [facts...], "relevant":
    [facts...]} in -> {"precision": float, "recall": float} out (both keys
    always present; the gate reads them with .get(key, 0), so a missing key
    would silently score zero).

    口径（与 g1_memory 判定一致）：
      - 检索策略 top-1：每条查询只取分数最高的一条。真实用途是往
        extra_system 注入一条最相关记忆，且评测集 relevant 恒为单项；
        需要 top-k 的调用方直接用 rank()。
      - 单条：precision_i = |retrieved ∩ relevant| / |retrieved|（retrieved
        为空记 0.0）；recall_i = |retrieved ∩ relevant| / |relevant|
        （relevant 为空记 0.0，确定性口径，评测集不应出现此形状）。
      - 汇总：宏平均（macro），mean(precision_i) / mean(recall_i)。
      - 空 golden 集：无样本可评，两指标均记 0.0。
    """
    if not golden:
        return {"precision": 0.0, "recall": 0.0}
    precisions: list[float] = []
    recalls: list[float] = []
    for item in golden:
        query = _as_text(item.get("query"))
        stored = [_as_text(fact) for fact in item.get("stored", [])]
        relevant = {_as_text(fact) for fact in item.get("relevant", [])}
        ranked = rank(query, stored)
        retrieved = {ranked[0][0]} if ranked else set()
        hits = len(retrieved & relevant)
        precisions.append(hits / len(retrieved) if retrieved else 0.0)
        recalls.append(hits / len(relevant) if relevant else 0.0)
    return {
        "precision": sum(precisions) / len(precisions),
        "recall": sum(recalls) / len(recalls),
    }
