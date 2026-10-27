# -*- coding: utf-8 -*-
"""校验构建产物：结构、frontmatter、索引完整性、链接与检索。"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent
ROOT = SKILL_DIR.parent
DIST = SKILL_DIR / "dist"
PRIVATE = DIST / "emochat-private"
PUBLIC = DIST / "emochat-public"

CARD_ID = re.compile(
    r"\b(?:raw|method|script|persona|astro|scene|risk|tactic|book|research|intimacy|user)-\d{3}\b"
)
MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
PLACEHOLDER = re.compile(r"\{\{[A-Z_]+\}\}")

SEARCH_CASES = [
    ("FWB 谁付出多 情绪劳动 公平", {"method-140"}),
    ("视频亲密 录屏 停止", {"script-153", "intimacy-041"}),
    ("异地网恋 奔现", {"method-141", "scene-048"}),
    ("语音克隆 冒充 转账", {"risk-049"}),
]


def parse_frontmatter(text):
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    meta = {}
    for line in text[4:end].splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip().strip('"').strip("'")
    return meta


def fail(failures, message):
    failures.append(message)


def check_frontmatter(base, expected_name, failures):
    path = base / "SKILL.md"
    if not path.is_file():
        fail(failures, f"{base.name}: 缺少 SKILL.md")
        return
    meta = parse_frontmatter(path.read_text(encoding="utf-8"))
    if meta.get("name") != expected_name:
        fail(failures, f"{base.name}: name 应为 {expected_name}，实际 {meta.get('name')!r}")
    description = meta.get("description", "")
    if not description:
        fail(failures, f"{base.name}: description 为空")
    elif len(description) > 1024:
        fail(failures, f"{base.name}: description 超过 1024 字符 ({len(description)})")
    if "18+" not in path.read_text(encoding="utf-8"):
        fail(failures, f"{base.name}: SKILL.md 未声明 18+")


def check_links(base, failures):
    for path in base.rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        for target in MARKDOWN_LINK.findall(text):
            target = target.split("#", 1)[0].strip()
            if not target or target.startswith(("http://", "https://", "mailto:")):
                continue
            if target.startswith("<") and target.endswith(">"):
                target = target[1:-1]
            if target.startswith("/") or target.startswith("$"):
                continue
            if not (path.parent / target).exists():
                fail(failures, f"{path.relative_to(base)}: 坏链 {target}")


def check_placeholders(base, failures):
    for suffix in ("*.md", "*.json"):
        for path in base.rglob(suffix):
            text = path.read_text(encoding="utf-8")
            for placeholder in set(PLACEHOLDER.findall(text)):
                fail(failures, f"{path.relative_to(base)}: 未替换占位符 {placeholder}")


def check_private(entries, failures):
    if not PRIVATE.is_dir():
        fail(failures, "私有完整版未构建，请先运行 python skill/build.py")
        return
    check_frontmatter(PRIVATE, "emochat", failures)

    for required in [
        "references/index.md",
        "references/board-01.md",
        "references/entry-map.json",
        "scripts/emochat_search.py",
        "adapters/installation.md",
        "adapters/AGENTS.md",
        "adapters/prompt-pack.md",
        "NOTICE.md",
        "LICENSE.txt",
    ]:
        if not (PRIVATE / required).is_file():
            fail(failures, f"私有版缺少 {required}")

    board_rows = []
    for path in sorted((PRIVATE / "references").glob("board-*.md")):
        for line in path.read_text(encoding="utf-8").splitlines():
            match = re.match(r"\| `([a-z]+-\d{3})` \|", line)
            if match:
                board_rows.append(match.group(1))
    expected_ids = {entry["id"] for entry in entries}
    if len(board_rows) != len(entries):
        fail(failures, f"私有版板块索引行数 {len(board_rows)}，应为 {len(entries)}")
    if set(board_rows) != expected_ids:
        missing = sorted(expected_ids - set(board_rows))[:5]
        extra = sorted(set(board_rows) - expected_ids)[:5]
        fail(failures, f"私有版板块索引 ID 不一致，缺失 {missing}，多出 {extra}")

    entry_map_path = PRIVATE / "references" / "entry-map.json"
    if entry_map_path.is_file():
        entry_map = json.loads(entry_map_path.read_text(encoding="utf-8"))
        if len(entry_map) != len(entries):
            fail(failures, f"entry-map.json 条目数 {len(entry_map)}，应为 {len(entries)}")

    manifest_path = PRIVATE / "manifest.json"
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("total") != len(entries):
            fail(failures, f"manifest total {manifest.get('total')}，应为 {len(entries)}")

    check_links(PRIVATE, failures)
    check_placeholders(PRIVATE, failures)

    script = PRIVATE / "scripts" / "emochat_search.py"
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    for query, expected in SEARCH_CASES:
        result = subprocess.run(
            [sys.executable, str(script), query, "--top", "5", "--json", "--kb", str(ROOT)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
        )
        if result.returncode != 0:
            fail(failures, f"检索失败: {query}\n{result.stderr.strip()}")
            continue
        try:
            hits = json.loads(result.stdout)
        except json.JSONDecodeError:
            fail(failures, f"检索输出不是 JSON: {query}")
            continue
        ids = {hit["id"] for hit in hits}
        if not (ids & expected):
            fail(failures, f"检索 {query!r} 未命中 {sorted(expected)}，实际 {sorted(ids)}")


def check_public(failures):
    if not PUBLIC.is_dir():
        fail(failures, "公开框架版未构建，请先运行 python skill/build.py")
        return
    check_frontmatter(PUBLIC, "emochat-framework", failures)

    for required in [
        "references/index.md",
        "references/playbook-chat.md",
        "references/playbook-risk.md",
        "references/playbook-intimacy.md",
        "references/playbook-crisis.md",
        "references/safety-boundaries.md",
        "references/output-templates.md",
        "references/kb-integration.md",
        "scripts/emochat_search.py",
        "adapters/prompt-pack.md",
        "NOTICE.md",
    ]:
        if not (PUBLIC / required).is_file():
            fail(failures, f"公开版缺少 {required}")

    if list((PUBLIC / "references").glob("board-*.md")):
        fail(failures, "公开版不应包含 board-*.md")
    if (PUBLIC / "references" / "entry-map.json").exists():
        fail(failures, "公开版不应包含 entry-map.json")

    for suffix in ("*.md", "*.json", "*.py"):
        for path in PUBLIC.rglob(suffix):
            text = path.read_text(encoding="utf-8")
            match = CARD_ID.search(text)
            if match:
                fail(failures, f"公开版 {path.relative_to(PUBLIC)} 含卡片 ID {match.group(0)}")

    notice = (PUBLIC / "NOTICE.md").read_text(encoding="utf-8") if (PUBLIC / "NOTICE.md").exists() else ""
    if "不包含" not in notice:
        fail(failures, "公开版 NOTICE 未声明不包含知识库正文")

    check_links(PUBLIC, failures)
    check_placeholders(PUBLIC, failures)

    prompt_pack = (PUBLIC / "adapters" / "prompt-pack.md").read_text(encoding="utf-8")
    for section in ["先做三件事", "输出格式", "硬边界", "求助渠道"]:
        if section not in prompt_pack:
            fail(failures, f"公开版 prompt-pack 缺少章节: {section}")


def main():
    if not (ROOT / "索引" / "metadata.json").is_file():
        print("找不到 索引/metadata.json", file=sys.stderr)
        return 1
    entries = json.loads((ROOT / "索引" / "metadata.json").read_text(encoding="utf-8"))
    failures = []
    check_private(entries, failures)
    check_public(failures)
    if failures:
        print(f"校验失败：{len(failures)} 项")
        for message in failures:
            print(f"- {message}")
        return 1
    print(f"校验通过：私有版 {len(entries)} 条；公开版仅框架；检索 {len(SEARCH_CASES)} 例命中。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
