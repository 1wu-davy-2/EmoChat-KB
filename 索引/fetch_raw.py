# -*- coding: utf-8 -*-
"""批量抓取 MIT 仓库原文,写入 知识库/00-语料原文/,每份加 YAML 溯源头。"""
import json
import os
import re
import urllib.request
from urllib.parse import quote

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DST = os.path.join(BASE, "00-语料原文")
UA = {"User-Agent": "knowledge-base-builder/1.0"}
REPOS = [
    # (owner/repo, 短名, 要抓的路径前缀列表)
    ("shengjidaguai-china/goutoujunshi", "狗头军师", ["references/knowledge/", "references/practical/"]),
    ("tomwong001/qingsheng-skill", "情圣", ["skill/"]),
    ("Mayuqi-crypto/HowToGetAlongWithGirls", "HowToGetAlongWithGirls", [""]),
]

def get(url, binary=False):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    return data if binary else data.decode("utf-8", errors="replace")

counter = 0
total_bytes = 0
skipped = []
for repo, short, prefixes in REPOS:
    tree = json.loads(get(f"https://api.github.com/repos/{repo}/git/trees/HEAD?recursive=1"))
    files = [e["path"] for e in tree["tree"]
             if e["type"] == "blob" and e["path"].endswith(".md")
             and any(e["path"].startswith(p) for p in prefixes)
             and "evals/" not in e["path"]]
    print(f"[{short}] 待抓 {len(files)} 个文件")
    for path in files:
        url = f"https://raw.githubusercontent.com/{repo}/HEAD/" + quote(path)
        try:
            text = get(url)
        except Exception as e:
            skipped.append((repo, path, str(e)))
            continue
        if len(text) < 600:
            skipped.append((repo, path, "太小跳过"))
            continue
        m = re.search(r"^#\s+(.+)$", text, re.M)
        title = m.group(1).strip() if m else os.path.splitext(os.path.basename(path))[0]
        counter += 1
        rel = f"{short}/{path}"
        out_path = os.path.join(DST, *rel.split("/"))
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        header = (
            "---\n"
            f"id: raw-{counter:03d}\n"
            f"title: {title}\n"
            f"tags: [语料原文, {short}]\n"
            "type: 语料原文\n"
            f'source: "https://github.com/{repo} (blob/HEAD/{path})"\n'
            "license: MIT\n"
            "confidence: 中\n"
            "---\n\n"
            f"> 语料原文层:整篇搬运自 MIT 许可仓库 {repo},原文路径 `{path}`。\n"
            "> 版权归原仓库作者所有,依据 MIT 许可证复制(保留版权与许可声明,全文见仓库 LICENSE)。\n\n"
        )
        with open(out_path, "w", encoding="utf-8", newline="") as f:
            f.write(header + text)
        total_bytes += len(header) + len(text)

print(f"\n完成:{counter} 个原文文件,共 {total_bytes//1024} KB")
if skipped:
    print(f"跳过 {len(skipped)} 个:")
    for r, p, why in skipped[:20]:
        print(f"  {r} {p} -- {why}")
