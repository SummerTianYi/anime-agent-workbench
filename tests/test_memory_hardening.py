"""Round-2 hardening tests for the deferred review findings L1-L8/L11/M19.

TDD 纪律（本文件的写法本身是证据）：这些测试在 `git stash pop` **之前**写好并
在 HEAD 上跑红，红因逐条对应审查发现的缺陷本身，而不是「符号不存在」这种间接
症状——凡是需要引用新符号的地方都走 getattr/hasattr，让断言消息说出缺陷。
应用 stash 里的实现改动后再跑绿。每条的红因原文见各测试的 docstring 与本轮
交付报告第 6 节。

覆盖的发现编号与判据来源（全部为本机实测，非推断）：

  L1  scope 谓词在 memory_store.py 里手抄 2 遍（实测 grep -c = 2，第 77 与
      106 行），无机制强制同步 → 断言字面量只出现 1 次 + 两方法可见集相等 +
      变异演练证明该常量是隔离语义的唯一承载点。
  L2  recall_relevant 对 limit=-1 不报错而是返回「窗口内除最后一条以外的全部
      行」（实测 3 行可见时返回 2 行），limit=True 被当成 1，limit=1.5/'2' 抛
      TypeError（来自切片）而非契约式 ValueError，query=None 抛
      AttributeError: 'NoneType' object has no attribute 'strip'。
  L3  str(item.get("query","")) 对显式 None 产出字面量 "None"，实测能让一条含
      "none" 的事实被排到 top-1 并骗取命中（指标虚高，不是报错）。
  L4  docstring 写 casefold、实现用 lower（实测 normalize('Straße')='straße'
      而 normalize('STRASSE')='strasse'，两者相似度只有 0.5477）；剥离集缺
      General Punctuation 区与间隔号，实测 bigram_similarity('a\\u200bb','ab')
      = 0.0——零宽空格把字面相似度彻底打掉。
  L6  CONCEPT_LEXICON 是可写 dict，实测 item 赋值静默成功、.pop 可用，改词典
      不会让任何测试变红。
  L7  rank() docstring 谎称 score_retrieval 与 recall_relevant 都取 top-1，
      实测后者是 limit 参数化的 top-k。
  L8  memory_store.py 用「Optional」指代 `| None`，而全仓零 typing.Optional。
  L11 英文契约段里夹中文分句，实测 5 处（_is_stable_attribute_query /
      _query_polarity / bigram_similarity / concept_bridge / transient_penalty）。
  M19 时态降权层的中文名未统一，实测全 src/ 零处出现「时态降权」。
"""
from __future__ import annotations

import inspect
import re
import sys
import unittest
from pathlib import Path
from types import MappingProxyType
from unittest import mock

TESTS = Path(__file__).resolve().parent
REPO = TESTS.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from src import memory_ranker as mr  # noqa: E402
from src import memory_store as ms  # noqa: E402


def _src(rel: str) -> str:
    """Read one repo-relative source file as text (never hardcode a path)."""
    return (REPO / rel).read_text(encoding="utf-8")


# L1 的谓词字面量：冻结的 scope 语义，逐字节抄自 HEAD 的两处手抄。
_SCOPE_PREDICATE = "scope = 'global' OR session_id = ?"

# L11 判据：含 "Contract:" 的段落里不许出现 CJK 表意文字。
# 为什么只查表意文字、不查中文标点：memory_store._sanitize_fact 的契约段里有
# 【】，那是该函数要中和的**字面对象**（伪造段落标记），不是中文叙述；把它算
# 成违反会逼实现把安全边界的关键资料从契约里删掉。实测 HEAD 的 5 处违反全部
# 含表意文字，所以收窄判据不减判别力。
_CJK_IDEOGRAPH = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")

# M19 的统一术语与被禁别名。别名清单是「可能与『时态降权』指同一层」的中文
# 措辞枚举，实测 HEAD 上一个都没出现（那条断言是护栏，红的是术语缺失那条）。
_TRANSIENT_TERM = "时态降权"
_TRANSIENT_ALIASES = ("短期状态降权", "时态惩罚", "临时降权", "短期降权")


class ScopePredicateSingleSourceTests(unittest.TestCase):
    """L1: the frozen scope predicate must exist in exactly one place."""

    def setUp(self) -> None:
        self.store = ms.MemoryStore()
        self.addCleanup(self.store.close)
        self.session_row = self.store.add("用户常驻上海", 1)
        self.other_row = self.store.add("用户住在成都", 2)
        # global 行故意挂在另一个 session_id 上：全局记忆的真实形态是「从某次
        # 会话提升为全局，此后对所有会话可见」。若把它也记在 session 1 名下，
        # 下面那条变异演练（谓词退化成只看 session_id）就分不出 global 行到底
        # 是靠 scope 还是靠 session_id 被看见的——本机实测踩过这个坑。
        self.global_row = self.store.add("用户喜欢蓝色", 99, scope="global")

    def test_predicate_literal_appears_exactly_once_in_source(self):
        """红因（HEAD）：字面量出现 2 次——recall() 与 _visible_facts() 各手抄一遍。"""
        count = _src("src/memory_store.py").count(_SCOPE_PREDICATE)
        self.assertEqual(
            count,
            1,
            f"scope 谓词手抄了 {count} 遍；两份手抄一旦漂移，精排看到的行集就会与冻结语义"
            "不一致，而这类漂移不会让任何按方法各自自洽的测试变红",
        )

    def test_module_exposes_the_predicate_as_a_constant(self):
        """红因（HEAD）：模块无 _SCOPE_SQL 常量，谓词内联在两个方法体里。"""
        self.assertTrue(
            hasattr(ms, "_SCOPE_SQL"),
            "scope 谓词未单点化：memory_store 没有 _SCOPE_SQL 常量",
        )
        self.assertEqual(
            getattr(ms, "_SCOPE_SQL", None),
            _SCOPE_PREDICATE,
            "抽出的常量必须与冻结语义逐字节等价，否则 SQL 行为被静默改写",
        )

    def test_recall_and_visible_facts_see_identical_row_sets(self):
        """一致性护栏：上限窗口内两个方法的可见 fact_id 集合必须相等。

        HEAD 上也绿（两处手抄今日逐字节相同），它的价值在将来：谁只改一处，
        可见集立刻分叉，本测试变红。这是 L1 要求的「一致性测试」。
        """
        recalled = {item.fact_id for item in self.store.recall(1, limit=ms._RECALL_SCAN_LIMIT)}
        visible = {item.fact_id for item in self.store._visible_facts(1)}
        self.assertEqual(recalled, visible)
        self.assertEqual(recalled, {self.session_row, self.global_row})
        self.assertNotIn(self.other_row, visible, "别会话的行不得进入精排窗口")

    def test_scope_constant_is_the_single_carrier_of_isolation(self):
        """变异演练：改这一个常量就能同时改变两个方法的可见集。

        红因（HEAD）：mock.patch.object 找不到 _SCOPE_SQL，AttributeError。
        牙齿证明：patch 后 recall() 与 _visible_facts() **一起**丢掉 global 行，
        说明可见性语义确实由单点承载，而不是两处各自决策。

        变异值选 "session_id = ?" 而不是 "scope = 'global'"：两个方法的 SQL 都用
        (session_id, limit) 两个绑定，谓词里的 `?` 一旦被删掉，sqlite3 会报
        Incorrect number of bindings，演练就变成在测 SQL 参数个数而不是在测
        可见性单点（本机实测踩过这个坑，如实记下）。
        """
        with mock.patch.object(ms, "_SCOPE_SQL", "session_id = ?"):
            recalled = [item.fact_id for item in self.store.recall(1, limit=100)]
            visible = [item.fact_id for item in self.store._visible_facts(1)]
        self.assertEqual(recalled, [self.session_row], "recall 的可见集由该常量单点决定")
        self.assertEqual(visible, [self.session_row], "_visible_facts 必须跟着一起变")
        self.assertNotIn(self.global_row, recalled)
        self.assertNotIn(self.other_row, recalled, "变异也不得放进别会话的行")


class RecallRelevantValidationTests(unittest.TestCase):
    """L2: recall_relevant must reject non-contract limit and tolerate None query."""

    def setUp(self) -> None:
        self.store = ms.MemoryStore()
        self.addCleanup(self.store.close)
        self.facts = ["用户喜欢蓝色", "用户常驻上海", "用户养了一只乌龟"]
        for text in self.facts:
            self.store.add(text, 1)

    def test_negative_limit_is_rejected_instead_of_slicing_the_window(self):
        """红因（HEAD）：limit=-1 不报错，3 行可见时返回 2 行（order[:-1]）。

        危害不是「多返回一条」：这 2 行会被 format_memory_prompt 整段拼进
        system prompt，而调用方以为自己只要了 -1 条。
        """
        with self.assertRaises(ValueError):
            self.store.recall_relevant(1, "用户喜欢什么颜色", limit=-1)

    def test_negative_limit_does_not_silently_return_window_minus_one(self):
        """同一条缺陷的行为面复现：断言「返回 n-1 行」这个具体症状不再发生。"""
        try:
            got = self.store.recall_relevant(1, "用户喜欢什么颜色", limit=-1)
        except ValueError:
            return
        self.fail(
            f"limit=-1 未报错且返回 {len(got)} 行（{[item.fact for item in got]}）："
            "非法值被当成切片下标静默消化"
        )

    def test_bool_limit_is_rejected_rather_than_read_as_one(self):
        """红因（HEAD）：bool 是 int 子类，limit=True 被静默当成 1。"""
        with self.assertRaises(ValueError):
            self.store.recall_relevant(1, "用户喜欢什么颜色", limit=True)

    def test_float_limit_raises_valueerror_not_typeerror(self):
        """红因（HEAD）：limit=1.5 抛 TypeError（来自切片），不是契约式 ValueError。"""
        with self.assertRaises(ValueError):
            self.store.recall_relevant(1, "用户喜欢什么颜色", limit=1.5)

    def test_string_limit_raises_valueerror_not_typeerror(self):
        """红因（HEAD）：limit='2' 抛 TypeError（来自切片），不是契约式 ValueError。"""
        with self.assertRaises(ValueError):
            self.store.recall_relevant(1, "用户喜欢什么颜色", limit="2")

    def test_zero_limit_returns_empty_list(self):
        """护栏：limit=0 是合法值，返回空（HEAD 与修复后同为绿）。"""
        self.assertEqual(self.store.recall_relevant(1, "用户喜欢什么颜色", limit=0), [])

    def test_none_query_falls_back_to_recency_instead_of_crashing(self):
        """红因（HEAD）：AttributeError: 'NoneType' object has no attribute 'strip'。

        这条在 harness 调用路径上可达：memory_candidate 缺失时上游可能传 None，
        而留出集 v2 里就有「query 是纯标点」这类退化输入，同属无检索意图形态。
        """
        got = self.store.recall_relevant(1, None, limit=2)
        self.assertEqual([item.fact for item in got], list(reversed(self.facts))[:2])

    def test_none_query_and_empty_query_agree(self):
        """None 与空串同义：都读作「无检索意图」，走同一套新近回退。"""
        by_none = [item.fact_id for item in self.store.recall_relevant(1, None, limit=3)]
        by_empty = [item.fact_id for item in self.store.recall_relevant(1, "", limit=3)]
        self.assertEqual(by_none, by_empty)


class NoneCoercionTests(unittest.TestCase):
    """L3: an explicit None must not become the scorable literal "None"."""

    def test_none_query_cannot_fabricate_a_hit(self):
        """红因（HEAD）：precision/recall 都是 1.0——脏数据骗到了命中。

        构造：query=None，stored[1] 含字面量 "none"，relevant 指向 stored[1]。
        HEAD 上 str(None)='None'，normalize 后为 'none'，与 stored[1] 产生虚假
        字面相似度并把它排到 top-1，于是命中；修复后 query 降级为空串，全候选
        同分、由「同分保留输入序」给出 stored[0]，如实不命中。
        """
        dirty = [{
            "query": None,
            "stored": ["用户喜欢蓝色", "用户住在none区"],
            "relevant": ["用户住在none区"],
        }]
        self.assertEqual(mr.score_retrieval(dirty), {"precision": 0.0, "recall": 0.0})

    def test_none_in_stored_does_not_outrank_a_real_candidate(self):
        """红因（HEAD）：stored 里的 None 变成 "None" 后抢走 top-1，指标 0.0。

        同一处 str() 转换的 stored 侧：query='none' 时 HEAD 把 None 行折成字面
        量 "None" 并排到 top-1，真正对题的事实被挤掉；修复后 None 降级为空串、
        不参与打分，同分保留输入序让对题事实回到 top-1。
        """
        dirty = [{
            "query": "none",
            "stored": ["用户喜欢蓝色", None],
            "relevant": ["用户喜欢蓝色"],
        }]
        self.assertEqual(mr.score_retrieval(dirty), {"precision": 1.0, "recall": 1.0})

    def test_as_text_helper_maps_none_to_empty_string(self):
        """红因（HEAD）：memory_ranker 无 _as_text，转换散落为裸 str()。"""
        as_text = getattr(mr, "_as_text", None)
        self.assertIsNotNone(as_text, "缺少把评测集字段安全转成 str 的单点 helper")
        self.assertEqual(as_text(None), "")
        self.assertEqual(as_text("用户喜欢蓝色"), "用户喜欢蓝色")

    def test_as_text_does_not_swallow_legitimate_falsy_values(self):
        """护栏：0 / False / 空串是合法资料，只许 None 降级，不许一律 falsy 归零。"""
        as_text = getattr(mr, "_as_text", None)
        if as_text is None:
            self.skipTest("_as_text 尚未落地")
        self.assertEqual(as_text(0), "0")
        self.assertEqual(as_text(""), "")


class NormalizeFoldingTests(unittest.TestCase):
    """L4: normalize must casefold (not lower) and strip General Punctuation."""

    def test_casefold_expands_sharp_s(self):
        """红因（HEAD）：normalize('Straße')='straße'，与 'strasse' 不等。"""
        self.assertEqual(mr.normalize("Straße"), "strasse")

    def test_equivalent_latin_forms_score_one(self):
        """红因（HEAD）：bigram_similarity('Straße','STRASSE')=0.5477，不是 1.0。"""
        self.assertEqual(mr.bigram_similarity("Straße", "STRASSE"), 1.0)

    def test_lowercase_latin_still_folds(self):
        """护栏：普通大小写折叠两侧都成立，修复不许把已有行为改掉。"""
        self.assertEqual(mr.normalize("PYTHON"), "python")
        self.assertEqual(mr.bigram_similarity("Python", "PYTHON"), 1.0)

    def test_general_punctuation_range_is_stripped(self):
        """红因（HEAD）：U+2000-206F 与 U+00B7 全部原样保留。

        逐个字符断言而不是只测一个：破折号、弯引号、零宽空格与间隔号在中文排版
        里各自独立出现，漏掉任何一个都会让 bigram 多重集带进噪声字符。
        """
        for codepoint in (0x2014, 0x2018, 0x2019, 0x201C, 0x201D, 0x200B, 0x200C, 0x200D, 0x00B7):
            char = chr(codepoint)
            self.assertEqual(
                mr.normalize(char),
                "",
                f"U+{codepoint:04X} 未被剥离，会直接进 bigram 多重集",
            )

    def test_zero_width_space_does_not_kill_similarity(self):
        """红因（HEAD）：bigram_similarity('a\\u200bb','ab')=0.0。

        零宽空格肉眼看不出差异，却能让字面相似度彻底归零——这是 L4 里最隐蔽
        的一路，也是补 U+2000-206F 的主要动因。
        """
        self.assertEqual(mr.bigram_similarity("a\u200bb", "ab"), 1.0)

    def test_middle_dot_does_not_split_a_name(self):
        """红因（HEAD）：normalize('洛·天依')='洛·天依'，相似度只有 0.4082。"""
        self.assertEqual(mr.normalize("洛·天依"), "洛天依")
        self.assertEqual(mr.bigram_similarity("洛·天依", "洛天依"), 1.0)

    def test_dashes_and_quotes_do_not_survive(self):
        """红因（HEAD）：normalize('——')='——'、normalize('“引号”')='“引号”'。"""
        self.assertEqual(mr.normalize("——"), "")
        self.assertEqual(mr.normalize("“引号”"), "引号")

    def test_superscript_is_folded_by_nfkc_not_stripped_as_punctuation(self):
        """护栏：NFKC 先把上标折成普通数字，补区间不许把它当标点剥掉。

        U+2070-209F 落在新补的 U+2000-206F **之外**，这条断言把这个边界钉住。
        """
        self.assertEqual(mr.normalize("⁷"), "7")
        self.assertEqual(mr.normalize("x⁷"), "x7")

    def test_cjk_and_digits_survive(self):
        """护栏：归一化只删标点与空白，内容字符一个不许少。"""
        self.assertEqual(mr.normalize("用户常驻上海2024"), "用户常驻上海2024")

    def test_fullwidth_latin_and_space_fold_for_the_v2_d5_shape(self):
        """护栏：v2 的 D5 形态（全角拉丁+全角空格+全角括号）在 HEAD 上已能折叠。

        如实记录：这条**两侧都绿**。它存在的意义是把「L4 对 D5 是决定性的」这个
        预期钉在实测上——D5 的全角由 NFKC 承担、大小写由 lower 已足够，L4 的
        casefold 与剥离集增量对 D5 并不决定性；L4 的真实价值在 ß/连字与零宽
        字符、破折号、弯引号、间隔号这些 v2 未覆盖的形态上。
        """
        folded = mr.normalize("用户的手机是ｉＰｈｏｎｅ　１５　Ｐｒｏ（深空黑）")
        self.assertEqual(folded, "用户的手机是iphone15pro深空黑")


class LexiconReadOnlyTests(unittest.TestCase):
    """L6: CONCEPT_LEXICON must be read-only without breaking patch-based drills."""

    def test_lexicon_is_a_read_only_mapping(self):
        """红因（HEAD）：type 是 dict，isinstance(..., MappingProxyType) 为 False。"""
        self.assertIsInstance(mr.CONCEPT_LEXICON, MappingProxyType)

    def test_item_assignment_raises_typeerror(self):
        """红因（HEAD）：item 赋值静默成功，打分语义被改写而无任何测试变红。"""
        replacement = mr.ConceptClass(name="颜色", head=("颜色",), member=("蓝",))
        with self.assertRaises(TypeError):
            mr.CONCEPT_LEXICON["颜色"] = replacement

    def test_mutating_methods_are_absent(self):
        """红因（HEAD）：.pop / .setdefault / .update 都可用。"""
        for name in ("pop", "setdefault", "update", "clear"):
            self.assertFalse(
                hasattr(mr.CONCEPT_LEXICON, name),
                f"只读映射不该暴露 {name}()",
            )

    def test_wholesale_replacement_still_works(self):
        """兼容性实测：变异演练靠整体替换模块属性，L6 不许把这条路堵死。

        tests/test_ranker_mutations.py 用 mock.patch.object 换掉整个词典，
        MappingProxyType 只拦 in-place 写、不拦属性重绑定，所以两者兼容；
        这条断言把兼容性钉成可执行的事实，而不是注释里的口头保证。
        """
        original = mr.CONCEPT_LEXICON
        probe = {"探针": mr.ConceptClass(name="探针", head=("探针",), member=("值",))}
        with mock.patch.object(mr, "CONCEPT_LEXICON", probe):
            self.assertEqual(list(mr.CONCEPT_LEXICON), ["探针"])
            self.assertGreater(mr.concept_bridge("探针", "探针的值"), 0.0)
        self.assertIs(mr.CONCEPT_LEXICON, original)

    def test_read_only_wrapper_preserves_lookup_semantics(self):
        """护栏：包一层不许改变读侧行为，类的数量与迭代序都保持原样。"""
        self.assertEqual(len(mr.CONCEPT_LEXICON), 8)
        self.assertEqual(
            list(mr.CONCEPT_LEXICON),
            ["颜色", "城市", "称呼", "生日", "宠物", "过敏", "职业", "爱好"],
        )


class RankDocstringAccuracyTests(unittest.TestCase):
    """L7: rank()'s docstring must not misdescribe its callers."""

    def test_docstring_does_not_claim_both_callers_take_top_one(self):
        """红因（HEAD）：docstring 第 469 行写 'both take top-1'，与实现不符。"""
        doc = inspect.getdoc(mr.rank) or ""
        self.assertNotIn("both take top-1", doc)

    def test_docstring_states_recall_relevant_is_limit_parameterised(self):
        """红因（HEAD）：docstring 未提 recall_relevant 的 limit 是 top-k。"""
        doc = inspect.getdoc(mr.rank) or ""
        self.assertIn("limit", doc)
        self.assertIn("recall_relevant", doc)

    def test_recall_relevant_really_is_top_k(self):
        """行为佐证：limit=2 确实返回 2 条不同事实，所以 top-1 的描述是错的。"""
        store = ms.MemoryStore()
        self.addCleanup(store.close)
        store.add("用户喜欢蓝色", 1)
        store.add("用户常驻上海", 1)
        store.add("用户养了一只乌龟", 1)
        got = store.recall_relevant(1, "用户喜欢什么颜色", limit=2)
        self.assertEqual(len(got), 2)
        self.assertEqual(len({item.fact_id for item in got}), 2)


class OptionalWordingTests(unittest.TestCase):
    """L8: docstrings must say `| None`, matching the zero-typing.Optional repo."""

    def test_no_optional_wording_in_memory_sources(self):
        """红因（HEAD）：memory_store.py 第 216 行用「Optional」指代 `| None`。

        全仓零 typing.Optional（实测），所以这个词在本仓没有定义来源，读者会
        去找一个不存在的 import。commit message 侧的同名措辞本轮不动（见报告
        延后清单）：阶段一已 reword 过一次历史，为措辞再动一次历史不划算。
        """
        for rel in ("src/memory_store.py", "src/memory_ranker.py"):
            # 用 assertTrue 而不是 assertNotIn：后者失败时会把整份源码打进输出。
            self.assertTrue(
                "Optional" not in _src(rel),
                f"{rel} 仍在用「Optional」措辞指代 `| None`",
            )

    def test_repo_never_imports_typing_optional(self):
        """护栏：措辞改动的前提是「全仓零 typing.Optional」，这条把前提钉住。"""
        for rel in ("src/memory_store.py", "src/memory_ranker.py"):
            self.assertTrue("typing" not in _src(rel), f"{rel} 引入了 typing")

    def test_store_score_retrieval_docstring_uses_pipe_none(self):
        """红因（HEAD）：转发函数的契约段写 Optional，没有 `| None`。"""
        doc = inspect.getdoc(ms.score_retrieval) or ""
        self.assertIn("| None", doc)


class DocstringLanguageLayeringTests(unittest.TestCase):
    """L11: the English contract paragraph must not carry Chinese clauses."""

    @staticmethod
    def _contract_violations(module) -> list[str]:
        violations: list[str] = []
        for name, obj in sorted(vars(module).items()):
            if not (inspect.isfunction(obj) or inspect.isclass(obj)):
                continue
            if getattr(obj, "__module__", None) != module.__name__:
                continue
            targets = [(name, obj)]
            if inspect.isclass(obj):
                targets += [
                    (f"{name}.{attr}", value)
                    for attr, value in sorted(vars(obj).items())
                    if inspect.isfunction(value)
                ]
            for qualname, target in targets:
                doc = inspect.getdoc(target)
                if not doc:
                    continue
                for paragraph in doc.split("\n\n"):
                    if "Contract:" in paragraph and _CJK_IDEOGRAPH.search(paragraph):
                        violations.append(qualname)
        return violations

    def test_contract_paragraphs_are_pure_english(self):
        """红因（HEAD）：5 处在契约段里夹中文分句。

        实测清单：_is_stable_attribute_query（爱好/职业/城市、行为式提问…）、
        _query_polarity（忌口/讨厌/不能吃/过敏）、bigram_similarity（哈哈）、
        concept_bridge（用户/喜欢/爱好）、transient_penalty（最近/今天/刚…）。
        只读英文段就该拿到完整接口口径，中文段承担设计理由，两者不互相污染。
        """
        violations = self._contract_violations(mr) + self._contract_violations(ms)
        self.assertEqual(violations, [], f"契约段夹中文：{violations}")

    def test_both_modules_state_the_convention(self):
        """红因（HEAD）：两个模块的 docstring 都没写这条规则。

        规则要写在代码里，任务 C/E 沿用时才有单一出处，不必翻本轮报告。
        """
        for module in (mr, ms):
            doc = inspect.getdoc(module) or ""
            self.assertIn("Docstring 约定", doc, f"{module.__name__} 模块 docstring 未声明该约定")

    def test_design_rationale_still_present_in_chinese(self):
        """护栏：分层不等于删理由，中文设计理由段必须还在。"""
        doc = inspect.getdoc(mr.concept_bridge) or ""
        self.assertIn("设计理由", doc)


class TransientTerminologyTests(unittest.TestCase):
    """M19: the tense-demotion layer has exactly one Chinese name."""

    def test_unified_term_is_used(self):
        """红因（HEAD）：全 src/ 零处出现「时态降权」。

        TRANSIENT_MARKERS / transient_penalty 的中文对应词缺失，文档与代码就对
        不上同一样东西；统一到与常量同词根的「时态降权」。
        """
        combined = _src("src/memory_ranker.py") + _src("src/memory_store.py")
        self.assertTrue(
            _TRANSIENT_TERM in combined,
            f"src/ 里零处出现「{_TRANSIENT_TERM}」，该层没有统一的中文名",
        )

    def test_no_alias_terms_survive(self):
        """别名不得作为对该层的**称呼**出现（实测 HEAD 上本就没有，这条防回填）。

        判据为什么不是「全文零出现」：术语约定那一句要声明禁令，就必须把被禁
        的别名写出来（「不混用「短期状态降权」「时态惩罚」等别名」），那是元语言
        引用而不是使用。本机实测：粗暴的全文搜索会把这句禁令自己判成违规。
        所以判据收窄成「别名出现的每一行都必须同时是禁令句」：行里必须出现
        「别名」或「不混用」，否则就是真的拿别名在称呼这一层。
        """
        for rel in ("src/memory_ranker.py", "src/memory_store.py"):
            for lineno, line in enumerate(_src(rel).splitlines(), start=1):
                for alias in _TRANSIENT_ALIASES:
                    if alias not in line:
                        continue
                    self.assertTrue(
                        "别名" in line or "不混用" in line,
                        f"{rel}:{lineno} 拿别名「{alias}」称呼时态降权层，"
                        f"应统一为「{_TRANSIENT_TERM}」",
                    )

    def test_term_appears_next_to_the_layer_it_names(self):
        """术语要出现在它命名的那一层旁边，而不是只在模块总览里挂个名。"""
        doc = inspect.getdoc(mr.transient_penalty) or ""
        self.assertIn(_TRANSIENT_TERM, doc)


if __name__ == "__main__":
    unittest.main(verbosity=2)
