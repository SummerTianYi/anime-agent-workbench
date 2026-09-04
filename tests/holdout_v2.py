"""Blind-authored retrieval holdout set (v2) for Task B memory scoring.

WHAT THIS IS
    A pure-data corpus of ``{"query", "stored", "relevant"}`` triples used to
    judge whether ``score_retrieval()`` generalises to inputs it was never
    tuned against. It mirrors the shape of the frozen gate corpus in
    ``acceptance/gates/g1_memory.py`` (``GOLDEN``) so it can be fed to the same
    scorer without adapters. ``relevant`` is always a subset of ``stored``.

WHY IT EXISTS
    The previous holdout set turned out to be non-diagnostic: every answer
    keyword it relied on had also been baked into the implementation's concept
    lexicon, and every one of its answers sat at ``stored[0]``. A scorer that
    merely returned candidates verbatim, or one that only matched those exact
    keywords, could score a perfect 1.0 without any real retrieval ability.
    This v2 corpus is built from the *domain* (what a companion character would
    remember about a user and how a user would ask for it), not from the
    implementation, and deliberately spreads answers across first / middle /
    last positions, varies ``stored`` length, and mixes in polarity, tense,
    full-width Latin, high-literal-overlap distractors, zero-overlap semantic
    bridges, colloquial restatements and degenerate inputs.

WHY IT MUST STAY ISOLATED FROM THE IMPLEMENTATION
    Its whole evidentiary value comes from the author never having read the
    scorer. The author of this file did NOT open ``src/memory_ranker.py``,
    ``tests/test_memory_retrieval.py``, ``evidence/task_b_retrieval_analysis.md``
    or ``evidence/task_b_self_sabotage.md`` while writing it. Files actually
    consulted: ``tasks/B-memory-system/SPEC.md``, ``README.md``,
    ``INTEGRATION.md``, ``acceptance/gates/g1_memory.py`` (data shape only),
    and the ``BASE_SYSTEM_PROMPT`` block of ``vendor/agent_core/harness.py``
    (to learn what ``memory_candidate`` facts look like). This module imports
    nothing from the implementation and contains no assertions and no scoring
    logic; wiring and grading are someone else's job.

PROVENANCE
    Authored 2026-09-03 by an independent writer, derived from SPEC + a domain
    analysis of the retrieval input space (stable attributes vs. short-term
    states, affirmation vs. aversion, orthographic normalisation, literal-overlap
    traps, semantic bridging, colloquial noise, co-reference, degenerate shapes).
    It was NOT reverse-engineered from any scorer output.

HARD CONSTRAINT
    Once finalised this corpus is an acceptance baseline. No pair may be edited,
    reordered, softened or removed in order to make an implementation pass. If a
    scorer falls short here, the scorer is what gets fixed -- never this file.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# 编写口径（中文）
#
# 1. 领域来源：全部素材取自"洛天依桌面陪伴 Agent 会从日常闲聊里记住的用户事实"
#    与"用户会怎么把这些事实问回来"。事实面向简体中文、中文全角标点，与
#    BASE_SYSTEM_PROMPT 的文风一致；长度以 5~60 字为主，个别长句用于制造长度悬殊。
#
# 2. 覆盖维度（每对下方行注释标注所属维度，逐维度 ≥2 对，退化/单候选维度除外）：
#      D1 稳定属性 vs 短期状态（正向）：查询问长期属性，带"最近/这几天/昨天/
#         正在/刚开始"的短期事实是干扰项。
#      D2 稳定属性 vs 短期状态（反向）：查询明确问近期状态，带短期标记的事实
#         才是答案，稳定属性反而是干扰项——专治"见到最近就扣分"的实现。
#      D3 肯定 vs 否定/厌恶（正向）：查询问喜欢/爱好，肯定陈述是答案。
#      D4 肯定 vs 否定/厌恶（反向）：查询问忌口/不喜欢/忌讳，否定陈述是答案
#         ——专治不辨极性、把语义搞反的实现。
#      D5 全角/半角与大写拉丁字母混排：事实侧含全角拉丁、全角数字、全角括号/
#         叹号/空格、英文大小写差异，查询侧用不同写法指同一事物，考察归一化。
#      D6 高字面重叠干扰项：干扰项与查询共享大量字符但语义不对，打击纯字面相似度。
#      D7 零字面重叠语义桥接：查询与答案不共享字符，需要概念知识才能连上。
#      D8 口语转述与冗余表达：答案是啰嗦、带语气词的长句，查询是简短问句。
#      D9 同指不同表述（多 relevant）：同一事实的不同说法都算正确答案，用于
#         区分查准率与查全率。
#      D10 退化输入：空 stored / 纯标点 query，仅提供输入形状，期望行为由实现方定义。
#      D11 单一候选：stored 只有 1 条，本身无判别力（任何打分都命中），仅用于
#         覆盖 stored 长度=1 的输入形状，全库只保留 1 对。
#
# 3. 结构约束：正确答案在 stored 中的首次出现下标已刻意分散到首位/中间/末位；
#    stored 长度覆盖 0/1/2/3/4；含 3 对多 relevant（≥2 个正确答案）。
#
# 4. 硬约束：本集一经定稿即为验收基准，不许为了让任何实现通过而修改、重排、
#    弱化或删除其中任意一对。实现不达标，修的是实现，不是这份语料。
#
# 5. 隐私与安全：不含真实可识别个人信息、密钥样式串（sk- / api_key= / Bearer）、
#    以及用户主目录前缀或 Windows 盘符前缀这类绝对路径。人名、地名、账号均为
#    虚构常识性素材。
#    （N2：本条原先把这两类前缀的原样字面量写在这里当示例。本仓要 push 到公开
#    仓库，而仓库规则禁止 src/ 与 tests/ 下出现它们，注释与字符串也不例外，故
#    改为只描述约束。语料数据一个字节未动：规范化序列化的 sha256 前后相同，
#    该值由 tests/test_holdout_v2.py 的 HOLDOUT_V2_SHA256 钉住并逐次校验。）
# ---------------------------------------------------------------------------

HOLDOUT_V2: list[dict[str, list[str] | str]] = [
    # ---- D1 稳定属性 vs 短期状态（正向）；relevant 在中间(idx=1)；len=3 ----
    {
        "query": "用户住在哪个城市",
        "stored": ["用户这几天在成都出差", "用户长期定居在苏州", "用户昨天去了趟超市"],
        "relevant": ["用户长期定居在苏州"],
    },
    # ---- D1 稳定属性 vs 短期状态（正向）；relevant 在首位(idx=0)；len=3 ----
    {
        "query": "用户的职业是什么",
        "stored": ["用户是小学音乐老师", "用户最近在学吉他", "用户刚开始做短视频剪辑的兼职"],
        "relevant": ["用户是小学音乐老师"],
    },
    # ---- D2 稳定属性 vs 短期状态（反向）；relevant 在中间(idx=1)；len=3 ----
    # 查询明确问近期状态，"最近"标记的事实才是答案，稳定职业/居住地是干扰项。
    {
        "query": "用户最近在忙什么",
        "stored": ["用户是产品经理", "用户最近在准备考研", "用户住在广州"],
        "relevant": ["用户最近在准备考研"],
    },
    # ---- D2 稳定属性 vs 短期状态（反向）；relevant 在末位(idx=2)；len=3 ----
    {
        "query": "用户这周心情怎么样",
        "stored": ["用户性格比较内向", "用户喜欢听轻音乐放松", "用户这几天因为项目上线压力很大，情绪有点低落"],
        "relevant": ["用户这几天因为项目上线压力很大，情绪有点低落"],
    },
    # ---- D1 稳定属性 vs 短期状态（正向）；relevant 在中间(idx=2)；len=4 ----
    {
        "query": "用户的作息习惯是怎样的",
        "stored": ["用户是夜班保安", "用户昨天熬到凌晨三点", "用户习惯晚上十一点前睡觉", "用户这周在倒班"],
        "relevant": ["用户习惯晚上十一点前睡觉"],
    },
    # ---- D1 稳定属性 vs 短期状态（正向）；relevant 在末位(idx=1)；len=2 ----
    {
        "query": "用户怕什么",
        "stored": ["用户这几天在看恐怖片", "用户从小就怕打雷"],
        "relevant": ["用户从小就怕打雷"],
    },
    # ---- D3 肯定 vs 否定（正向）；relevant 在首位(idx=0)；len=3 ----
    {
        "query": "用户平时有什么爱好",
        "stored": ["用户喜欢在周末去江边跑步", "用户讨厌吵闹的夜店", "用户不吃香菜"],
        "relevant": ["用户喜欢在周末去江边跑步"],
    },
    # ---- D3 肯定 vs 否定（正向）；relevant 在末位(idx=1)；len=2 ----
    {
        "query": "用户喜欢喝什么饮品",
        "stored": ["用户不喝酒", "用户每天早上要喝一杯手冲咖啡"],
        "relevant": ["用户每天早上要喝一杯手冲咖啡"],
    },
    # ---- D4 肯定 vs 否定（反向，忌口）；relevant 在中间(idx=1)；len=3 ----
    # 查询问"忌讳"，否定陈述（过敏/不能吃）才是答案，"很喜欢/爱吃"是干扰项。
    {
        "query": "用户饮食上有什么忌讳",
        "stored": ["用户很喜欢吃麻辣火锅", "用户对海鲜过敏，不能吃虾蟹", "用户爱吃甜食"],
        "relevant": ["用户对海鲜过敏，不能吃虾蟹"],
    },
    # ---- D4 肯定 vs 否定（反向，不喜欢）；relevant 在首位(idx=0)；len=3 ----
    {
        "query": "用户不喜欢什么样的地方",
        "stored": ["用户不喜欢人多嘈杂的商场", "用户常去市图书馆看书", "用户喜欢安静的咖啡馆"],
        "relevant": ["用户不喜欢人多嘈杂的商场"],
    },
    # ---- D5 全角拉丁+全角括号+全角空格+小写ｉ；relevant 在中间(idx=1)；len=3 ----
    # 查询用中文"型号"，事实用全角 ｉＰｈｏｎｅ　１５　Ｐｒｏ（含全角空格与全角数字）。
    {
        "query": "用户的手机是什么型号",
        "stored": ["用户在西安上学", "用户的手机是ｉＰｈｏｎｅ　１５　Ｐｒｏ（深空黑）", "用户不喜欢熬夜"],
        "relevant": ["用户的手机是ｉＰｈｏｎｅ　１５　Ｐｒｏ（深空黑）"],
    },
    # ---- D5 英文大小写差异+全角拉丁；relevant 在中间(idx=1)；len=3 ----
    # 查询用小写 python，事实用大写 PYTHON 与全角 Ｐｙｔｈｏｎ，考察大小写/全角归一化。
    {
        "query": "用户在学 python 吗",
        "stored": ["用户是会计", "用户在自学 PYTHON，还买了本《Ｐｙｔｈｏｎ编程从入门到实践》", "用户周末喜欢爬山"],
        "relevant": ["用户在自学 PYTHON，还买了本《Ｐｙｔｈｏｎ编程从入门到实践》"],
    },
    # ---- D5 全角数字+全角叹号；relevant 在首位(idx=0)；len=3 ----
    {
        "query": "用户的生日是哪天",
        "stored": ["用户的生日是３月８号！", "用户在南京工作", "用户不喜欢吃胡萝卜"],
        "relevant": ["用户的生日是３月８号！"],
    },
    # ---- D5 全角拉丁+零字面重叠（查询"社交软件"↔"ＷｅＣｈａｔ"）；idx=0；len=2 ----
    {
        "query": "用户常用什么社交软件",
        "stored": ["用户常用 ＷｅＣｈａｔ 和朋友聊天", "用户养了一只猫"],
        "relevant": ["用户常用 ＷｅＣｈａｔ 和朋友聊天"],
    },
    # ---- D6 高字面重叠（宠物）；relevant 在中间(idx=1)；len=3 ----
    # 干扰项"用户养过一盆多肉植物"共享"用户养"，但语义是植物不是宠物。
    {
        "query": "用户养了什么宠物",
        "stored": ["用户养过一盆多肉植物，养了三年", "用户养了一只叫团子的橘猫", "用户喜欢在阳台上种花"],
        "relevant": ["用户养了一只叫团子的橘猫"],
    },
    # ---- D6 高字面重叠（城市工作）；relevant 在末位(idx=2)；len=3 ----
    # 干扰项共享"城市"但语义不是"在哪个城市工作"。
    {
        "query": "用户在哪个城市工作",
        "stored": ["用户喜欢在城市的公园里散步", "用户下班常去城市广场看电影", "用户在武汉的一家设计院上班"],
        "relevant": ["用户在武汉的一家设计院上班"],
    },
    # ---- D6 高字面重叠（过敏）；relevant 在中间(idx=1)；len=3 ----
    # 干扰项共享"花"但语义是偏好/审美，不是过敏。
    {
        "query": "用户对什么过敏",
        "stored": ["用户不喜欢花香味太浓的香水", "用户对花粉和尘螨过敏", "用户觉得春天的花很好看"],
        "relevant": ["用户对花粉和尘螨过敏"],
    },
    # ---- D6 高字面重叠+D3；relevant 在中间(idx=1)；len=4 ----
    # 干扰项"运动场边看别人踢球""买了新的运动鞋""讨厌运动后的疲惫感"共享"运动"。
    {
        "query": "用户喜欢什么运动",
        "stored": ["用户喜欢在运动场边看别人踢球", "用户每周三去体育馆打两个小时羽毛球", "用户买了新的运动鞋", "用户讨厌运动后的疲惫感"],
        "relevant": ["用户每周三去体育馆打两个小时羽毛球"],
    },
    # ---- D7 零字面重叠语义桥接（职业）；relevant 在首位(idx=0)；len=3 ----
    # "职业"与"护士/三甲医院"无共享字符，需概念桥接。
    {
        "query": "用户的职业是什么",
        "stored": ["用户在三甲医院的儿科当护士", "用户喜欢在阳台种多肉", "用户家住在长沙"],
        "relevant": ["用户在三甲医院的儿科当护士"],
    },
    # ---- D7 零字面重叠语义桥接（年龄）；relevant 在末位(idx=2)；len=3 ----
    # "多大"与"本命年/属龙"无共享字符，需从生肖/本命年推断年龄信息。
    {
        "query": "用户多大了",
        "stored": ["用户是程序员", "用户喜欢喝美式咖啡", "用户明年就本命年了，属龙"],
        "relevant": ["用户明年就本命年了，属龙"],
    },
    # ---- D7 零字面重叠语义桥接（身体状况）；relevant 在末位(idx=2)；len=3 ----
    {
        "query": "用户的身体状况怎么样",
        "stored": ["用户喜欢看展览", "用户在学油画", "用户有轻度哮喘，换季容易犯"],
        "relevant": ["用户有轻度哮喘，换季容易犯"],
    },
    # ---- D7 零字面重叠语义桥接（爱好）；relevant 在首位(idx=0)；len=3 ----
    # "爱好"与"背着相机去郊外拍鸟"无共享字符，需从行为推断摄影爱好。
    {
        "query": "用户有什么爱好",
        "stored": ["用户周末常背着相机去郊外拍鸟", "用户在银行上班", "用户不吃辣"],
        "relevant": ["用户周末常背着相机去郊外拍鸟"],
    },
    # ---- D7 零字面重叠语义桥接（家乡）；relevant 在中间(idx=1)；len=4 ----
    # "家乡"↔"从小在黄土高原的窑洞里长大"；"现在住在深圳"是当前居住地的干扰项。
    {
        "query": "用户的家乡在哪里",
        "stored": ["用户是程序员", "用户从小在黄土高原的窑洞里长大", "用户喜欢听摇滚", "用户现在住在深圳"],
        "relevant": ["用户从小在黄土高原的窑洞里长大"],
    },
    # ---- D8 口语转述与冗余；relevant 在首位(idx=0)；len=3 ----
    # 答案是带语气词的啰嗦长句，查询是简短问句，制造长度悬殊与噪声词干扰。
    {
        "query": "用户喜欢吃什么",
        "stored": ["嗯……用户说他其实还挺喜欢吃麻辣火锅的，就是胃不太行，不敢多吃", "用户住在重庆", "用户不喜欢香菜"],
        "relevant": ["嗯……用户说他其实还挺喜欢吃麻辣火锅的，就是胃不太行，不敢多吃"],
    },
    # ---- D8 口语转述与冗余；relevant 在中间(idx=1)；len=3 ----
    {
        "query": "用户的宠物叫什么",
        "stored": ["用户是老师", "用户之前提过一嘴，说他家那只橘猫特别能吃，叫团子", "用户喜欢跑步"],
        "relevant": ["用户之前提过一嘴，说他家那只橘猫特别能吃，叫团子"],
    },
    # ---- D8 口语转述+D7 桥接；relevant 在末位(idx=3)；len=4 ----
    # "工作"↔"当大厨"，且答案是口语长句，位置在最末。
    {
        "query": "用户的工作是什么",
        "stored": ["用户是老师", "用户喜欢看电影", "用户住在青岛", "用户之前唠过，说他在那家海鲜酒楼当大厨好几年了"],
        "relevant": ["用户之前唠过，说他在那家海鲜酒楼当大厨好几年了"],
    },
    # ---- D9 同指不同表述（多 relevant）；答案在首位与末位(idx=0,2)；len=3 ----
    # 两条不同说法都指"称呼偏好"，都算 relevant，用于区分查准率与查全率。
    {
        "query": "用户希望怎么被称呼",
        "stored": ["用户希望被叫做阿豪", "用户是健身教练", "用户说他朋友都管他叫豪哥"],
        "relevant": ["用户希望被叫做阿豪", "用户说他朋友都管他叫豪哥"],
    },
    # ---- D9 同指不同表述（多 relevant，音乐领域）；答案在首位与末位(idx=0,2)；len=3 ----
    {
        "query": "用户喜欢听什么类型的歌",
        "stored": ["用户偏爱民谣和独立音乐", "用户住在厦门", "用户说他特别喜欢那种安静的、能弹吉他的民谣"],
        "relevant": ["用户偏爱民谣和独立音乐", "用户说他特别喜欢那种安静的、能弹吉他的民谣"],
    },
    # ---- D9 同指不同表述（多 relevant）；答案在首位与中间(idx=0,1)；len=3 ----
    {
        "query": "用户住在哪个区",
        "stored": ["用户家住在西湖区", "用户户口落在杭州西湖区", "用户喜欢周末逛超市"],
        "relevant": ["用户家住在西湖区", "用户户口落在杭州西湖区"],
    },
    # ---- D11 单一候选（无判别力，全库仅此 1 对）；idx=0；len=1 ----
    # stored 只有 1 条，任何打分都会命中，仅用于覆盖 stored 长度=1 的输入形状。
    {
        "query": "用户喜欢什么颜色",
        "stored": ["用户最喜欢的颜色是藏青色"],
        "relevant": ["用户最喜欢的颜色是藏青色"],
    },
    # ---- D10 退化输入：stored 为空列表；len=0 ----
    # 只提供输入形状，不规定期望输出；空 stored 下 relevant 只能为空子集。
    {
        "query": "用户喜欢什么颜色",
        "stored": [],
        "relevant": [],
    },
    # ---- D10 退化输入：query 为纯标点；len=2 ----
    # 无明确检索意图，relevant 留空；是否返回任何事实由实现方定义。
    {
        "query": "……",
        "stored": ["用户养了一只鹦鹉", "用户在广州上班"],
        "relevant": [],
    },
]
