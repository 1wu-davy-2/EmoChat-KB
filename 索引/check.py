# -*- coding: utf-8 -*-
"""P3 全量校验:文件存在/大小/UTF-8/frontmatter 完整性/ID 唯一性/归属板块。输出问题清单。"""
import os
import re
import sys
import json
from glob import glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOARDS = {
    "00-语料原文": "raw-", "01-核心方法": "method-", "02-话术库": "script-", "03-人群画像": "persona-",
    "04-性格星座": "astro-", "05-场景流程": "scene-", "06-风险与反收割": "risk-",
    "07-操控图谱": "tactic-", "08-书籍要点": "book-", "10-调研报告": "research-",
    "11-亲密与性": "intimacy-",
}
REQUIRED = ["id", "title", "tags", "type", "source", "confidence"]

problems = []
stats = {}
seen_ids = {}
count = 0

for board, prefix in BOARDS.items():
    files = sorted(glob(os.path.join(ROOT, board, "**", "*.md"), recursive=True))
    stats[board] = len(files)
    for path in files:
        count += 1
        rel = os.path.relpath(path, ROOT)
        size = os.path.getsize(path)
        if size < 1024:
            problems.append(f"[大小] {rel} 仅 {size}B (<1KB,卡片条目不完整)")
        elif size < 2048:
            print(f"  [提示] {rel} {size}B(1-2KB,卡片型条目,正常)")
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        except UnicodeDecodeError:
            problems.append(f"[编码] {rel} 非 UTF-8")
            continue
        if not text.startswith("---"):
            problems.append(f"[frontmatter] {rel} 缺少 frontmatter")
            continue
        end = text.find("\n---", 3)
        if end < 0:
            problems.append(f"[frontmatter] {rel} frontmatter 未闭合")
            continue
        fm = {}
        for line in text[4:end].splitlines():
            if ":" in line:
                k, _, v = line.partition(":")
                fm[k.strip()] = v.strip()
        for key in REQUIRED:
            if not fm.get(key):
                problems.append(f"[frontmatter] {rel} 缺字段 {key}")
        fid = fm.get("id", "")
        if not fid.startswith(prefix):
            problems.append(f"[ID前缀] {rel} id={fid} 应以 {prefix} 开头")
        if fid in seen_ids:
            problems.append(f"[ID重复] {rel} 与 {seen_ids[fid]} 重复 id={fid}")
        else:
            seen_ids[fid] = rel
        if not re.match(r"^[a-z]+-\d{3}", fid):
            problems.append(f"[ID格式] {rel} id={fid} 不符合 {{前缀}}-{{三位数字}}")

print(f"总条目: {count}")
for b, n in stats.items():
    print(f"  {b}: {n}")
print()
if problems:
    print(f"问题 {len(problems)} 个:")
    for p in problems:
        print(" ", p)
    sys.exit(1)
else:
    print("校验通过:无问题。")
