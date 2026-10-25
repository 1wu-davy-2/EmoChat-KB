# -*- coding: utf-8 -*-
"""P4:扫描全部条目 frontmatter,生成 索引/metadata.json。"""
import os
import json
from glob import glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOARDS = ["00-语料原文", "01-核心方法", "02-话术库", "03-人群画像", "04-性格星座",
          "05-场景流程", "06-风险与反收割", "07-操控图谱", "08-书籍要点", "10-调研报告"]


def parse(text):
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
        k, _, v = line.partition(":")
        k, v = k.strip(), v.strip()
        if v.startswith("[") and v.endswith("]"):
            v = [x.strip().strip('"').strip("'") for x in v[1:-1].split(",") if x.strip()]
        meta[k] = v
    return meta


out = []
for b in BOARDS:
    for path in sorted(glob(os.path.join(ROOT, b, "**", "*.md"), recursive=True)):
        with open(path, encoding="utf-8") as f:
            meta = parse(f.read())
        meta["board"] = b
        meta["file"] = os.path.relpath(path, ROOT).replace("\\", "/")
        out.append(meta)

dst = os.path.join(ROOT, "索引", "metadata.json")
with open(dst, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)

ids = [e.get("id") for e in out]
print(f"metadata.json 写入 {len(out)} 条 -> {dst}")
print(f"ID 唯一性: {len(ids)} == {len(set(ids))} -> {len(ids)==len(set(ids))}")
stats = {}
for e in out:
    stats[e["board"]] = stats.get(e["board"], 0) + 1
for k in sorted(stats):
    print(f"  {k}: {stats[k]}")
