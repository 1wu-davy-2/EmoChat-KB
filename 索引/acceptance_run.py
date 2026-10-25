# -*- coding: utf-8 -*-
"""P5 验收:10 条测试 query 检索验证。每条 query 断言期望板块命中 top3。"""
import importlib.util
import os

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(os.path.join(HERE, "search_mod.py"), os.path.join(HERE, "search.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

CASES = [
    ("她是大学生 怎么开场", ["03-人群画像", "02-话术库", "00-语料原文", "10-调研报告"]),
    ("对方总暗示买东西要礼物 怎么办", ["06-风险与反收割", "00-语料原文", "10-调研报告"]),
    ("推拉是什么 怎么破解", ["07-操控图谱", "00-语料原文/狗头军师", "10-调研报告"]),
    ("依恋类型 怎么判断 聊天", ["08-书籍要点", "01-核心方法", "00-语料原文", "10-调研报告"]),
    ("聊天冷场 急救", ["01-核心方法", "02-话术库", "00-语料原文"]),
    ("约女生出来 被拒绝了 怎么接", ["05-场景流程", "00-语料原文", "01-核心方法"]),
    ("白羊座 雷区", ["04-性格星座", "10-调研报告"]),
    ("杀猪盘 识别 话术", ["06-风险与反收割", "10-调研报告"]),
    ("女生说晚安 怎么回", ["02-话术库", "00-语料原文", "05-场景流程"]),
    ("煤气灯 被说想太多", ["07-操控图谱", "10-调研报告", "00-语料原文"]),
]

ok = 0
for q, expect in CASES:
    rs = mod.search(q, top=3)
    hit = any(any(r["path"].startswith(e) for e in expect) for r in rs)
    ok += hit
    print(f"{'PASS' if hit else 'FAIL'}  {q}")
    for r in rs:
        print(f"      {r['score']:6.2f}  {r['id']}  {r['title']}  ({r['path']})")
    print()

print(f"命中 {ok}/{len(CASES)}")
