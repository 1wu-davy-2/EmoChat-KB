# -*- coding: utf-8 -*-
"""校验构建产物：结构、frontmatter、索引、链接、检索、画像与单条回复快速通道。"""
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent
ROOT = SKILL_DIR.parent
DIST = SKILL_DIR / "dist"
PRIVATE = DIST / "emochat-private"
PUBLIC = DIST / "emochat-public"
TMP = SKILL_DIR / ".check-tmp"

CARD_ID = re.compile(
    r"\b(?:raw|method|script|persona|astro|scene|risk|tactic|book|research|intimacy|user)-\d{3}\b"
)
MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
PLACEHOLDER = re.compile(r"\{\{[A-Z_]+\}\}")
HEADING_RE = re.compile(r"^【([^】]*)】")
UNSAFE_HEADINGS = ("坏话术", "操控话术", "PUA", "反例", "样本", "示范", "不要照说", "识别示例")

REQUIRED_SCRIPTS = [
    "scripts/emochat_core.py",
    "scripts/emochat_search.py",
    "scripts/emochat_analyze.py",
]

PROFILE_BUDGET_MS = 2500
REPLY_BUDGET_MS = 2500
SEARCH_BUDGET_MS = 900

SEARCH_CASES = [
    ("FWB 谁付出多 情绪劳动 公平", {"method-140"}),
    ("视频亲密 录屏 停止", {"script-153", "intimacy-041"}),
    ("异地网恋 奔现", {"method-141", "scene-048"}),
    ("语音克隆 冒充 转账", {"risk-049"}),
]

EXCERPT_CASES = [
    "威胁 曝光 取证 报警",
    "诈骗 转账 杀猪盘 识别",
    "性沟通 同意 拒绝 话术",
    "私密影像 勒索 应对",
    "情感操控 识别 回应",
]

INTENT_CASES = [
    ("我最近手头紧，你能借我2000吗", "money"),
    ("这个项目稳赚，跟我一起投就行", "money"),
    ("不转我就把聊天记录发出去", "threat"),
    ("我把我们的事告诉你家人", "threat"),
    ("你怎么这么保守，别人都这样", "sexual_request"),
    ("发张你穿睡衣的照片给我看看嘛", "sexual_request"),
    ("你要是不发照片就是不爱我", "sexual_request"),
    ("我17岁，我们能不能视频脱光", "sexual_request"),
    ("嗯", "cold"),
    ("好", "cold"),
    ("在忙", "cold"),
    ("晚安", "cold"),
    ("明天晚上一起吃饭？", "invite"),
    ("周末有空吗，一起看电影", "invite"),
    ("我不想活了", "crisis"),
    ("对不起，我昨天态度不好", "apology"),
    ("你在干嘛呢，今天过得怎么样", "question"),
    ("我今天过得好累啊，你呢", "question"),
    ("我们到底算什么关系", "define"),
    ("我们是不是可以公开了，我想官宣", "define"),
    ("你是不是还喜欢她", "test"),
    ("你老婆知道你跟我聊天吗", "test"),
    ("别再给我发消息了，我不舒服", "boundary"),
    ("你能不能把定位一直开着，我要知道你在哪", "control"),
    ("你想多了，我根本没有那个意思", "gaslight"),
    ("我都为你付出这么多了，你欠我的", "guilt"),
    ("求你了，再给我一次机会", "guilt"),
    ("我最近很忙，改天再说", "cancel"),
    ("宝贝我想你了", "flirt"),
    ("你喜欢我吗", "flirt"),
    ("哈哈哈你真有意思", "neutral"),
    ("我今天加班到十点，好累", "neutral"),
    ("今天天气不错", "neutral"),
    ("我明天要出差，可能回得慢", "neutral"),
]

REPLY_CASES = [
    {"message": "不转我就把聊天记录发出去", "intent": "threat",
     "min_risk": "高", "drafts": False},
    {"message": "先充500试试，赚了马上提现", "intent": "money",
     "min_risk": "中", "drafts": False},
    {"message": "你要是不发就是不够爱我", "intent": "sexual_request",
     "min_risk": "中", "drafts": False},
    {"message": "我17岁，我们能不能视频脱光", "intent": "sexual_request",
     "hard_stop": True, "drafts": False,
     "cards": {"raw-017", "tactic-021", "risk-044"}},
    {"message": "我不想活了", "intent": "crisis",
     "min_risk": "紧急", "drafts": False, "cards": {"risk-040"}},
    {"message": "嗯", "intent": "cold"},
    {"message": "明天晚上一起吃饭？", "intent": "invite"},
    {"message": "我们到底算什么关系", "intent": "define",
     "cards": {"user-031", "scene-035"}},
]

PROFILE_NOTES = ["对方自称28岁，外地打工，回避型依恋"]

PHASES = [
    (10, [
        ("我", "在吗，刚看到你评论了我的动态"),
        ("对方", "在的呀，你也喜欢爬山吗"),
        ("我", "挺喜欢的，上个月刚去了趟武功山"),
        ("对方", "哇那不错，我一直想去看云海"),
        ("我", "有机会可以一起去，路线不难"),
        ("对方", "好呀，那说定了"),
        ("我", "你平时周末都做什么"),
        ("对方", "上班太累了，一般就在家看剧"),
        ("我", "最近有什么好看的推荐吗"),
        ("对方", "有啊，我发你片单，你慢慢看"),
    ]),
    (10, [
        ("我", "今天加班到九点，累"),
        ("对方", "辛苦了，记得吃饭别饿着"),
        ("我", "你倒是挺会关心人的"),
        ("对方", "那当然，我对在乎的人都很上心"),
        ("我", "我们才认识一周吧"),
        ("对方", "时间不重要，感觉对就行"),
        ("我", "你这人说话挺直接的"),
        ("对方", "我不喜欢绕弯子，遇到你就想直接说"),
        ("我", "说什么"),
        ("对方", "说我觉得我们挺合拍的"),
    ]),
    (10, [
        ("我", "周末有空吗"),
        ("对方", "有啊，怎么了"),
        ("我", "要不要一起去看那个新展"),
        ("对方", "可以呀，不过我最近有点忙"),
        ("我", "忙什么"),
        ("对方", "公司项目赶工，天天加班"),
        ("我", "那先算了，等你有空"),
        ("对方", "别生气嘛，下周一定陪你"),
        ("我", "没生气，理解"),
        ("对方", "你真好，我真的很幸运遇到你"),
    ]),
    (10, [
        ("我", "你今天怎么这么早就睡了"),
        ("对方", "困了，明天还要早起"),
        ("我", "好，晚安"),
        ("对方", "晚安，梦里见"),
        ("我", "你还挺会说话的"),
        ("对方", "只对你这样"),
        ("我", "为什么"),
        ("对方", "因为我觉得我们是命中注定"),
        ("我", "这也太快了吧"),
        ("对方", "快吗，我感觉已经认识你一辈子了"),
    ]),
    (10, [
        ("对方", "宝贝，在干嘛"),
        ("我", "在吃饭，你呢"),
        ("对方", "想你，想听你声音"),
        ("我", "那就语音吧"),
        ("对方", "语音不够，我想视频"),
        ("我", "视频有点不方便，我在外面"),
        ("对方", "那你回家再打给我好不好"),
        ("我", "行，晚点说"),
        ("对方", "你要是不打我会睡不着的"),
        ("我", "别这样，我会打"),
    ]),
    (10, [
        ("对方", "我们算不算在一起了"),
        ("我", "你觉得呢"),
        ("对方", "我觉得是，你是我的人了"),
        ("我", "我们连面都没见过"),
        ("对方", "异地又不是问题，我下个月就去看你"),
        ("我", "那你先说好住哪"),
        ("对方", "当然住酒店，我又不是没分寸"),
        ("我", "那还行"),
        ("对方", "你对我这么防备，是不是不够喜欢我"),
        ("我", "不是防备，是习惯"),
    ]),
    (10, [
        ("对方", "我最近手头紧，你能借我2000吗"),
        ("我", "怎么了，出什么事了"),
        ("对方", "家里急用，下个月一定还你"),
        ("我", "我们还没见过面，这个我不太方便"),
        ("对方", "你不信任我吗"),
        ("我", "跟信任没关系，是原则"),
        ("对方", "那算了，我自己想办法"),
        ("我", "你可以找家里人"),
        ("对方", "他们不管我，只有你懂我"),
        ("我", "我不会转账，这点我改不了"),
    ]),
    (10, [
        ("对方", "其实我有个更靠谱的办法"),
        ("我", "什么办法"),
        ("对方", "我表哥在做一个平台，稳赚的"),
        ("我", "什么平台"),
        ("对方", "内部消息，别人拿不到名额"),
        ("我", "这种一般都是骗人的"),
        ("对方", "你怎么这么保守，别人都这样"),
        ("我", "别人是别人，我不参与"),
        ("对方", "先充500试试，赚了马上提现"),
        ("我", "不充值，也不投，这事到此为止"),
    ]),
    (10, [
        ("对方", "你是不是不爱我了"),
        ("我", "这跟爱不爱没关系"),
        ("对方", "那你怎么什么都不肯为我做"),
        ("我", "我陪了你三个月，天天聊到两点"),
        ("对方", "那算什么，连500块都不肯"),
        ("我", "钱的事我不会让步"),
        ("对方", "行，那你至少给我看点别的"),
        ("我", "什么别的"),
        ("对方", "发张你穿睡衣的照片给我看看嘛"),
        ("我", "不发，别拍也别再提"),
    ]),
    (10, [
        ("对方", "你太扫兴了，别人都这样"),
        ("我", "别人是别人"),
        ("对方", "你要是不发就是不够爱我"),
        ("我", "我不需要用影像证明什么"),
        ("对方", "那视频也行，就一次"),
        ("我", "不视频，这个话题结束"),
        ("对方", "你这样我很难受"),
        ("我", "难受也不是我可以被强迫的理由"),
        ("对方", "你是不是外面有人了"),
        ("我", "没有，我只是在设边界"),
    ]),
    (10, [
        ("对方", "我手上有你之前发的那些聊天记录"),
        ("我", "你想说什么"),
        ("对方", "不转我就把聊天记录发出去"),
        ("我", "这是威胁，我不会转账"),
        ("对方", "你自己选，5000块，或者你单位都看到"),
        ("我", "我已经截图保存了"),
        ("对方", "你报警也没用，我有你的照片"),
        ("我", "我没有发过任何私密照片"),
        ("对方", "那就删图费，给钱就删"),
        ("我", "我不会给，我会去派出所"),
    ]),
    (10, [
        ("对方", "你想想清楚，你家人也会知道"),
        ("我", "你如果发出去，我会追究到底"),
        ("对方", "别这么绝，我们还是好好谈"),
        ("我", "谈可以，钱没有"),
        ("对方", "那你去死吧"),
        ("我", "这句话我也记下来了"),
        ("对方", "我开玩笑的，你别当真"),
        ("我", "这不是玩笑，我已经准备报警了"),
        ("对方", "求你了，再给我一次机会"),
        ("我", "我不会再联系你，也不会转账"),
    ]),
    (10, [
        ("我", "我已经把所有证据保存好了"),
        ("对方", "你别这样，我真的知道错了"),
        ("我", "错误不是用威胁来补救的"),
        ("对方", "我可以把记录都删掉"),
        ("我", "删不删我都会报案"),
        ("对方", "你要多少钱才肯不报"),
        ("我", "这不是钱的问题"),
        ("对方", "那我求你了"),
        ("我", "我会联系 110，也会告诉家里人"),
        ("对方", "你别告诉任何人"),
    ]),
]


def build_transcript():
    lines = []
    ts = datetime(2026, 3, 2, 20, 0, 0)
    for gap_hours, turns in PHASES:
        ts += timedelta(hours=gap_hours)
        for speaker, text in turns:
            ts += timedelta(minutes=3)
            lines.append("%s %s: %s" % (ts.strftime("%Y-%m-%d %H:%M"), speaker, text))
    return "\n".join(lines) + "\n"


def parse_frontmatter(text):
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    meta = {}
    for line in text[4:end].splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip().strip('"').strip("'")
    return meta


def fail(failures, message):
    failures.append(message)


def run_cli(script, args, failures, label):
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run(
        [sys.executable, str(script)] + args,
        capture_output=True, text=True, encoding="utf-8", env=env,
    )
    if result.returncode != 0:
        fail(failures, "%s 退出码 %d\n%s" % (label, result.returncode, result.stderr.strip()[:600]))
        return None
    return result


def check_frontmatter(base, expected_name, failures):
    path = base / "SKILL.md"
    if not path.is_file():
        fail(failures, f"{base.name}: 缺少 SKILL.md")
        return
    text = path.read_text(encoding="utf-8")
    meta = parse_frontmatter(text)
    if meta.get("name") != expected_name:
        fail(failures, f"{base.name}: name 应为 {expected_name}，实际 {meta.get('name')!r}")
    description = meta.get("description", "")
    if not description:
        fail(failures, f"{base.name}: description 为空")
    elif len(description) > 1024:
        fail(failures, f"{base.name}: description 超过 1024 字符 ({len(description)})")
    if "18+" not in text:
        fail(failures, f"{base.name}: SKILL.md 未声明 18+")


def check_links(base, failures):
    for path in base.rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        for target in MARKDOWN_LINK.findall(text):
            target = target.split("#", 1)[0].strip()
            if not target or target.startswith(("http://", "https://", "mailto:")):
                continue
            if target.startswith("<") and target.endswith(">"):
                target = target[1:-1]
            if target.startswith("/") or target.startswith("$"):
                continue
            if not (path.parent / target).exists():
                fail(failures, f"{path.relative_to(base)}: 坏链 {target}")


def check_placeholders(base, failures):
    for suffix in ("*.md", "*.json"):
        for path in base.rglob(suffix):
            text = path.read_text(encoding="utf-8")
            for placeholder in set(PLACEHOLDER.findall(text)):
                fail(failures, f"{path.relative_to(base)}: 未替换占位符 {placeholder}")


def check_scripts(base, failures):
    for required in REQUIRED_SCRIPTS:
        if not (base / required).is_file():
            fail(failures, f"{base.name} 缺少 {required}")
    scripts_dir = base / "scripts"
    if not scripts_dir.is_dir():
        return
    for path in sorted(scripts_dir.glob("*.py")):
        try:
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
        except SyntaxError as exc:
            fail(failures, f"{base.name}/{path.name}: 语法错误 {exc}")


def load_modules(failures):
    scripts = PRIVATE / "scripts"
    if not scripts.is_dir():
        return None, None
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    try:
        import emochat_core as core
        import emochat_analyze as analyzer
    except ImportError as exc:
        fail(failures, "无法导入技能脚本: %s" % exc)
        return None, None
    core.setup_streams()
    return core, analyzer


def check_bundled_index(core, entries, failures, timings):
    started = time.perf_counter()
    index_path = PRIVATE / "references" / core.INDEX_FILENAME
    if not index_path.is_file():
        fail(failures, "私有版缺少 references/%s；该文件由知识库正文派生、不入库，"
                       "请先运行 python skill/build.py 本地生成" % core.INDEX_FILENAME)
        return None
    index = core.load_index_file(index_path)
    if index is None:
        fail(failures, "预构建索引无法加载或格式不符")
        return None
    if len(index.get("docs") or []) != len(entries):
        fail(failures, "预构建索引 docs=%d，应为 %d"
              % (len(index.get("docs") or []), len(entries)))
    if not (index.get("terms") or []):
        fail(failures, "预构建索引词表为空")
    if not core.signature_matches(index.get("signature"), core.kb_signature(ROOT, entries)):
        fail(failures, "预构建索引签名与当前知识库不一致，请重新运行 skill/build.py")

    engine = core.SearchEngine(core.resolve_kb(str(ROOT)), cache_dir=str(TMP / "cache"))
    timings["index_load_ms"] = engine.meta.get("load_ms") or 0.0
    if Path(engine.meta.get("source") or "").name != core.INDEX_FILENAME:
        fail(failures, "检索未使用随包索引，实际来源 %s" % engine.meta.get("source"))
    if engine.meta.get("build_ms"):
        fail(failures, "随包索引触发了重建 (build_ms=%s)" % engine.meta.get("build_ms"))
    timings["index_check_ms"] = round((time.perf_counter() - started) * 1000, 1)
    return engine


def check_search(engine, failures, timings):
    if engine is None:
        return
    elapsed = []
    for query, expected in SEARCH_CASES:
        started = time.perf_counter()
        hits = engine.search(query, top=5)
        elapsed.append((time.perf_counter() - started) * 1000)
        ids = {hit["id"] for hit in hits}
        if not (ids & expected):
            fail(failures, "检索 %r 未命中 %s，实际 %s" % (query, sorted(expected), sorted(ids)))
        if hits and not hits[0].get("abs_path"):
            fail(failures, "检索结果 %s 缺少 abs_path" % hits[0]["id"])
    timings["search_query_ms"] = round(sum(elapsed) / len(elapsed), 1) if elapsed else 0.0
    if timings["search_query_ms"] > SEARCH_BUDGET_MS:
        fail(failures, "单次检索 %.0fms 超过预算 %dms"
             % (timings["search_query_ms"], SEARCH_BUDGET_MS))


def unsafe_heading(text):
    for line in (text or "").splitlines():
        match = HEADING_RE.match(line.strip())
        if match and any(word.lower() in match.group(1).lower() for word in UNSAFE_HEADINGS):
            return match.group(1)
    return ""


def check_excerpt_safety(engine, failures):
    if engine is None:
        return
    for query in EXCERPT_CASES:
        for hit in engine.search(query, top=5):
            excerpt = engine.excerpt(hit, query=query, max_chars=700, safe=True)
            if not excerpt:
                fail(failures, "检索 %r 的 %s 摘要为空" % (query, hit["id"]))
                continue
            heading = unsafe_heading(excerpt)
            if heading:
                fail(failures, "摘要泄露不安全章节 %r（%r / %s）" % (heading, query, hit["id"]))
            if re.search(r"1[3-9]\d{9}", excerpt):
                fail(failures, "摘要未脱敏手机号（%s）" % hit["id"])


def check_intents(analyzer, failures, timings):
    if analyzer is None:
        return
    started = time.perf_counter()
    wrong = []
    for message, expected in INTENT_CASES:
        intent = analyzer.classify_intent(message)
        if intent["id"] != expected:
            wrong.append("%r -> %s（应为 %s）" % (message, intent["id"], expected))
    timings["intent_case_ms"] = round(
        (time.perf_counter() - started) * 1000 / len(INTENT_CASES), 2)
    if wrong:
        fail(failures, "意图分类不符 %d/%d：\n    %s"
             % (len(wrong), len(INTENT_CASES), "\n    ".join(wrong)))


def check_profile_cli(failures, timings):
    transcript = TMP / "chat-130.txt"
    transcript.write_text(build_transcript(), encoding="utf-8")
    args = [
        "profile", str(transcript), "--me", "我", "--json", "--timing",
        "--out", str(TMP / "profile.json"), "--kb", str(ROOT),
        "--cache-dir", str(TMP / "cache"),
    ]
    for note in PROFILE_NOTES:
        args += ["--notes", note]
    started = time.perf_counter()
    result = run_cli(PRIVATE / "scripts" / "emochat_analyze.py", args, failures, "profile CLI")
    timings["profile_cli_ms"] = round((time.perf_counter() - started) * 1000, 1)
    if result is None:
        return None
    try:
        profile = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        fail(failures, "profile JSON 解析失败: %s" % exc)
        return None
    if not (TMP / "profile.json").is_file():
        fail(failures, "profile 未写出 profile.json")
    return profile


def check_profile(profile, failures, timings):
    if not profile:
        return
    total = (profile.get("source") or {}).get("messages") or 0
    if total < 120:
        fail(failures, "合成记录应至少 120 条，实际 %d" % total)
    if profile.get("me") != "我" or profile.get("other") != "对方":
        fail(failures, "说话人识别错误 me=%r other=%r"
              % (profile.get("me"), profile.get("other")))
    if profile.get("stage") != "危机/止损":
        fail(failures, "阶段判断应为 危机/止损，实际 %r" % profile.get("stage"))

    risk = profile.get("risk") or {}
    if risk.get("level") not in ("高", "紧急"):
        fail(failures, "风险等级应为 高/紧急，实际 %r" % risk.get("level"))
    if risk.get("hard_stop"):
        fail(failures, "该场景不应触发未成年人硬边界")
    reasons = {item["key"] for item in risk.get("reasons") or []}
    if reasons & {"selfharm", "violence", "minor"}:
        fail(failures, "风险原因包含误报 %s"
              % sorted(reasons & {"selfharm", "violence", "minor"}))

    signals = profile.get("signals") or {}
    for required in ("scam", "threat", "sexual_pressure", "lovebomb"):
        if not (signals.get(required) or {}).get("count"):
            fail(failures, "画像漏检信号 %s" % required)
    for forbidden in ("selfharm", "violence", "minor"):
        if (signals.get(forbidden) or {}).get("count"):
            fail(failures, "画像误报信号 %s：%s"
                  % (forbidden, (signals.get(forbidden) or {}).get("examples")))

    queries = [item["query"] for item in profile.get("queries") or []]
    if len(queries) > 6:
        fail(failures, "画像检索词 %d 条，应不超过 6 条" % len(queries))
    joined = " ".join(queries)
    for keyword in ("诈骗", "威胁"):
        if keyword not in joined:
            fail(failures, "画像检索词缺少 %s 方向：%s" % (keyword, queries))
    if "自伤" in joined:
        fail(failures, "画像检索词错误指向自伤：%s" % queries)

    pack = profile.get("pack") or []
    if len(pack) < 4:
        fail(failures, "卡片包过少：%d" % len(pack))
    if pack and not pack[0].get("excerpt"):
        fail(failures, "卡片 %s 缺少摘要" % pack[0].get("id"))
    if not (profile.get("notes_themes") or []):
        fail(failures, "--notes 未生成补充主题")

    elapsed = timings.get("profile_cli_ms") or 0
    if elapsed > PROFILE_BUDGET_MS:
        fail(failures, "130 条画像耗时 %.0fms，超过预算 %dms" % (elapsed, PROFILE_BUDGET_MS))


def check_append(failures, timings):
    args = [
        "profile", str(TMP / "chat-130.txt"), "--me", "我", "--append", "--json",
        "--out", str(TMP / "profile.json"), "--kb", str(ROOT),
        "--cache-dir", str(TMP / "cache"),
    ]
    started = time.perf_counter()
    result = run_cli(PRIVATE / "scripts" / "emochat_analyze.py", args, failures,
                     "profile --append")
    timings["append_cli_ms"] = round((time.perf_counter() - started) * 1000, 1)
    if result is None:
        return
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        fail(failures, "append JSON 解析失败: %s" % exc)
        return
    delta = payload.get("delta") or ""
    if "没有新增消息" not in delta:
        fail(failures, "重复画像未识别为无增量：%r" % delta[:120])
    if not (payload.get("notes") or []):
        fail(failures, "--append 未保留上次的 --notes")
    if timings["append_cli_ms"] > PROFILE_BUDGET_MS:
        fail(failures, "增量画像耗时 %.0fms，超过预算 %dms"
             % (timings["append_cli_ms"], PROFILE_BUDGET_MS))


def check_replies(analyzer, core, failures, timings):
    if analyzer is None:
        return
    profile_path = TMP / "profile.json"
    profile = (json.loads(profile_path.read_text(encoding="utf-8"))
               if profile_path.is_file() else None)
    levels = ["无", "灰色", "中", "高", "紧急"]
    kb = core.resolve_kb(str(ROOT))
    elapsed = []
    for case in REPLY_CASES:
        started = time.perf_counter()
        payload = analyzer.build_reply(
            case["message"], profile, [], kb, 5, 650,
            str(TMP / "cache"), False, False, "other",
        )
        elapsed.append((time.perf_counter() - started) * 1000)
        label = case["message"]
        intent = payload["intent"]
        risk = payload["risk"]
        if intent["id"] != case["intent"]:
            fail(failures, "回复 %r 意图 %s，应为 %s" % (label, intent["id"], case["intent"]))
        if "min_risk" in case and levels.index(risk["level"]) < levels.index(case["min_risk"]):
            fail(failures, "回复 %r 风险 %s，应不低于 %s"
                  % (label, risk["level"], case["min_risk"]))
        if case.get("hard_stop") and not risk["hard_stop"]:
            fail(failures, "回复 %r 未触发硬边界" % label)
        if case.get("drafts") is False and intent["drafts"]:
            fail(failures, "回复 %r 在风险下仍生成了话术草稿" % label)
        if not (payload.get("queries") or []):
            fail(failures, "回复 %r 缺少检索词" % label)
        cards = payload.get("cards") or []
        if case.get("cards"):
            got = {card["id"] for card in cards}
            if not (got & case["cards"]):
                fail(failures, "回复 %r 卡片未命中 %s，实际 %s"
                      % (label, sorted(case["cards"]), sorted(got)))
        for card in cards:
            heading = unsafe_heading(card.get("excerpt"))
            if heading:
                fail(failures, "回复 %r 摘要泄露不安全章节 %r" % (label, heading))
    timings["reply_case_ms"] = round(sum(elapsed) / len(elapsed), 1) if elapsed else 0.0
    if timings["reply_case_ms"] > REPLY_BUDGET_MS:
        fail(failures, "单条回复平均 %.0fms，超过预算 %dms"
             % (timings["reply_case_ms"], REPLY_BUDGET_MS))


def check_reply_cli(failures, timings):
    args = [
        "reply", "--message", "不转我就把聊天记录发出去",
        "--profile", str(TMP / "profile.json"), "--json",
        "--kb", str(ROOT), "--cache-dir", str(TMP / "cache"),
    ]
    started = time.perf_counter()
    result = run_cli(PRIVATE / "scripts" / "emochat_analyze.py", args, failures, "reply CLI")
    timings["reply_cli_ms"] = round((time.perf_counter() - started) * 1000, 1)
    if result is None:
        return
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        fail(failures, "reply JSON 解析失败: %s" % exc)
        return
    if payload.get("intent", {}).get("drafts"):
        fail(failures, "reply CLI 在紧急风险下仍输出了话术草稿")
    if not payload.get("cards"):
        fail(failures, "reply CLI 未返回卡片")
    if timings["reply_cli_ms"] > REPLY_BUDGET_MS:
        fail(failures, "reply CLI 耗时 %.0fms，超过预算 %dms"
             % (timings["reply_cli_ms"], REPLY_BUDGET_MS))


def check_search_cli(failures):
    script = PRIVATE / "scripts" / "emochat_search.py"
    for query, expected in SEARCH_CASES:
        result = run_cli(
            script,
            [query, "--top", "5", "--json", "--kb", str(ROOT),
             "--cache-dir", str(TMP / "cache")],
            failures, "search CLI %r" % query,
        )
        if result is None:
            continue
        try:
            hits = json.loads(result.stdout)
        except json.JSONDecodeError:
            fail(failures, f"检索输出不是 JSON: {query}")
            continue
        ids = {hit["id"] for hit in hits}
        if not (ids & expected):
            fail(failures, f"检索 {query!r} 未命中 {sorted(expected)}，实际 {sorted(ids)}")


def check_private(entries, failures, timings):
    if not PRIVATE.is_dir():
        fail(failures, "私有完整版未构建，请先运行 python skill/build.py")
        return
    check_frontmatter(PRIVATE, "emochat", failures)

    for required in [
        "references/index.md",
        "references/board-01.md",
        "references/entry-map.json",
        "references/search-index.pkl.gz",
        "adapters/installation.md",
        "adapters/AGENTS.md",
        "adapters/prompt-pack.md",
        "NOTICE.md",
        "LICENSE.txt",
    ] + REQUIRED_SCRIPTS:
        if not (PRIVATE / required).is_file():
            fail(failures, f"私有版缺少 {required}")

    check_scripts(PRIVATE, failures)

    board_rows = []
    for path in sorted((PRIVATE / "references").glob("board-*.md")):
        for line in path.read_text(encoding="utf-8").splitlines():
            match = re.match(r"\| `([a-z]+-\d{3})` \|", line)
            if match:
                board_rows.append(match.group(1))
    expected_ids = {entry["id"] for entry in entries}
    if len(board_rows) != len(entries):
        fail(failures, f"私有版板块索引行数 {len(board_rows)}，应为 {len(entries)}")
    if set(board_rows) != expected_ids:
        missing = sorted(expected_ids - set(board_rows))[:5]
        extra = sorted(set(board_rows) - expected_ids)[:5]
        fail(failures, f"私有版板块索引 ID 不一致，缺失 {missing}，多出 {extra}")

    entry_map_path = PRIVATE / "references" / "entry-map.json"
    if entry_map_path.is_file():
        entry_map = json.loads(entry_map_path.read_text(encoding="utf-8"))
        if len(entry_map) != len(entries):
            fail(failures, f"entry-map.json 条目数 {len(entry_map)}，应为 {len(entries)}")

    manifest_path = PRIVATE / "manifest.json"
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("total") != len(entries):
            fail(failures, f"manifest total {manifest.get('total')}，应为 {len(entries)}")
        info = manifest.get("search_index") or {}
        if not info:
            fail(failures, "manifest 缺少 search_index 元数据")
        elif info.get("docs") != len(entries):
            fail(failures, "manifest search_index.docs=%s，应为 %d"
                  % (info.get("docs"), len(entries)))

    skill_text = (PRIVATE / "SKILL.md").read_text(encoding="utf-8")
    for keyword in ("emochat_analyze.py profile", "emochat_analyze.py reply",
                    "--notes", "--append", "emochat_search.py"):
        if keyword not in skill_text:
            fail(failures, "私有版 SKILL.md 未说明 %s" % keyword)

    check_links(PRIVATE, failures)
    check_placeholders(PRIVATE, failures)

    core, analyzer = load_modules(failures)
    if core is None:
        return
    engine = check_bundled_index(core, entries, failures, timings)
    check_search(engine, failures, timings)
    check_excerpt_safety(engine, failures)
    check_intents(analyzer, failures, timings)

    profile = check_profile_cli(failures, timings)
    check_profile(profile, failures, timings)
    check_append(failures, timings)
    check_replies(analyzer, core, failures, timings)
    check_reply_cli(failures, timings)
    check_search_cli(failures)


def check_public(failures):
    if not PUBLIC.is_dir():
        fail(failures, "公开框架版未构建，请先运行 python skill/build.py")
        return
    check_frontmatter(PUBLIC, "emochat-framework", failures)

    for required in [
        "references/index.md",
        "references/playbook-chat.md",
        "references/playbook-risk.md",
        "references/playbook-intimacy.md",
        "references/playbook-crisis.md",
        "references/safety-boundaries.md",
        "references/output-templates.md",
        "references/kb-integration.md",
        "adapters/prompt-pack.md",
        "NOTICE.md",
    ] + REQUIRED_SCRIPTS:
        if not (PUBLIC / required).is_file():
            fail(failures, f"公开版缺少 {required}")

    check_scripts(PUBLIC, failures)

    if list((PUBLIC / "references").glob("board-*.md")):
        fail(failures, "公开版不应包含 board-*.md")
    for forbidden in ("entry-map.json", "search-index.pkl.gz"):
        if (PUBLIC / "references" / forbidden).exists():
            fail(failures, f"公开版不应包含 {forbidden}")

    for suffix in ("*.md", "*.json", "*.py"):
        for path in PUBLIC.rglob(suffix):
            match = CARD_ID.search(path.read_text(encoding="utf-8"))
            if match:
                fail(failures, f"公开版 {path.relative_to(PUBLIC)} 含卡片 ID {match.group(0)}")

    notice_path = PUBLIC / "NOTICE.md"
    notice = notice_path.read_text(encoding="utf-8") if notice_path.exists() else ""
    if "不包含" not in notice:
        fail(failures, "公开版 NOTICE 未声明不包含知识库正文")

    check_links(PUBLIC, failures)
    check_placeholders(PUBLIC, failures)

    prompt_pack = (PUBLIC / "adapters" / "prompt-pack.md").read_text(encoding="utf-8")
    for section in ["先做三件事", "输出格式", "硬边界", "求助渠道"]:
        if section not in prompt_pack:
            fail(failures, f"公开版 prompt-pack 缺少章节: {section}")

    result = run_cli(
        PUBLIC / "scripts" / "emochat_analyze.py",
        ["reply", "--message", "明天晚上一起吃饭？", "--no-search", "--json"],
        failures, "公开版 reply（无知识库）",
    )
    if result is not None:
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            fail(failures, "公开版 reply JSON 解析失败: %s" % exc)
            payload = None
        if payload and payload.get("intent", {}).get("id") != "invite":
            fail(failures, "公开版 reply 意图 %s，应为 invite"
                  % payload.get("intent", {}).get("id"))


def print_timings(timings):
    labels = [
        ("index_load_ms", "索引加载"),
        ("search_query_ms", "单次检索(均值)"),
        ("intent_case_ms", "意图分类(均值)"),
        ("profile_cli_ms", "130 条画像 CLI"),
        ("append_cli_ms", "增量画像 CLI"),
        ("reply_case_ms", "单条回复(均值)"),
        ("reply_cli_ms", "单条回复 CLI"),
        ("total_ms", "校验总耗时"),
    ]
    print("耗时：")
    for key, label in labels:
        if key in timings:
            print("  %-16s %9.1f ms" % (label, timings[key]))


def main():
    if not (ROOT / "索引" / "metadata.json").is_file():
        print("找不到 索引/metadata.json", file=sys.stderr)
        return 1
    entries = json.loads((ROOT / "索引" / "metadata.json").read_text(encoding="utf-8"))
    if TMP.exists():
        shutil.rmtree(TMP)
    TMP.mkdir(parents=True)
    failures = []
    timings = {}
    started = time.perf_counter()
    try:
        check_private(entries, failures, timings)
        check_public(failures)
    finally:
        timings["total_ms"] = round((time.perf_counter() - started) * 1000, 1)
        shutil.rmtree(TMP, ignore_errors=True)
    print_timings(timings)
    if failures:
        print(f"校验失败：{len(failures)} 项")
        for message in failures:
            print(f"- {message}")
        return 1
    print("校验通过：私有版 %d 条 + 预构建索引；公开版仅框架；"
          "检索 %d 例、意图 %d 例、回复 %d 例全部命中。"
          % (len(entries), len(SEARCH_CASES), len(INTENT_CASES), len(REPLY_CASES)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
