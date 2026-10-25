# -*- coding: utf-8 -*-
"""把 调研/*.md 挂入知识库 10-调研报告/ 层(本地自产内容,加溯源头)。"""
import os
import re

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.dirname(BASE) + os.sep + "调研"
DST = os.path.join(BASE, "10-调研报告")

n = 0
for name in sorted(os.listdir(SRC)):
    if not name.endswith(".md"):
        continue
    with open(os.path.join(SRC, name), encoding="utf-8") as f:
        text = f.read()
    m = re.search(r"^#\s+(.+)$", text, re.M)
    title = m.group(1).strip() if m else name[:-3]
    n += 1
    header = (
        "---\n"
        f"id: research-{n:03d}\n"
        f"title: {title}\n"
        f"tags: [调研长文]\n"
        "type: 调研长文\n"
        f'source: "本地调研笔记 调研/{name}(含全部来源URL)"\n'
        "confidence: 高\n"
        "---\n\n"
        "> 调研长文层:知识库建库过程的原始调研报告,含完整来源链接,供深度检索与溯源。\n\n"
    )
    with open(os.path.join(DST, f"research-{n:03d}.md"), "w", encoding="utf-8", newline="") as f:
        f.write(header + text)
print(f"挂入 {n} 份调研长文")
