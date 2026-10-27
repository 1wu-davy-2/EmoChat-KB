# -*- coding: utf-8 -*-
"""EmoChat-KB 便携检索（零依赖，BM25 风格评分）。

用法:
    python emochat_search.py "查询词"
    python emochat_search.py "查询词" --top 5
    python emochat_search.py "查询词" --tag 话术示例
    python emochat_search.py "查询词" --board 06
    python emochat_search.py "查询词" --json
    python emochat_search.py "查询词" --kb /path/to/EmoChat-KB

知识库路径优先级: --kb > EMOCHAT_KB 环境变量 > 从脚本位置向上查找
包含 索引/metadata.json 的目录。
"""
import argparse
import json
import math
import os
import re
import sys
from collections import Counter
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except (OSError, ValueError):
            pass


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
    for candidate in [here.parent, *here.parents]:
        try:
            candidate = candidate.resolve()
        except OSError:
            continue
        if is_kb(candidate):
            return candidate
    return None


def tokenize(text):
    tokens = []
    for word in re.findall(r"[A-Za-z0-9]+", text.lower()):
        tokens.append(word)
    for segment in re.findall(r"[\u4e00-\u9fff]+", text):
        if len(segment) == 1:
            tokens.append(segment)
        for i in range(len(segment) - 1):
            tokens.append(segment[i:i + 2])
    return tokens


def load_entries(kb):
    metadata_path = kb / "索引" / "metadata.json"
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SystemExit(f"无法读取 metadata: {metadata_path}\n{exc}")
    if not isinstance(metadata, list):
        raise SystemExit(f"metadata.json 应为数组: {metadata_path}")

    entries = []
    for item in metadata:
        if not isinstance(item, dict):
            continue
        relative = str(item.get("file") or "").replace("\\", "/")
        body = ""
        if relative:
            path = kb / relative
            try:
                body = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                body = ""
        title = str(item.get("title") or "")
        tags = item.get("tags") or []
        audience = item.get("audience") or []
        stage = item.get("stage") or []
        tags_text = " ".join(tags) if isinstance(tags, list) else str(tags)
        audience_text = " ".join(audience) if isinstance(audience, list) else str(audience)
        stage_text = " ".join(stage) if isinstance(stage, list) else str(stage)
        tokens = tokenize(
            title * 3 + " " + tags_text * 2 + " " + audience_text + " "
            + stage_text + " " + str(item.get("type") or "") + " " + body
        )
        entries.append({
            "id": str(item.get("id") or "?"),
            "title": title,
            "path": relative,
            "abs_path": str((kb / relative).resolve()) if relative else "",
            "tags": tags,
            "type": item.get("type") or "",
            "stage": stage,
            "audience": audience,
            "severity": item.get("severity") or "",
            "board": str(item.get("board") or ""),
            "tf": Counter(tokens),
        })
    return entries


def search(entries, query, top=8, tag=None, board=None):
    filtered = entries
    if tag:
        filtered = [
            entry for entry in filtered
            if tag in str(entry["tags"]) or tag == entry["type"]
            or tag in str(entry["audience"])
        ]
    if board:
        filtered = [
            entry for entry in filtered
            if entry["board"].startswith(board)
            or entry["path"].startswith(board)
        ]
    query_tokens = tokenize(query)
    if not query_tokens or not filtered:
        return []

    document_frequency = {}
    for entry in filtered:
        for token in set(query_tokens):
            if token in entry["tf"]:
                document_frequency[token] = document_frequency.get(token, 0) + 1

    total = len(filtered)
    results = []
    for entry in filtered:
        score = 0.0
        for token in query_tokens:
            frequency = entry["tf"].get(token, 0)
            if not frequency:
                continue
            df = document_frequency.get(token, 0)
            idf = math.log(1 + (total - df + 0.5) / (df + 0.5))
            score += idf * frequency / (frequency + 1.2)
        if score > 0:
            results.append({
                "score": round(score, 3),
                "id": entry["id"],
                "title": entry["title"],
                "path": entry["path"],
                "abs_path": entry["abs_path"],
                "tags": entry["tags"],
                "type": entry["type"],
                "stage": entry["stage"],
                "audience": entry["audience"],
                "severity": entry["severity"],
            })
    results.sort(key=lambda result: -result["score"])
    return results[:top]


def printable(value):
    if isinstance(value, list):
        return ",".join(str(item) for item in value)
    return str(value)


def main():
    parser = argparse.ArgumentParser(description="EmoChat-KB 便携检索")
    parser.add_argument("query", nargs="?", help="查询词")
    parser.add_argument("--top", type=int, default=8, help="返回条数，默认 8")
    parser.add_argument("--tag", help="按标签/类型/受众过滤")
    parser.add_argument("--board", help="按板块前缀过滤，如 06")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    parser.add_argument("--kb", help="知识库根目录")
    args = parser.parse_args()

    if not args.query:
        parser.print_help()
        return 1

    kb = resolve_kb(args.kb)
    if kb is None:
        message = (
            "找不到 EmoChat-KB。请用 --kb 指定仓库根目录，"
            "或设置 EMOCHAT_KB 环境变量。"
        )
        if args.json:
            print(json.dumps({"error": message}, ensure_ascii=False, indent=2))
        else:
            print(message, file=sys.stderr)
        return 2

    entries = load_entries(kb)
    results = search(entries, args.query, max(1, args.top), args.tag, args.board)

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 0
    if not results:
        print("(无匹配结果)")
        return 0
    for result in results:
        print(f"[{result['score']:>6.2f}] {result['id']}  {result['title']}")
        print(f"          path: {result['path']}")
        print(f"          abs:  {result['abs_path']}")
        print(
            f"          tags: {printable(result['tags'])} | type: {result['type']}"
            f" | stage: {printable(result['stage'])}"
        )
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
