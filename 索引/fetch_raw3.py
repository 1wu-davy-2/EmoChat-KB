# -*- coding: utf-8 -*-
"""第三轮语料抓取:5 个新 MIT 仓库,ID 续接 raw-075。"""
import io
import os
import re
import tarfile
import urllib.request

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DST = os.path.join(BASE, "00-语料原文")
UA = {"User-Agent": "knowledge-base-builder/1.0"}
REPOS = [
    ("863401402/she-love-me", "她不一样-she-love-me", 978),
    ("cozer-1024/openclaw-relationship-coach", "关系教练-146课", 6),
    ("YXZ1211/junshi-skill", "军师", 5),
    ("aisoftwarely/lianai-fupan", "恋爱复盘", 3),
    ("lgl1996521/love-advise-skill", "恋爱导师-进化心理学", 6),
]
EXCLUDE = (".github/", "evals/", "demos/", "img/", "assets/", "node_modules/")

counter = 74
total = 0
skipped = 0
for repo, short, star in REPOS:
    url = f"https://codeload.github.com/{repo}/tar.gz/HEAD"
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=120) as r:
            data = r.read()
    except Exception as e:
        print(f"[{short}] 下载失败: {e}")
        continue
    tf = tarfile.open(fileobj=io.BytesIO(data), mode="r:gz")
    members = [m for m in tf.getmembers()
               if m.isfile() and m.name.endswith(".md") and "/" in m.name
               and not any(x in m.name for x in EXCLUDE)]
    n = 0
    for m in members:
        path = m.name.split("/", 1)[1]
        text = tf.extractfile(m).read().decode("utf-8", errors="replace")
        if len(text) < 600:
            skipped += 1
            continue
        mt = re.search(r"^#\s+(.+)$", text, re.M)
        title = mt.group(1).strip() if mt else os.path.splitext(os.path.basename(path))[0]
        counter += 1
        n += 1
        out_path = os.path.join(DST, short, *path.split("/"))
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
            f"> 语料原文层:整篇搬运自 MIT 许可仓库 {repo}({star}★),原文路径 `{path}`。\n"
            "> 版权归原仓库作者所有,依据 MIT 许可证复制(保留版权与许可声明)。\n\n"
        )
        with open(out_path, "w", encoding="utf-8", newline="") as f:
            f.write(header + text)
        total += len(header) + len(text)
    print(f"[{short}] 入库 {n} 个 md")

print(f"\n完成:新增 {counter-74} 个文件(raw-075~raw-{counter:03d}),共 {total//1024} KB;跳过 {skipped} 个小文件")
