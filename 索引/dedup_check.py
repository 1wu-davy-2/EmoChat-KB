# -*- coding: utf-8 -*-
"""P3 交叉查重:对知识库条目两两计算 8 元字符组的 Jaccard 相似度,报告 >0.15 的文件对。"""
import os
import re
from glob import glob
from itertools import combinations

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOARDS = ["00-语料原文", "01-核心方法", "02-话术库", "03-人群画像", "04-性格星座",
          "05-场景流程", "06-风险与反收割", "07-操控图谱", "08-书籍要点", "10-调研报告",
          "11-亲密与性"]


def shingles(text, n=8):
    text = re.sub(r"\s+", "", text)
    return {text[i:i + n] for i in range(max(0, len(text) - n + 1))}


entries = []
for b in BOARDS:
    for path in glob(os.path.join(ROOT, b, "**", "*.md"), recursive=True):
        with open(path, encoding="utf-8") as f:
            entries.append((os.path.relpath(path, ROOT), shingles(f.read())))

pairs = []
for (na, sa), (nb, sb) in combinations(entries, 2):
    if not sa or not sb:
        continue
    inter = len(sa & sb)
    union = len(sa | sb)
    j = inter / union if union else 0
    if j > 0.15:
        pairs.append((j, na, nb))

pairs.sort(reverse=True)
print(f"对比文件对数: {len(entries)*(len(entries)-1)//2}")
if pairs:
    print(f"高相似对 (>0.15) {len(pairs)} 个:")
    for j, na, nb in pairs:
        print(f"  {j:.2f}  {na}  <->  {nb}")
else:
    print("无 >0.15 的重复对,查重通过。")
