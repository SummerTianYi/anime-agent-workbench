"""Anti-overfit audit of CONCEPT_LEXICON: the H2 criterion, rebuilt (审查发现 H2).

为什么旧判据必须换掉（这是实测结论，不是推测）
    阶段一的断言是「每个语义类至少 3 个 member 从未出现在 **golden** 集里」。
    审查者证明它零判别力：把每类 member 换成「仅 golden 答案词 + 3 个填充词
    qqa/qqb/qqc」，断言照样 8/8 PASS、golden 宏平均照样 1.000。本文件的
    `OldCriterionHadNoDiscriminatingPowerTests` 把这个实验原样复现并钉成测试，
    所以「旧判据无效」在本仓里是机器可验证的事实，而不是一句指控。

    旧判据失效有两个独立原因，新判据必须同时堵住：
      1. 语料范围只有 golden。城市类 14 个 member 里有 12 个出现在
         golden ∪ v1 ∪ v2（占比 0.857，只有「天津」「籍贯」unseen），但在
         golden 单集上 unseen 数仍 ≥3 —— 于是「v1 的答案词全进了词典」这件
         事被完全遮蔽。范围必须扩到三集并集。
      2. 判据是「unseen 的**个数**下限」。个数可以被填充词无代价地凑够，
         因为它不看分母。改成「seen/total 的**占比**上限」后，填充词只会同时
         抬高分子与分母中的分母——除非分母把填充词排除掉，所以占比上限必须
         与「什么算真 member」的判据配套，这就是下面的填充词免疫。

新判据（三条，联合生效）
    对 CONCEPT_LEXICON 的每个类，令 real = 真 member 集合（见下），
    seen = real 中出现在 golden ∪ v1 ∪ v2 任一位置（query/stored/relevant）
    的词，归一化后按子串判定（与 L3 的匹配口径一致，判据必须审的是打分器
    实际会命中的东西，而不是字面拼写）：

      C1 占比上限    len(seen) / len(real) <= MAX_SEEN_RATIO
      C2 规模下限    len(real)            >= MIN_REAL_MEMBERS
      C3 填充词免疫  real 只收含 CJK 表意文字、且非三字以上单字重复的 member

C3 的两条子判据都是「什么算中文词典的成员」的陈述，不是针对 qqa 的 hack：
不含表意文字的 token 永远匹配不上任何中文事实，对检索能力贡献恒为 0；三字
以上的单字重复在中文里几乎总是拟声或占位。二字重叠（画画/看看）不在此列，
那是能产的动词重叠构词——这条线是实测撞出来的，详见 _DEGENERATE_REPEAT。

MAX_SEEN_RATIO = 1/3 的论证
    语义：一个**通用**概念类，其成员里「恰好出现在评测集里」的比例不应超过
    三分之一。取值的两侧约束都是实的：
      - 不能更小。三个评测集合计 100 对、归一化后约 2280 字符，全部围绕
        「中文用户画像」这一个窄领域。一个通用词表在这个领域里的自然命中率
        天然不为零：颜色类 14 个基本颜色词里，日常对话会提到 7 个（红黄青蓝
        黑粉银），占比 0.5，这是「窄领域评测集 × 小封闭词表」的正常现象而不
        是 tailor。把上限压到 0.2 就会把这种正常命中判成过拟合，逼着实现去
        塞无关词凑分母——那是判据在制造过拟合，不是防止它。
      - 不能更大。0.5 意味着「一半的词表是为评测集准备的」，语义上已越界；
        而现状有 5 个类正好落在 0.444-0.615，把上限定在 0.5 或 0.6 会让它们
        「刚好通过」，判据就失去了逼出结构性动作的力量。
    1/3 是同时满足这两侧的最紧的常用分数。它的关键性质是：**当前词典有 7/8
    个类违反它**（颜色 0.500、城市 0.857、称呼 0.500、生日 0.500、宠物
    0.444、职业 0.615、爱好 0.600，只有过敏 0.333 达标）。这不是判据定坏了，
    这正是 H2 要暴露的事实——现有词典在 v1 上就是 tailor 过的，而合规的唯一
    出路是按外部通用知识枚举规则把每个类扩到它应有的规模（扩充的审计痕迹见
    CONCEPT_LEXICON 上方的枚举规则注释与 report_retrieval.py 的 lexicon 模式）。

    「上限是不是照着现状倒推的」这一质疑可以被 diff 直接否证：倒推的典型形态
    是把常量定在刚好让现状通过（0.857），而定 1/3 的结果是现状大面积变红。
    一个让自己通过的判据没有判别力，一个让现状失败的判据才有。

MIN_REAL_MEMBERS = 12 的论证
    C1 单独用是可以被稀释的：加 100 个填充词就能把 0.857 拉到 0.08。C3 挡住
    的是「廉价填充」（非中文、单字重复），挡不住「大量长得像中文词的填充」，
    后者要外部词频表才能判，超出本仓「纯标准库」的约束。C2 是这条防线的补充：
    它让「少量填充 + 极少真词」这种最省事的绕过直接失败（1 个答案词 + 3 个
    填充 → real=1 < 12）。
    取 12 的依据是「按通用枚举规则能生成的规模的下界」：城市类按「省级行政
    中心 + 计划单列市 + 各省人口前三地级市」约 130 个，职业类按「以
    师/员/家/工/生/手/士 结尾的职业名词 + 常见职务词」约 60 个，颜色类按
    「基本色 + 常见复合色」约 45 个，爱好/过敏/宠物/称呼/生日按各自的通用
    枚举也都在 15 以上。12 低于其中最小的那个，留了余量给「有些类天然小」，
    又高到让任何「只放答案词」的词表无法通过。

已知局限（如实记录，不粉饰）
    三条联合能抓住：小词表 tailor（C2）、非中文/退化填充稀释（C3 + C1）、
    高占比 tailor（C1）。抓不住：往类里塞几十上百个「看起来像中文词但检索上
    无用」的词来稀释占比（`test_bulk_cjk_filler_is_a_documented_blind_spot` 把
    这个盲区钉成了测试）。判定这种需要词频或词表外部知识，纯标准库下无解；
    它属于「有意的、高成本的作弊」而非「无意的过拟合」，而本判据的目标是后者。
    第二个局限：seen 按子串判定，单字 member 会因为落在无关词里而被算成 seen
    （「银」在「银行」里）。这让判据**偏严**而不是偏松，方向是安全的。
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path
from types import MappingProxyType
from unittest import mock

TESTS = Path(__file__).resolve().parent
REPO = TESTS.parent
for _path in (str(REPO), str(TESTS)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from src import memory_ranker as mr  # noqa: E402
from holdout_v2 import HOLDOUT_V2  # noqa: E402
from test_memory_retrieval import HOLDOUT_GOLDEN  # noqa: E402
from acceptance.gates.g1_memory import GOLDEN  # noqa: E402

# 三条判据的常量。取值论证写在模块 docstring 里，改这两个数字等于改判据，
# 在 diff 里必须连同论证一起改——所以它们不许内联在断言里。
MAX_SEEN_RATIO = 1 / 3
MIN_REAL_MEMBERS = 12

# C3 填充词免疫的两个判据。
# CJK 表意文字：本词典是中文概念词典，它的全部作用是桥接中文改写；一个不含
# 表意文字的 token 永远匹配不上任何中文事实，对检索能力的贡献恒为 0，把它计入
# 分母就是定义上的填充。这条不是针对 qqa 的 hack，而是「什么算中文词典的成员」
# 的陈述，所以它同样适用于未来任何拉丁/数字/符号填充。
_CJK_IDEOGRAPH = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
# 单字重复：拟声与占位，不是概念实例。**线划在重复至少三次（总长 ≥3）**，因为
# 中文有能产的动词重叠构词（AA 式：画画/看看/聊聊/走走），它们是真实概念词；
# 而三个以上相同字符连排在中文里几乎总是拟声或占位（哈哈哈/啊啊啊/嘻嘻嘻）。
# 这条线是写测试时实测撞出来的：初版用 `^(.)\1+$`（总长 ≥2），把爱好类合法的
# 「画画」判成填充词踢出了分母，占比从 9/15 变成 9/14 —— 判据自己制造了偏差。
_DEGENERATE_REPEAT = re.compile(r"^(.)\1{2,}$")

# 三个评测集。名字与 report_retrieval.py 的 CORPORA 一致，两处必须同步。
CORPORA = {"golden": GOLDEN, "v1": HOLDOUT_GOLDEN, "v2": HOLDOUT_V2}


def corpus_text(corpus: list[dict]) -> str:
    """Normalize every string of one corpus into a single searchable blob."""
    parts: list[str] = []
    for pair in corpus:
        parts.append(str(pair.get("query") or ""))
        parts += [str(fact) for fact in pair.get("stored", [])]
        parts += [str(fact) for fact in pair.get("relevant", [])]
    return mr.normalize("\n".join(parts))


def union_text() -> str:
    """golden ∪ v1 ∪ v2, normalized. H2 的语料范围（旧判据只有 golden）。"""
    return "".join(corpus_text(corpus) for corpus in CORPORA.values())


def real_members(members: tuple[str, ...]) -> tuple[str, ...]:
    """C3: the members that count toward the anti-overfit denominator."""
    return tuple(
        word for word in members
        if _CJK_IDEOGRAPH.search(word) and not _DEGENERATE_REPEAT.match(word)
    )


def audit_class(concept, haystack: str) -> dict:
    """Audit one concept class against a corpus blob -> C1/C2/C3 evidence."""
    real = real_members(concept.member)
    seen = tuple(w for w in real if mr.normalize(w) in haystack)
    return {
        "name": concept.name,
        "declared": len(concept.member),
        "real_total": len(real),
        "seen": seen,
        "seen_count": len(seen),
        "ratio": (len(seen) / len(real)) if real else 1.0,
        "padding": tuple(w for w in concept.member if w not in real),
        "c1_ok": bool(real) and (len(seen) / len(real)) <= MAX_SEEN_RATIO,
        "c2_ok": len(real) >= MIN_REAL_MEMBERS,
        "c3_ok": len(real) == len(concept.member),
    }


def audit_lexicon(lexicon, haystack: str | None = None) -> dict[str, dict]:
    """Audit every class of a lexicon mapping (default: the live one)."""
    blob = union_text() if haystack is None else haystack
    return {name: audit_class(concept, blob) for name, concept in lexicon.items()}


def old_criterion_unseen_count(concept, corpus: list[dict]) -> int:
    """Faithful re-implementation of the phase-1 assertion, for the proof below.

    旧判据原文：`unseen = [w for w in concept.member if mr.normalize(w) not in
    corpus]` 且 `assertGreaterEqual(len(unseen), 3)`，其中 corpus 只有 GOLDEN。
    这里逐字复现它，好让「旧判据在同一个绕过下通过、新判据失败」成为可执行的
    对照，而不是叙述。
    """
    blob = corpus_text(corpus)
    return sum(1 for word in concept.member if mr.normalize(word) not in blob)


class LiveLexiconAuditTests(unittest.TestCase):
    """C1/C2 applied to the real CONCEPT_LEXICON over golden ∪ v1 ∪ v2."""

    @classmethod
    def setUpClass(cls):
        cls.blob = union_text()
        cls.audit = audit_lexicon(mr.CONCEPT_LEXICON, cls.blob)

    def test_union_corpus_covers_all_three_sets(self):
        """护栏：并集真的包含三集，否则占比会被系统性低估（判据变松）。"""
        for name, corpus in CORPORA.items():
            self.assertTrue(corpus, f"{name} 是空的")
            probe = mr.normalize(str(corpus[0]["query"]))
            self.assertIn(probe, self.blob, f"{name} 的首条 query 不在并集里")
        self.assertGreater(len(self.blob), 2000)

    def test_every_class_stays_under_the_seen_ratio_cap(self):
        """C1：出现在任一评测集里的 member 占比不得超过 MAX_SEEN_RATIO。"""
        offenders = {
            name: f"{info['seen_count']}/{info['real_total']}={info['ratio']:.3f}"
            for name, info in self.audit.items() if not info["c1_ok"]
        }
        self.assertEqual(
            offenders, {},
            f"以下概念类的评测集命中率超过 {MAX_SEEN_RATIO:.3f}（说明词表是为评测集 "
            f"tailor 的，而不是通用词表顺带覆盖）：{offenders}。合规修法是按外部通用"
            f"知识枚举规则扩充该类，不是调高这个常量。",
        )

    def test_every_class_has_enough_real_members(self):
        """C2：真 member 数下限，堵「少量填充词 + 极少真词」这条最省事的绕过。"""
        offenders = {
            name: info["real_total"] for name, info in self.audit.items() if not info["c2_ok"]
        }
        self.assertEqual(
            offenders, {},
            f"以下概念类的真 member 数少于 {MIN_REAL_MEMBERS}：{offenders}。"
            f"通用枚举规则能生成的规模远大于此（见模块 docstring）。",
        )

    def test_no_padding_words_are_declared_as_members(self):
        """C3：活词典里不该有任何填充词——它是给绕过用的判据，不是给现状用的。"""
        padded = {name: info["padding"] for name, info in self.audit.items() if info["padding"]}
        self.assertEqual(padded, {}, f"词典里混入了非中文/退化填充词：{padded}")

    def test_audit_reports_are_complete_for_every_class(self):
        """护栏：八个类都被审到，一个都没漏（漏审 = 判据有盲区）。"""
        self.assertEqual(set(self.audit), set(mr.CONCEPT_LEXICON))
        self.assertEqual(len(self.audit), 8)


class OldCriterionHadNoDiscriminatingPowerTests(unittest.TestCase):
    """Reproduce the reviewer's bypass: old criterion PASSes, new one FAILs.

    这是本文件存在的理由。绕过手法原样照抄审查者的描述：把每个类的 member 换成
    「仅 golden 答案词 + 3 个填充词 qqa/qqb/qqc」。golden 答案词取该类里确实出现
    在 GOLDEN 中的 member——这正是「把评测集答案塞进词典」的极端形态。
    """

    FILLERS = ("qqa", "qqb", "qqc")

    @classmethod
    def setUpClass(cls):
        golden_blob = corpus_text(GOLDEN)
        tailored = {}
        for name, concept in mr.CONCEPT_LEXICON.items():
            answers = tuple(w for w in concept.member if mr.normalize(w) in golden_blob)
            tailored[name] = mr.ConceptClass(
                name=concept.name, head=concept.head, member=answers + cls.FILLERS
            )
        cls.tailored = MappingProxyType(tailored)

    def test_bypass_lexicon_is_actually_tailored_to_golden(self):
        """前置事实：构造出的词典确实只剩 golden 答案词 + 填充词。"""
        for name, concept in self.tailored.items():
            answers = concept.member[: -len(self.FILLERS)]
            self.assertTrue(answers, f"{name} 类在 golden 里没有答案词，构造失败")
            self.assertEqual(concept.member[-3:], self.FILLERS)

    def test_old_criterion_passes_the_bypass(self):
        """旧判据在这个完全 tailor 的词典上 8/8 通过——这就是它零判别力的证明。"""
        passed = []
        for name, concept in self.tailored.items():
            unseen = old_criterion_unseen_count(concept, GOLDEN)
            if unseen >= 3:
                passed.append(name)
        self.assertEqual(
            len(passed), 8,
            f"旧判据本应 8/8 通过（填充词 qqa/qqb/qqc 在 golden 里 unseen，凑够 3 个）；"
            f"实测只有 {passed} 通过，说明我对旧判据的复现不忠实，对照证明失效",
        )

    def test_golden_score_is_untouched_by_the_bypass(self):
        """审查者的另一半指控：绕过之后 golden 宏平均照样满分，闸门毫无反应。"""
        with mock.patch.object(mr, "CONCEPT_LEXICON", self.tailored):
            scored = mr.score_retrieval(GOLDEN)
        self.assertGreaterEqual(scored["precision"], 0.8, f"实测 {scored}")
        self.assertGreaterEqual(scored["recall"], 0.8, f"实测 {scored}")

    def test_new_criterion_catches_the_bypass(self):
        """新判据在同一个词典上必须全类失败——判别力增益的直接证据。"""
        audit = audit_lexicon(self.tailored)
        caught_c1 = {name for name, info in audit.items() if not info["c1_ok"]}
        caught_c2 = {name for name, info in audit.items() if not info["c2_ok"]}
        caught_c3 = {name for name, info in audit.items() if not info["c3_ok"]}
        self.assertEqual(
            caught_c1, set(self.tailored),
            f"C1 未能抓住全部 tailor 类，漏掉：{set(self.tailored) - caught_c1}",
        )
        self.assertEqual(caught_c2, set(self.tailored), "C2 未能抓住（real=答案词数<12）")
        self.assertEqual(caught_c3, set(self.tailored), "C3 未能识别 qqa/qqb/qqc 为填充词")
        for name, info in audit.items():
            self.assertEqual(
                info["ratio"], 1.0,
                f"{name} 类的真 member 应当全部来自评测集，占比应为 1.0，实测 {info['ratio']}",
            )

    def test_padding_cannot_dilute_the_ratio(self):
        """填充词免疫的核心性质：加填充词只增加 declared，不增加 real_total。"""
        concept = self.tailored["宠物"]
        diluted = mr.ConceptClass(
            name="宠物", head=concept.head, member=concept.member + tuple(f"qq{c}" for c in "defgh")
        )
        before, after = audit_class(concept, union_text()), audit_class(diluted, union_text())
        self.assertEqual(before["real_total"], after["real_total"], "填充词改变了分母")
        self.assertGreater(after["declared"], before["declared"])
        self.assertEqual(before["ratio"], after["ratio"], "填充词稀释了占比")

    def test_degenerate_repeats_are_not_real_members(self):
        """C3 也覆盖中文填充：三字以上的单字重复不是概念实例。

        同时钉住 AA 式动词重叠不被误伤 —— 这一半是实测踩出来的（见
        _DEGENERATE_REPEAT 上方注释），少了它判据就会把真词当填充踢掉。
        """
        self.assertEqual(real_members(("哈哈哈", "啊啊啊", "嘻嘻嘻")), ())
        # 合法词不许被误伤：单字基本颜色词与 AA 式重叠动词
        self.assertEqual(real_members(("红", "蓝", "黑")), ("红", "蓝", "黑"))
        self.assertEqual(real_members(("画画", "看看", "聊聊", "唱歌")), ("画画", "看看", "聊聊", "唱歌"))
        # 审查者用的拉丁填充词也必须排除（它们同时被 CJK 判据拦住）
        self.assertEqual(real_members(("qqa", "qqb", "zzz")), ())

    def test_bulk_cjk_filler_is_a_documented_blind_spot(self):
        """如实钉住已知局限：大量中文填充词确实能稀释 C1，C2 挡不住它。

        这条测试**断言盲区存在**而不是断言它被防住。把盲区写成测试的意义是：
        将来若有人引入词频表把这条堵上，这条测试会红，提醒他更新 docstring 里
        的「已知局限」段落——盲区被消除时文档必须同步。
        """
        concept = self.tailored["宠物"]
        answers = concept.member[: -len(self.FILLERS)]
        bulk = tuple(chr(0x9FA0 + offset) for offset in range(60))
        smuggled = mr.ConceptClass(name="宠物", head=concept.head, member=answers + bulk)
        info = audit_class(smuggled, union_text())
        self.assertTrue(info["c2_ok"], "60 个真 member 应当通过 C2")
        self.assertLessEqual(info["ratio"], MAX_SEEN_RATIO, "C1 被稀释了——这正是盲区")
        self.assertTrue(info["c3_ok"], "C3 抓不到它：这些字至少是 CJK、也不是单字重复")


class CriterionSelfCheckTests(unittest.TestCase):
    """The criterion must be able to say YES as well as NO, or it is noise."""

    def test_a_genuinely_general_class_passes(self):
        """正例：一个真通用的小词表必须能通过，否则判据只会逼人塞词。"""
        general = mr.ConceptClass(
            name="自检",
            head=("自检",),
            member=(
                "甲字", "乙字", "丙字", "丁字", "戊字", "己字", "庚字", "辛字",
                "壬字", "癸字", "子字", "丑字",
            ),
        )
        info = audit_class(general, union_text())
        self.assertEqual(info["seen_count"], 0)
        self.assertTrue(info["c1_ok"] and info["c2_ok"] and info["c3_ok"], f"实测 {info}")

    def test_seen_detection_uses_the_same_normalization_as_scoring(self):
        """判据必须审「打分器实际会命中的东西」：全角写法也算 seen。

        L3 在归一化文本上做子串匹配，所以词典里写全角「ＰＹ语言」、评测集里
        写半角「py语言」，打分器是会命中的。若判据按字面拼写比，全角/大小写
        差异就会造成假阴（判据偏松）——那正是 H2 失效的同一类错误。
        """
        fullwidth = mr.ConceptClass(name="自检", head=("自检",), member=("ＰＹ语言",))
        self.assertEqual(audit_class(fullwidth, mr.normalize("我在学py语言"))["seen_count"], 1)
        # 反过来：字面拼写相等但归一化后不相等，就不算 seen。
        self.assertEqual(audit_class(fullwidth, mr.normalize("我在学 java 语言"))["seen_count"], 0)

    def test_c3_excludes_tokens_without_any_cjk_ideograph(self):
        """C3 的边界：含 CJK 就算真 member（哪怕夹着拉丁），完全不含才算填充。

        把这条边界钉死是为了防止将来把 C3 悄悄改成「必须以 CJK 开头」之类的
        更严判据——那会让「ＰＹ语言」这种中英混排的真实概念词被踢出分母，
        占比被人为抬高或压低，判据就不再反映打分器的真实行为。
        """
        mixed = mr.ConceptClass(name="自检", head=("自检",), member=("ＰＹ语言", "python语言"))
        self.assertEqual(real_members(mixed.member), ("ＰＹ语言", "python语言"))
        latin = mr.ConceptClass(name="自检", head=("自检",), member=("python", "IDE"))
        self.assertEqual(real_members(latin.member), ())
        self.assertEqual(audit_class(latin, "python")["ratio"], 1.0, "全填充词表占比必须是 1.0")


if __name__ == "__main__":
    unittest.main()
