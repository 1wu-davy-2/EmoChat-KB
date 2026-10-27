# -*- coding: utf-8 -*-
"""构建 EmoChat 技能包：私有完整版 + 公开框架版。"""
import json
import re
import shutil
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent
ROOT = SKILL_DIR.parent
SRC = SKILL_DIR / "src"
DIST = SKILL_DIR / "dist"

BOARDS = [
    ("00-语料原文", "MIT 原始语料，适合查早期话术与风格；引用时保留出处与 MIT 许可。"),
    ("01-核心方法", "沟通方法、边界、冲突、长期关系、关系决策。"),
    ("02-话术库", "可复用话术、拒绝、边界、邀约、修复、性沟通。"),
    ("03-人群画像", "基础人群与处境画像。"),
    ("04-性格星座", "MBTI/DISC/九型/星座等沟通参考（娱乐化，不是诊断）。"),
    ("05-场景流程", "从初识到分手、异地、见家长、同居等流程。"),
    ("06-风险与反收割", "诈骗、隐私、经济控制、跟踪、暴力、影像等风险。"),
    ("07-操控图谱", "操控战术识别、案例、AI 判定与反制。"),
    ("08-书籍要点", "书籍原创摘要与阅读路线。"),
    ("10-调研报告", "建库调研长文与来源 URL。"),
    ("11-亲密与性", "18+ 同意、性健康、沟通与影像安全。"),
    ("12-用户侧画像", "用户偏好、边界、关系结构、媒介偏好。"),
]

COMMON_REFERENCES = [
    "playbook-chat.md",
    "playbook-risk.md",
    "playbook-intimacy.md",
    "playbook-crisis.md",
    "safety-boundaries.md",
    "output-templates.md",
    "kb-integration.md",
]

COMMON_ADAPTERS = [
    "AGENTS.md",
    "installation.md",
    "prompt-pack.md",
]

PRIVATE_KB_SECTION = """## 检索知识库（私有完整版）

本版随包提供 589 条卡片的板块索引（`references/board-*.md`）。不要一次读完整个知识库，按以下顺序按需取用：

1. 运行 `python scripts/emochat_search.py "关键词" --top 5`，用 2-4 组不同关键词检索。
2. 读取排名最高的 3-5 张卡片，核对 `audience / stage / severity` 是否匹配。
3. 需要浏览板块时，先读对应 `board-*.md` 的索引表，再按 `path` 读取原文。
4. 引用时写清卡片 ID 与标题；公开案例与合成案例要区分，坏话术只用于识别。

脚本找不到知识库时，先询问用户仓库路径，再设置 `EMOCHAT_KB` 或传 `--kb`。不要猜测路径，也不要把整库内容复制进回答。"""

PUBLIC_KB_SECTION = """## 使用方式（公开框架版）

本版不包含知识库正文、案例、话术或卡片索引。若你有一份自己的 EmoChat-KB 副本，设置 `EMOCHAT_KB` 指向仓库根目录，技能会通过 `scripts/emochat_search.py` 检索；没有副本时，使用内置 playbooks 做通用分析。不要声称检索了未提供的资料；引用时标明“内置框架”或“用户提供的材料”。"""

PRIVATE_SEARCH_HINT = """## 检索

本版随包提供 589 条卡片索引（`board-*.md`）。优先运行 `python scripts/emochat_search.py "关键词" --top 5`；需要浏览板块时再读对应索引。"""

PUBLIC_SEARCH_HINT = """## 检索

本版不含卡片索引。如你有自己的同结构知识库，设置 `EMOCHAT_KB` 后运行 `python scripts/emochat_search.py ...`；否则使用本包的 playbooks。"""


def render(text, values):
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def copy_file(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)


def load_metadata():
    path = ROOT / "索引" / "metadata.json"
    entries = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(entries, list):
        raise SystemExit("索引/metadata.json 应为数组")
    return entries


def natural_key(entry):
    match = re.match(r"([a-zA-Z]+)-(\d+)", str(entry.get("id", "")))
    if match:
        return (match.group(1), int(match.group(2)))
    return (str(entry.get("id", "")), 0)


def cell(value):
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def joined(value):
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return str(value or "")


def copy_common(target):
    for name in COMMON_REFERENCES:
        copy_file(SRC / "references" / name, target / "references" / name)
    copy_file(SRC / "scripts" / "emochat_search.py", target / "scripts" / "emochat_search.py")
    for name in COMMON_ADAPTERS:
        source = SRC / "adapters" / name
        if name == "prompt-pack.md":
            text = source.read_text(encoding="utf-8")
            text = render(text, {"EDITION_NOTICE": edition_notice_for(target.name)})
            write(target / "adapters" / name, text)
        else:
            copy_file(source, target / "adapters" / name)


def edition_notice_for(dist_name):
    if dist_name == "emochat-private":
        return "> 版本：私有完整版（v13，589 条卡片）。仅供仓库作者本地/私有环境使用；不得向第三方分发、上传公共平台或用于对外服务。"
    return "> 版本：公开框架版。包含分析流程、边界与输出模板，不含 EmoChat-KB 的 589 条知识库正文、案例、话术或卡片索引。"


def build_index(target, board_table, search_hint, notice):
    template = (SRC / "references" / "index.md").read_text(encoding="utf-8")
    text = render(template, {
        "BOARD_TABLE": board_table,
        "SEARCH_HINT": search_hint,
        "EDITION_NOTICE": notice,
    })
    write(target / "references" / "index.md", text)


def private_board_table(entries):
    counts = {}
    for entry in entries:
        counts[entry.get("board", "")] = counts.get(entry.get("board", ""), 0) + 1
    lines = ["| 板块 | 条目数 | 用途 | 索引 |", "|---|---|---|---|"]
    for board, purpose in BOARDS:
        if counts.get(board, 0) == 0:
            continue
        lines.append(
            f"| {board} | {counts[board]} | {purpose} | "
            f"[board-{board[:2]}.md](board-{board[:2]}.md) |"
        )
    return "\n".join(lines)


def public_board_table():
    lines = ["| 类别 | 用途 |", "|---|---|"]
    rows = [
        ("沟通方法", "开场、接话、热聊、邀约、冲突修复、长期关系与关系决策。"),
        ("话术与边界", "表达需求、拒绝、设限、停止、退出、道歉与修复。"),
        ("人群与阶段", "不同人群、关系阶段与处境下的沟通差异。"),
        ("场景流程", "从初识到分手、异地、见家长、同居等关键流程。"),
        ("风险与反收割", "诈骗、经济控制、隐私、跟踪、暴力与影像风险。"),
        ("操控识别", "PUA、爱轰炸、冷暴力、威胁、孤立等模式识别。"),
        ("亲密与同意", "18+ 同意、性沟通、语音/视频、私密影像与性健康。"),
        ("用户侧画像", "用户偏好、边界、关系结构与媒介偏好。"),
    ]
    for category, purpose in rows:
        lines.append(f"| {category} | {purpose} |")
    return "\n".join(lines)


def build_boards(entries, target):
    grouped = {}
    for entry in entries:
        grouped.setdefault(entry.get("board", ""), []).append(entry)
    for board, purpose in BOARDS:
        board_entries = sorted(grouped.get(board, []), key=natural_key)
        if not board_entries:
            continue
        prefix = board[:2]
        lines = [
            f"# {board}（{len(board_entries)} 条）",
            "",
            f"用途：{purpose}",
            "",
            "读取原文：`$EMOCHAT_KB/<path>`（仓库相对路径）。",
            "",
            "| ID | 标题 | 类型 | 阶段 | 标签 | 路径 |",
            "|---|---|---|---|---|---|",
        ]
        for entry in board_entries:
            lines.append(
                "| `{id}` | {title} | {type} | {stage} | {tags} | `{path}` |".format(
                    id=cell(entry.get("id", "")),
                    title=cell(entry.get("title", "")),
                    type=cell(entry.get("type", "")),
                    stage=cell(joined(entry.get("stage"))),
                    tags=cell(joined(entry.get("tags"))),
                    path=cell(entry.get("file", "")),
                )
            )
        if board == "00-语料原文":
            lines.extend([
                "",
                "> 本板块为 MIT 许可的第三方原文，使用时保留原作者署名与来源，"
                "不适用仓库其余内容的“保留所有权利”条款。",
            ])
        write(target / "references" / f"board-{prefix}.md", "\n".join(lines) + "\n")


def build_entry_map(entries, target):
    keys = [
        "id", "title", "tags", "type", "stage", "audience",
        "severity", "board", "file", "license", "confidence", "source",
    ]
    compact = []
    for entry in entries:
        compact.append({key: entry.get(key) for key in keys if key in entry})
    write(
        target / "references" / "entry-map.json",
        json.dumps(compact, ensure_ascii=False, indent=2) + "\n",
    )


def build_manifest(entries, target, edition, name):
    counts = {}
    for entry in entries:
        counts[entry.get("board", "")] = counts.get(entry.get("board", ""), 0) + 1
    if edition == "private":
        manifest = {
            "edition": edition,
            "name": name,
            "source": "索引/metadata.json",
            "total": len(entries),
            "boards": dict(sorted(counts.items())),
        }
    else:
        manifest = {
            "edition": edition,
            "name": name,
            "content": "framework-only",
            "included_entries": 0,
            "source_entries": len(entries),
        }
    write(target / "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")


def build_private(entries):
    target = DIST / "emochat-private"
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)

    description = (
        "中文情感聊天与关系风险分析（18+ 教育/防御向，含 589 条卡片索引）。"
        "用于分析聊天记录、判断关系走势、识别 PUA/诈骗/情感操控、处理拒绝与边界、"
        "异地网恋/FWB/线上亲密、性沟通与同意、私密影像与隐私安全、分手止损与危机转介。"
        "Use when the user asks for Chinese dating/relationship chat analysis, red flags, "
        "boundaries, consent, online intimacy, breakup, or privacy/safety advice."
    )
    notice = edition_notice_for("emochat-private")
    skill = (SRC / "SKILL.md").read_text(encoding="utf-8")
    skill = render(skill, {
        "NAME": "emochat",
        "DESCRIPTION": description,
        "EDITION_NOTICE": notice,
        "KB_SECTION": PRIVATE_KB_SECTION,
    })
    write(target / "SKILL.md", skill)

    copy_common(target)
    build_index(target, private_board_table(entries), PRIVATE_SEARCH_HINT, notice)
    build_boards(entries, target)
    build_entry_map(entries, target)
    build_manifest(entries, target, "private", "emochat")

    notice_text = (SRC / "NOTICE-private.md").read_text(encoding="utf-8")
    write(target / "NOTICE.md", notice_text)
    if (ROOT / "LICENSE.txt").is_file():
        copy_file(ROOT / "LICENSE.txt", target / "LICENSE.txt")
    write(target / "README.md", private_readme(entries))
    return target


def private_readme(entries):
    boards = len({entry.get("board") for entry in entries})
    return f"""# EmoChat 私有完整版

- 条目：{len(entries)} 条，{boards} 个板块
- 入口：`SKILL.md`
- 检索：`python scripts/emochat_search.py "关键词" --top 5`
- 安装：见 `adapters/installation.md`
- 索引：`references/index.md` 与 `references/board-*.md`
- 机器可读：`references/entry-map.json`

本版仅供仓库作者本地/私有环境使用，不得向第三方分发、上传公共平台或用于对外服务。
知识库正文仍受仓库根目录 `LICENSE.txt` 约束。
"""


def build_public(entries):
    target = DIST / "emochat-public"
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)

    description = (
        "中文情感聊天与关系风险分析框架（18+ 教育/防御向，不含知识库正文）。"
        "用于分析聊天记录、识别 PUA/诈骗/情感操控、处理边界与拒绝、"
        "异地网恋/FWB/线上亲密、性沟通与同意、隐私与危机转介。"
        "Use when the user asks for Chinese dating/relationship chat analysis, red flags, "
        "boundaries, consent, or safety advice."
    )
    notice = edition_notice_for("emochat-public")
    skill = (SRC / "SKILL.md").read_text(encoding="utf-8")
    skill = render(skill, {
        "NAME": "emochat-framework",
        "DESCRIPTION": description,
        "EDITION_NOTICE": notice,
        "KB_SECTION": PUBLIC_KB_SECTION,
    })
    write(target / "SKILL.md", skill)

    copy_common(target)
    build_index(target, public_board_table(), PUBLIC_SEARCH_HINT, notice)
    build_manifest(entries, target, "public", "emochat-framework")

    notice_text = (SRC / "NOTICE-public.md").read_text(encoding="utf-8")
    write(target / "NOTICE.md", notice_text)
    write(target / "README.md", public_readme())
    return target


def public_readme():
    return """# EmoChat 公开框架版

- 入口：`SKILL.md`
- 内容：分析流程、风险/亲密/危机 playbook、输出模板、安全边界
- 不含：EmoChat-KB 的 589 条知识库正文、案例、话术或卡片索引
- 可选：如自备同结构知识库，设置 `EMOCHAT_KB` 后使用 `scripts/emochat_search.py`
- 安装：见 `adapters/installation.md`

本版可原样分享；不得加入知识库正文、用于商业服务、训练/微调或修改后再分发。
"""


def main():
    entries = load_metadata()
    private = build_private(entries)
    public = build_public(entries)
    print(f"私有完整版: {private} ({len(entries)} 条)")
    print(f"公开框架版: {public} (仅框架)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
