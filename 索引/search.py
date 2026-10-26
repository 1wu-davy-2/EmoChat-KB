# -*- coding: utf-8 -*-
"""
情感聊天知识库 · 零依赖关键词检索脚本(BM25 风格评分)
用法:
    python search.py "查询词"                 # 默认返回 top 8
    python search.py "查询词" --top 5
    python search.py "查询词" --tag 话术示例
    python search.py "查询词" --json           # 机器可读输出
"""
import os
import re
import sys
import json
import math
from glob import glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 知识库/
BOARDS = ["00-语料原文", "01-核心方法", "02-话术库", "03-人群画像", "04-性格星座",
          "05-场景流程", "06-风险与反收割", "07-操控图谱", "08-书籍要点", "10-调研报告",
          "11-亲密与性", "12-用户侧画像"]


def parse_frontmatter(text):
    """解析简单 YAML frontmatter(key: value / key: [a, b]),失败返回空 dict。"""
    meta = {}
    if not text.startswith("---"):
        return meta
    end = text.find("\n---", 3)
    if end < 0:
        return meta
    for line in text[4:end].splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if val.startswith("[") and val.endswith("]"):
            val = [v.strip().strip('"').strip("'") for v in val[1:-1].split(",") if v.strip()]
        meta[key] = val
    return meta


def tokenize(s):
    """中文按单字+二元组切分,英文/数字按词切分。"""
    tokens = []
    for w in re.findall(r"[A-Za-z0-9]+", s.lower()):
        tokens.append(w)
    cjk = re.findall(r"[\u4e00-\u9fff]+", s)
    for seg in cjk:
        if len(seg) == 1:
            tokens.append(seg)
        for i in range(len(seg) - 1):
            tokens.append(seg[i:i + 2])
    return tokens


def load_entries():
    entries = []
    for board in BOARDS:
        for path in glob(os.path.join(ROOT, board, "**", "*.md"), recursive=True):
            try:
                with open(path, encoding="utf-8") as f:
                    text = f.read()
            except Exception:
                continue
            meta = parse_frontmatter(text)
            body = text
            entries.append({
                "path": os.path.relpath(path, ROOT).replace("\\", "/"),
                "meta": meta,
                "title": str(meta.get("title", os.path.basename(path))),
                "tokens": tokenize(
                    str(meta.get("title", "")) * 3
                    + " " + str(meta.get("tags", "")) * 2
                    + " " + str(meta.get("audience", "")) + " " + str(meta.get("stage", ""))
                    + " " + text),
            })
    return entries


def search(query, top=8, tag=None):
    entries = load_entries()
    if tag:
        entries = [e for e in entries if tag in str(e["meta"].get("tags", ""))
                   or tag in str(e["meta"].get("type", ""))
                   or tag in str(e["meta"].get("audience", ""))]
    qtokens = tokenize(query)
    if not qtokens:
        return []
    # 文档频率
    df = {}
    for e in entries:
        for t in set(qtokens):
            if t in e["tokens"]:
                df[t] = df.get(t, 0) + 1
    n = len(entries)
    results = []
    for e in entries:
        score = 0.0
        for t in qtokens:
            tf = e["tokens"].count(t)
            if tf == 0:
                continue
            idf = math.log(1 + (n - df.get(t, 0) + 0.5) / (df.get(t, 0) + 0.5))
            score += idf * tf / (tf + 1.2)
        if score > 0:
            results.append({"score": round(score, 3), "id": e["meta"].get("id", "?"),
                            "title": e["title"], "path": e["path"],
                            "tags": e["meta"].get("tags", []),
                            "type": e["meta"].get("type", "?"),
                            "audience": e["meta"].get("audience", []),
                            "stage": e["meta"].get("stage", [])})
    results.sort(key=lambda r: -r["score"])
    return results[:top]


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return
    query = args[0]
    top, tag, as_json = 8, None, False
    i = 1
    while i < len(args):
        if args[i] == "--top":
            top = int(args[i + 1]); i += 2
        elif args[i] == "--tag":
            tag = args[i + 1]; i += 2
        elif args[i] == "--json":
            as_json = True; i += 1
        else:
            i += 1
    results = search(query, top, tag)
    if as_json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    elif not results:
        print("(无匹配结果)")
    else:
        for r in results:
            print(f"[{r['score']:>6.2f}] {r['id']}  {r['title']}")
            print(f"          {r['path']}")
            tags = r.get("tags")
            if isinstance(tags, list):
                t = ",".join(tags)
            else:
                t = str(tags)
            print(f"          tags: {t} | type: {r['type']}")
            print()


if __name__ == "__main__":
    main()
