# -*- coding: utf-8 -*-
"""方案B:下载整仓 tar.gz(codeload,不吃 API 限额),解包提取全部 md 原文。"""
import io
import os
import re
import tarfile
import urllib.request

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DST = os.path.join(BASE, "00-语料原文")
UA = {"User-Agent": "knowledge-base-builder/1.0"}
REPOS = [
    ("shengjidaguai-china/goutoujunshi", "狗头军师", ["references/knowledge/", "references/practical/"]),
    ("tomwong001/qingsheng-skill", "情圣", ["skill/"]),
    ("Mayuqi-crypto/HowToGetAlongWithGirls", "HowToGetAlongWithGirls", [""]),
]

counter = 0
total_bytes = 0
skipped = []
for repo, short, prefixes in REPOS:
    url = f"https://codeload.github.com/{repo}/tar.gz/HEAD"
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=120) as r:
        data = r.read()
    print(f"[{short}] tarball {len(data)//1024} KB")
    tf = tarfile.open(fileobj=io.BytesIO(data), mode="r:gz")
    members = [m for m in tf.getmembers()
               if m.isfile() and m.name.endswith(".md")
               and "/" in m.name
               and any(m.name.split("/", 1)[1].startswith(p) for p in prefixes)
               and "evals/" not in m.name]
    print(f"[{short}] 命中 {len(members)} 个 md")
    for m in members:
        path = m.name.split("/", 1)[1]  # 去掉根目录前缀
        text = tf.extractfile(m).read().decode("utf-8", errors="replace")
        if len(text) < 600:
            skipped.append((repo, path, "太小跳过"))
            continue
        mt = re.search(r"^#\s+(.+)$", text, re.M)
        title = mt.group(1).strip() if mt else os.path.splitext(os.path.basename(path))[0]
        counter += 1
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
            f"> 语料原文层:整篇搬运自 MIT 许可仓库 {repo},原文路径 `{path}`。\n"
            "> 版权归原仓库作者所有,依据 MIT 许可证复制(保留版权与许可声明,全文见仓库 LICENSE)。\n\n"
        )
        with open(out_path, "w", encoding="utf-8", newline="") as f:
            f.write(header + text)
        total_bytes += len(header) + len(text)

print(f"\n完成:{counter} 个原文文件,共 {total_bytes//1024} KB")
if skipped:
    print(f"跳过 {len(skipped)} 个(过小或非内容)")
