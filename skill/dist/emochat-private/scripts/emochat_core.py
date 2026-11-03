# -*- coding: utf-8 -*-
"""EmoChat-KB 检索核心。

零第三方依赖。负责：
- 知识库路径解析
- 预构建 / 缓存 BM25 索引
- 字段加权检索、同义词扩展、板块路由、批量合并
- 卡片摘要抽取与隐私打码

索引由 `skill/build.py` 预生成到 `references/search-index.pkl.gz`；
知识库变化或没有预构建索引时，自动在缓存目录生成。
"""
import gzip
import hashlib
import json
import math
import os
import pickle
import re
import tempfile
import time
from array import array
from bisect import bisect_left
from collections import Counter, OrderedDict
from pathlib import Path

INDEX_FORMAT = "emochat-index-v1"
INDEX_FILENAME = "search-index.pkl.gz"
CACHE_ENV = "EMOCHAT_CACHE"
K1 = 1.5
B = 0.75

STOPWORDS = {
    "的", "了", "是", "在", "我", "你", "他", "她", "它", "们", "这", "那",
    "有", "和", "就", "不", "也", "都", "还", "要", "会", "到", "对", "吗",
    "呢", "吧", "啊", "呀", "哦", "嗯", "把", "被", "给", "让", "从", "为",
    "上", "下", "里", "中", "个", "很", "太", "更", "最", "又", "再", "才",
    "我们", "你们", "他们", "她们", "这个", "那个", "就是", "还是", "但是",
    "因为", "所以", "如果", "然后", "现在", "已经", "什么", "怎么", "为什",
    "可以", "不是", "没有", "觉得", "真的", "有点", "一下", "这样", "那样",
    "自己", "时候", "一个", "那些", "这些", "以及", "或者", "而且", "不过",
}

SYNONYMS = [
    ("fwb", ["休闲关系", "非承诺关系", "friend with benefits"]),
    ("炮友", ["休闲关系", "非承诺", "边界"]),
    ("网恋", ["异地恋", "线上关系", "奔现"]),
    ("异地", ["距离", "见面", "网恋"]),
    ("奔现", ["见面", "安全", "公共场所"]),
    ("冷暴力", ["已读不回", "忽视", "冷淡"]),
    ("已读不回", ["冷淡", "回复", "停止追加"]),
    ("忽冷忽热", ["推拉", "操控", "不稳定"]),
    ("pua", ["操控", "打压", "情感操控"]),
    ("杀猪盘", ["诈骗", "投资", "转账"]),
    ("诈骗", ["转账", "验证码", "核实"]),
    ("借钱", ["转账", "边界", "拒绝"]),
    ("投资", ["平台", "转账", "风险"]),
    ("裸聊", ["私密影像", "录屏", "勒索"]),
    ("私密影像", ["录屏", "截图", "传播"]),
    ("录屏", ["偷拍", "隐私", "停止"]),
    ("同意", ["自愿", "边界", "撤回"]),
    ("边界", ["拒绝", "停止", "尊重"]),
    ("拒绝", ["边界", "停止", "尊重"]),
    ("分手", ["止损", "断联", "退出"]),
    ("复合", ["分手", "判断", "边界"]),
    ("暧昧", ["兴趣", "推进", "关系定义"]),
    ("邀约", ["见面", "时间", "地点"]),
    ("关系定义", ["专一", "期待", "沟通"]),
    ("权力差", ["师生", "上下级", "资源"]),
    ("师生", ["权力差", "边界", "投诉"]),
    ("第三者", ["已婚", "出轨", "边界"]),
    ("包养", ["交易", "资源", "边界"]),
    ("语音克隆", ["冒充", "核实", "转账"]),
    ("冒充", ["核实", "官方渠道", "诈骗"]),
    ("跟踪", ["定位", "骚扰", "报警"]),
    ("威胁", ["曝光", "勒索", "取证"]),
    ("家暴", ["暴力", "安全", "求助"]),
    ("自伤", ["危机", "求助", "陪伴"]),
    ("依恋", ["回避型", "焦虑型", "沟通"]),
    ("回避型", ["依恋", "距离", "沟通"]),
    ("焦虑型", ["依恋", "确认", "边界"]),
]

BOARD_HINTS = [
    (("诈骗", "转账", "投资", "借钱", "杀猪", "验证码", "敲诈", "勒索", "裸聊",
      "威胁", "曝光", "跟踪", "暴力", "隐私", "录屏", "定位", "冒充", "语音克隆",
      "家暴", "安全", "报警", "取证", "止损"),
     ("06", "07")),
    (("亲密", "性", "同意", "边界", "拒绝", "避孕", "安全套", "影像", "视频",
      "语音", "线上", "fwb", "私密", "异地", "网恋"),
     ("11", "02", "12")),
    (("聊天", "回复", "邀约", "暧昧", "推进", "兴趣", "接话", "开场", "表白",
      "相亲", "话题", "热聊"),
     ("01", "02", "05")),
    (("分手", "复合", "冷战", "断联", "冲突", "道歉", "修复", "长期"),
     ("01", "05", "02")),
    (("画像", "依恋", "回避", "焦虑", "mbti", "星座", "性格", "人群"),
     ("03", "04", "12")),
    (("第三者", "已婚", "开放关系", "形婚", "包养", "交易", "契约", "权力差"),
     ("03", "12", "01")),
]

RISK_HINTS = (
    "诈骗", "转账", "投资", "借钱", "威胁", "曝光", "勒索", "隐私", "录屏",
    "跟踪", "暴力", "家暴", "自杀", "自伤", "未成年", "迷药", "裸聊", "验证码",
)

PII_PATTERNS = [
    (re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"), "1**********"),
    (re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)"), "[身份证已屏蔽]"),
    (re.compile(r"(?<!\d)\d{16,19}(?!\d)"), "[卡号已屏蔽]"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "[邮箱已屏蔽]"),
    (re.compile(r"(?i)(?:微信|wechat|qq|vx)[:：]?\s*[A-Za-z0-9_-]{5,}"), "微信/QQ已屏蔽"),
]


def setup_streams():
    import sys
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except (OSError, ValueError):
                pass


def mask_pii(text):
    text = str(text)
    for pattern, replacement in PII_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def is_kb(path):
    return (path / "索引" / "metadata.json").is_file()


def resolve_kb(explicit=None):
    if explicit:
        candidate = Path(explicit).expanduser()
        return candidate.resolve() if is_kb(candidate) else None
    env = os.environ.get("EMOCHAT_KB")
    if env:
        candidate = Path(env).expanduser()
        return candidate.resolve() if is_kb(candidate) else None
    here = Path(__file__).resolve()
    config = here.parent.parent / ".emochat-kb"
    try:
        configured = config.read_text(encoding="utf-8").strip()
    except OSError:
        configured = ""
    if configured:
        candidate = Path(configured.splitlines()[0].strip()).expanduser()
        return candidate.resolve() if is_kb(candidate) else None
    for candidate in [here.parent, *here.parents]:
        try:
            candidate = candidate.resolve()
        except OSError:
            continue
        if is_kb(candidate):
            return candidate
    return None


def skill_root():
    return Path(__file__).resolve().parent.parent


def read_metadata(kb):
    path = kb / "索引" / "metadata.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SystemExit("无法读取 metadata: %s\n%s" % (path, exc))
    if not isinstance(data, list):
        raise SystemExit("metadata.json 应为数组: %s" % path)
    return [item for item in data if isinstance(item, dict)]


def normalize_text(text):
    return str(text).replace("\u200b", "").replace("\ufeff", "")


def tokenize(text):
    text = normalize_text(text)
    tokens = []
    for word in re.findall(r"[A-Za-z0-9]+", text.lower()):
        tokens.append(word)
    for segment in re.findall(r"[\u4e00-\u9fff]+", text):
        if len(segment) == 1:
            tokens.append(segment)
        for index in range(len(segment) - 1):
            tokens.append(segment[index:index + 2])
    return tokens


def query_token_weights(query, max_tokens=48):
    base = tokenize(query)
    filtered = [token for token in base if token not in STOPWORDS] or base
    weights = OrderedDict()
    for token in filtered:
        weights[token] = min(2.0, weights.get(token, 0.0) + 1.0)
    normalized = normalize_text(query).lower()
    for key, expansions in SYNONYMS:
        if key not in normalized:
            continue
        for expansion in expansions:
            for token in tokenize(expansion):
                if token in STOPWORDS:
                    continue
                if token not in weights:
                    weights[token] = 0.35
                if len(weights) >= max_tokens:
                    return weights
    return OrderedDict(list(weights.items())[:max_tokens])


def phrases_of(query):
    phrases = []
    for segment in re.findall(r"[\u4e00-\u9fff]{2,}", normalize_text(query)):
        if segment not in STOPWORDS:
            phrases.append(segment)
    for word in re.findall(r"[A-Za-z0-9]{2,}", normalize_text(query)):
        phrases.append(word.lower())
    ordered = []
    for phrase in phrases:
        if phrase not in ordered:
            ordered.append(phrase)
    return ordered[:8]


def phrase_form(text):
    return re.sub(r"[\s\W_]+", "", normalize_text(text).lower())


def kb_signature(kb, entries=None, fast=False):
    metadata_path = kb / "索引" / "metadata.json"
    try:
        stat = metadata_path.stat()
    except OSError:
        return {}
    entries = entries if entries is not None else read_metadata(kb)
    base = {
        "total": len(entries),
        "metadata_size": stat.st_size,
        "metadata_mtime_ns": stat.st_mtime_ns,
    }
    if fast:
        return base
    total_bytes = 0
    max_mtime = 0
    missing = 0
    for item in entries:
        relative = str(item.get("file") or "").replace("\\", "/")
        if not relative:
            missing += 1
            continue
        try:
            card = (kb / relative).stat()
            total_bytes += card.st_size
            max_mtime = max(max_mtime, card.st_mtime_ns)
        except OSError:
            missing += 1
    base.update({
        "card_bytes": total_bytes,
        "card_mtime_ns": max_mtime,
        "missing": missing,
    })
    return base


def signature_matches(stored, current):
    if not isinstance(stored, dict) or not isinstance(current, dict):
        return False
    for key, value in current.items():
        if stored.get(key) != value:
            return False
    return True


def _add_tokens(counter, tokens, weight):
    for token in tokens:
        counter[token] += weight


def build_index(kb, entries=None):
    started = time.perf_counter()
    entries = entries if entries is not None else read_metadata(kb)
    signature = kb_signature(kb, entries)
    vocab = {}
    terms = []
    docs = []

    def term_id(token):
        value = vocab.get(token)
        if value is None:
            value = len(terms)
            vocab[token] = value
            terms.append(token)
        return value

    for item in entries:
        relative = str(item.get("file") or "").replace("\\", "/")
        body = ""
        if relative:
            try:
                body = (kb / relative).read_text(encoding="utf-8", errors="ignore")
            except OSError:
                body = ""
        title = str(item.get("title") or "")
        tags = [str(value) for value in (item.get("tags") or [])]
        audience = [str(value) for value in (item.get("audience") or [])]
        stage = [str(value) for value in (item.get("stage") or [])]
        meta_parts = [str(item.get("type") or ""), str(item.get("board") or "")]
        meta_parts.extend(audience)
        meta_parts.extend(stage)

        weighted = Counter()
        _add_tokens(weighted, tokenize(title), 4)
        _add_tokens(weighted, tokenize(" ".join(tags)), 3)
        _add_tokens(weighted, tokenize(" ".join(meta_parts)), 2)
        _add_tokens(weighted, tokenize(body), 1)
        if not weighted:
            continue
        pairs = sorted((term_id(token), count) for token, count in weighted.items())
        ids = array("I", (pair[0] for pair in pairs))
        max_count = max((pair[1] for pair in pairs), default=0)
        if max_count > 65535:
            counts = array("I", (pair[1] for pair in pairs))
        else:
            counts = array("H", (pair[1] for pair in pairs))
        docs.append({
            "id": str(item.get("id") or "?"),
            "title": title,
            "path": relative,
            "tags": tags,
            "type": str(item.get("type") or ""),
            "stage": stage,
            "audience": audience,
            "severity": str(item.get("severity") or ""),
            "board": str(item.get("board") or ""),
            "len": sum(weighted.values()),
            "ids": ids,
            "counts": counts,
        })

    total_len = sum(doc["len"] for doc in docs)
    index = {
        "format": INDEX_FORMAT,
        "signature": signature,
        "terms": terms,
        "docs": docs,
        "avgdl": (total_len / len(docs)) if docs else 0.0,
        "build_seconds": round(time.perf_counter() - started, 3),
    }
    return index


def write_index(index, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with gzip.open(str(temporary), "wb", compresslevel=6) as handle:
        pickle.dump(index, handle, protocol=4)
    os.replace(str(temporary), str(path))


def load_index_file(path):
    try:
        with gzip.open(str(path), "rb") as handle:
            index = pickle.load(handle)
    except (OSError, ValueError, EOFError, pickle.UnpicklingError):
        return None
    except Exception:
        return None
    if not isinstance(index, dict) or index.get("format") != INDEX_FORMAT:
        return None
    if not index.get("docs") or not index.get("terms"):
        return None
    return index


def _writable(path):
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".write-test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return True
    except OSError:
        return False


def resolve_cache_dir(explicit=None):
    if explicit:
        path = Path(explicit).expanduser().resolve()
        if _writable(path):
            return path
    env = os.environ.get(CACHE_ENV)
    if env:
        path = Path(env).expanduser().resolve()
        if _writable(path):
            return path
    candidates = [skill_root() / "cache"]
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        if base:
            candidates.append(Path(base) / "emochat" / "cache")
    else:
        base = os.environ.get("XDG_CACHE_HOME")
        candidates.append((Path(base) if base else Path.home() / ".cache") / "emochat")
    candidates.append(Path(tempfile.gettempdir()) / "emochat-cache")
    for candidate in candidates:
        try:
            candidate = candidate.expanduser().resolve()
        except OSError:
            continue
        if _writable(candidate):
            return candidate
    return Path(tempfile.gettempdir())


def load_index(kb, cache_dir=None, rebuild=False, bundled_dir=None, entries=None):
    started = time.perf_counter()
    fast_signature = kb_signature(kb, entries, fast=True)
    bundled_dir = Path(bundled_dir) if bundled_dir else skill_root() / "references"
    cache_dir = resolve_cache_dir(cache_dir)
    kb_key = hashlib.sha1(str(Path(kb).resolve()).encode("utf-8")).hexdigest()[:12]
    cached = cache_dir / ("emochat-index-%s.pkl.gz" % kb_key)
    strict = os.environ.get("EMOCHAT_INDEX_STRICT") == "1"

    loaded = []
    if not rebuild:
        for path in (bundled_dir / INDEX_FILENAME, cached):
            if not path.is_file():
                continue
            index = load_index_file(path)
            if index is None:
                continue
            loaded.append((path, index))
            if not strict and signature_matches(index.get("signature"), fast_signature):
                return index, {
                    "source": str(path),
                    "load_ms": round((time.perf_counter() - started) * 1000, 1),
                    "build_ms": 0.0,
                    "cached": True,
                    "signature": index.get("signature"),
                    "cache_dir": str(cache_dir),
                }

    if loaded:
        full_signature = kb_signature(kb, entries)
        for path, index in loaded:
            if signature_matches(index.get("signature"), full_signature):
                return index, {
                    "source": str(path),
                    "load_ms": round((time.perf_counter() - started) * 1000, 1),
                    "build_ms": 0.0,
                    "cached": True,
                    "signature": index.get("signature"),
                    "cache_dir": str(cache_dir),
                }

    build_started = time.perf_counter()
    index = build_index(kb, entries)
    build_ms = round((time.perf_counter() - build_started) * 1000, 1)
    try:
        write_index(index, cached)
        source = str(cached)
    except OSError:
        source = "memory"
    return index, {
        "source": source,
        "load_ms": round((time.perf_counter() - started) * 1000, 1),
        "build_ms": build_ms,
        "cached": False,
        "signature": index.get("signature"),
        "cache_dir": str(cache_dir),
    }


def _board_prior_moment(query_moment, board):
    for hints, prefixes in BOARD_HINTS:
        if any(hint in query_moment for hint in hints):
            if any(board.startswith(prefix) for prefix in prefixes):
                return 1.08
    return 1.0


def _type_boost_moment(query_moment, doc_type):
    if any(word in query_moment for word in ("话术", "怎么回", "回复", "怎么说")):
        if "话术" in doc_type:
            return 1.08
    if any(word in query_moment for word in ("识别", "信号", "表现", "判断", "是不是")):
        if any(word in doc_type for word in ("识别", "风险", "判定")):
            return 1.06
    return 1.0


def _severity_boost_moment(query, severity):
    if severity in ("高", "紧急") and any(hint in query for hint in RISK_HINTS):
        return 1.06
    return 1.0


def _normalized_title(title):
    return re.sub(r"[\s\W_]+", "", normalize_text(title).lower())


def _diversify(results, top, per_board=3):
    chosen = []
    overflow = []
    seen_titles = []
    board_counts = Counter()
    for result in results:
        normalized = _normalized_title(result["title"])
        duplicate = False
        for seen in seen_titles:
            if normalized == seen:
                duplicate = True
                break
            if len(normalized) >= 8 and len(seen) >= 8 and (normalized in seen or seen in normalized):
                duplicate = True
                break
        if duplicate:
            continue
        board_key = str(result.get("board") or "")[:2]
        if per_board and board_counts[board_key] >= per_board:
            overflow.append(result)
            continue
        chosen.append(result)
        seen_titles.append(normalized)
        board_counts[board_key] += 1
        if len(chosen) >= top:
            return chosen[:top]
    for result in overflow:
        if len(chosen) >= top:
            break
        chosen.append(result)
    return chosen[:top]


class SearchEngine:
    def __init__(self, kb, cache_dir=None, rebuild=False):
        self.kb = Path(kb)
        self.index, self.meta = load_index(self.kb, cache_dir=cache_dir, rebuild=rebuild)
        self.docs = self.index["docs"]
        self.terms = self.index["terms"]
        self.vocab = {token: index for index, token in enumerate(self.terms)}
        self.avgdl = float(self.index.get("avgdl") or 0.0)
        self._body_cache = {}
        self._body_form_cache = {}
        self._doc_position = {id(doc): index for index, doc in enumerate(self.docs)}
        self._form_cache = {}

    def _read_body(self, doc):
        relative = doc.get("path") or ""
        if not relative:
            return ""
        if relative in self._body_cache:
            return self._body_cache[relative]
        try:
            text = (self.kb / relative).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            text = ""
        if len(self._body_cache) < 256:
            self._body_cache[relative] = text
        return text

    def search(self, query, top=8, tag=None, board=None, diversify=True,
               read_bodies=True, exclude_ids=None):
        weights = query_token_weights(query)
        if not weights or top <= 0:
            return []
        token_weights = {}
        for token, weight in weights.items():
            token_id = self.vocab.get(token)
            if token_id is not None:
                token_weights[token_id] = weight
        if not token_weights:
            return []
        filtered = []
        for doc in self.docs:
            if exclude_ids and doc["id"] in exclude_ids:
                continue
            if board and not (
                str(doc["board"]).startswith(board) or str(doc["path"]).startswith(board)
            ):
                continue
            if tag:
                haystack = " ".join(
                    [str(item) for item in doc["tags"]]
                    + [str(item) for item in doc["audience"]]
                    + [doc["type"]]
                )
                if tag not in haystack:
                    continue
            filtered.append(doc)
        if not filtered:
            return []

        total = len(filtered)
        avgdl = sum(doc["len"] for doc in filtered) / total or 1.0
        document_frequency = {}
        for token in token_weights:
            count = 0
            for doc in filtered:
                ids = doc["ids"]
                position = bisect_left(ids, token)
                if position < len(ids) and ids[position] == token:
                    count += 1
            document_frequency[token] = count

        phrases = phrases_of(query)
        normalized_query = phrase_form(query)
        query_moment = normalize_text(query).lower()
        board_priors = {}
        type_boosts = {}
        severity_boosts = {}
        ranked = []
        for doc in filtered:
            ids = doc["ids"]
            counts = doc["counts"]
            score = 0.0
            matched = []
            for token, weight in token_weights.items():
                position = bisect_left(ids, token)
                if position >= len(ids) or ids[position] != token:
                    continue
                frequency = counts[position]
                if not frequency:
                    continue
                df = document_frequency.get(token, 0)
                idf = math.log(1.0 + (total - df + 0.5) / (df + 0.5))
                norm = K1 * (1.0 - B + B * doc["len"] / avgdl)
                score += weight * idf * frequency * (K1 + 1.0) / (frequency + norm)
                matched.append(token)
            if score <= 0:
                continue
            board = str(doc["board"])
            prior = board_priors.get(board)
            if prior is None:
                prior = _board_prior_moment(query_moment, board)
                board_priors[board] = prior
            doc_type = doc["type"]
            type_boost = type_boosts.get(doc_type)
            if type_boost is None:
                type_boost = _type_boost_moment(query_moment, doc_type)
                type_boosts[doc_type] = type_boost
            severity = str(doc["severity"])
            severity_boost = severity_boosts.get(severity)
            if severity_boost is None:
                severity_boost = _severity_boost_moment(query, severity)
                severity_boosts[severity] = severity_boost
            score *= prior * type_boost * severity_boost
            coverage = len(matched) / max(1, len(token_weights))
            score *= 0.55 + 0.45 * coverage
            ranked.append({
                "score": score,
                "doc": doc,
                "matched": matched,
                "coverage": coverage,
                "phrase": "",
            })

        if not ranked:
            return []
        ranked.sort(key=lambda item: -item["score"])

        if read_bodies and phrases:
            for item in ranked[:40]:
                doc = item["doc"]
                position = self._doc_position[id(doc)]
                forms = self._form_cache.get(position)
                if forms is None:
                    body = self._read_body(doc)
                    forms = (
                        phrase_form(doc["title"]),
                        phrase_form(" ".join(str(tag) for tag in doc["tags"])),
                        phrase_form(body),
                    )
                    self._form_cache[position] = forms
                title_form, tags_form, body_form = forms
                best = 1.0
                best_phrase = ""
                for phrase in phrases:
                    form = phrase_form(phrase)
                    if len(form) < 2:
                        continue
                    if form in title_form:
                        bonus = 1.25
                    elif form in tags_form:
                        bonus = 1.14
                    elif form in body_form:
                        bonus = 1.08
                    else:
                        continue
                    if bonus > best:
                        best = bonus
                        best_phrase = phrase
                if best_phrase:
                    item["score"] *= best
                    item["phrase"] = best_phrase
            if normalized_query and len(normalized_query) >= 4:
                for item in ranked[:10]:
                    position = self._doc_position[id(item["doc"])]
                    forms = self._form_cache.get(position)
                    if forms is None:
                        forms = (
                            phrase_form(item["doc"]["title"]),
                            phrase_form(" ".join(str(tag) for tag in item["doc"]["tags"])),
                            phrase_form(self._read_body(item["doc"])),
                        )
                        self._form_cache[position] = forms
                    if normalized_query in forms[2]:
                        item["score"] *= 1.05

        ranked.sort(key=lambda item: -item["score"])
        results = []
        for item in ranked[:80]:
            doc = item["doc"]
            results.append({
                "score": round(item["score"], 3),
                "id": doc["id"],
                "title": doc["title"],
                "path": doc["path"],
                "abs_path": "",
                "tags": doc["tags"],
                "type": doc["type"],
                "stage": doc["stage"],
                "audience": doc["audience"],
                "severity": doc["severity"],
                "board": doc["board"],
                "why": [str(self.terms[token]) for token in item["matched"][:8]],
                "phrase": item["phrase"],
                "coverage": round(item["coverage"], 2),
            })
        if diversify:
            results = _diversify(results, top, per_board=3)
        else:
            results = results[:top]
        kb_root = str(self.kb)
        for result in results:
            if result["path"]:
                result["abs_path"] = os.path.join(kb_root, result["path"])
        return results

    def batch(self, query_specs, top=6, per_query=6, diversify=True):
        merged = {}
        normalized_queries = []
        for spec in query_specs:
            if isinstance(spec, dict):
                query = str(spec.get("query") or "").strip()
                weight = float(spec.get("weight") or 1.0)
                reason = str(spec.get("reason") or "")
            else:
                query = str(spec).strip()
                weight = 1.0
                reason = ""
            if not query:
                continue
            normalized_queries.append({"query": query, "weight": weight, "reason": reason})
            hits = self.search(query, top=per_query, diversify=False)
            if not hits:
                continue
            best = hits[0]["score"] or 1.0
            for hit in hits:
                entry = merged.get(hit["id"])
                if entry is None:
                    entry = dict(hit)
                    entry["matched_queries"] = []
                    entry["merge_score"] = 0.0
                    entry["hits"] = 0
                    merged[hit["id"]] = entry
                entry["merge_score"] += (hit["score"] / best) * weight
                entry["hits"] += 1
                if query not in entry["matched_queries"]:
                    entry["matched_queries"].append(query)
                entry["why"] = list(OrderedDict.fromkeys(entry["why"] + hit["why"]))[:8]
        results = list(merged.values())
        results.sort(key=lambda item: (-item["merge_score"], -item["hits"], -item["score"]))
        for item in results:
            item["score"] = round(item["merge_score"], 3)
        if diversify:
            results = _diversify(results, top, per_board=3)
        else:
            results = results[:top]
        return results, normalized_queries

    def excerpt(self, doc_or_result, query="", max_chars=700, safe=True):
        if isinstance(doc_or_result, dict) and "ids" in doc_or_result:
            doc = doc_or_result
        else:
            path = str(doc_or_result.get("path") or "")
            doc = {"path": path}
        body = self._read_body(doc)
        return extract_excerpt(body, query, max_chars=max_chars, safe=safe)


def _strip_frontmatter(text):
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end >= 0:
            return text[end + 4:]
    return text


def _sections(text):
    text = _strip_frontmatter(text)
    lines = text.splitlines()
    sections = []
    heading = ""
    buffer = []
    in_code = False
    for line in lines:
        if line.strip().startswith("```"):
            in_code = not in_code
            buffer.append(line)
            continue
        match = re.match(r"^(#{1,4})\s+(.+?)\s*$", line)
        if match and not in_code:
            if buffer and any(item.strip() for item in buffer):
                sections.append((heading, "\n".join(buffer)))
            heading = match.group(2).strip()
            buffer = []
            continue
        buffer.append(line)
    if buffer and any(item.strip() for item in buffer):
        sections.append((heading, "\n".join(buffer)))
    return sections


SECTION_PRIORITY = [
    ("可直接使用的话术", 4.0),
    ("话术", 3.0),
    ("怎么回", 3.0),
    ("回复", 2.6),
    ("边界", 2.5),
    ("拒绝", 2.5),
    ("停止", 2.2),
    ("识别信号", 2.4),
    ("识别", 2.0),
    ("判断", 1.8),
    ("做法", 1.8),
    ("步骤", 1.6),
    ("处理", 1.8),
    ("安全", 1.7),
    ("求助", 1.6),
    ("同意", 1.8),
    ("FWB", 1.6),
    ("异地", 1.5),
    ("线上", 1.5),
    ("案例", 0.8),
    ("坏话术", -3.0),
    ("操控话术", -4.0),
    ("PUA", -3.0),
    ("反例", -2.0),
]

UNSAFE_HEADINGS = ("坏话术", "操控话术", "PUA", "反例", "样本", "示范", "不要照说", "识别示例")


def _section_priority(heading):
    priority = 0.5
    for keyword, value in SECTION_PRIORITY:
        if keyword.lower() in heading.lower():
            priority = max(priority, value)
    return priority


def extract_excerpt(text, query="", max_chars=700, safe=True):
    if not text:
        return ""
    query_terms = [token for token in tokenize(query) if token not in STOPWORDS]
    sections = _sections(text)
    if not sections:
        compact = re.sub(r"\n{3,}", "\n\n", text).strip()
        return mask_pii(compact[:max_chars])

    scored = []
    for heading, content in sections:
        if safe and any(word.lower() in heading.lower() for word in UNSAFE_HEADINGS):
            continue
        priority = _section_priority(heading)
        lines = []
        for raw in content.splitlines():
            line = raw.strip()
            if not line or set(line) <= {"-", "|", ":", " "}:
                continue
            if line.startswith("```"):
                continue
            hits = sum(1 for term in query_terms if term in line)
            weight = priority + hits * 0.9
            if line.startswith("|"):
                weight -= 0.6
            if len(line) > 220:
                weight -= 0.4
            lines.append((weight, line))
        for weight, line in lines:
            scored.append((weight, heading, line))
    if not scored:
        compact = re.sub(r"\n{3,}", "\n\n", text).strip()
        return mask_pii(compact[:max_chars])

    scored.sort(key=lambda item: -item[0])
    chosen = []
    used = 0
    seen = set()
    for weight, heading, line in scored:
        if line in seen:
            continue
        label = "【%s】" % heading if heading else ""
        addition = (label + line) if not chosen else "\n" + line
        if used + len(addition) > max_chars and chosen:
            continue
        chosen.append((heading, line))
        seen.add(line)
        used += len(addition)
        if used >= max_chars:
            break
    if not chosen:
        return ""
    output = []
    current_heading = None
    for heading, line in chosen:
        if heading != current_heading:
            if heading:
                output.append("【%s】%s" % (heading, line))
            else:
                output.append(line)
            current_heading = heading
        else:
            output.append(line)
    return mask_pii("\n".join(output))[:max_chars]


def printable(value):
    if isinstance(value, list):
        return ",".join(str(item) for item in value)
    return str(value)
