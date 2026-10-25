# -*- coding: utf-8 -*-
"""11-亲密与性 板块检索冒烟测试。"""
import importlib.util
import os

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("search_mod", os.path.join(HERE, "search.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

for q, expect in [
    ("性需求沟通", "intimacy-"),
    ("安全词", "intimacy-"),
    ("裸聊敲诈", "intimacy-"),
    ("性癖好正常吗", "intimacy-"),
]:
    rs = mod.search(q, top=3)
    hit = any(r["id"].startswith(expect) for r in rs)
    top = rs[0] if rs else None
    print(("PASS" if hit else "FAIL"), q, "->", (top["id"] + " " + top["title"]) if top else "NONE")
