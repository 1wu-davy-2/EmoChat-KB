# 接入本地知识库

## 两种运行方式

| 方式 | 适用 | 行为 |
|---|---|---|
| 私有完整版 + 本地仓库 | 仓库作者本人 | 用 `scripts/emochat_analyze.py` 出画像/回复，用 `scripts/emochat_search.py` 检索 589 条卡片，按需读取原文 |
| 公开框架版 | 没有知识库副本，或使用自己的知识库 | 用内置 playbooks；`emochat_analyze.py --no-search` 仍可解析与判断，设置 `EMOCHAT_KB` 后可检索用户自备的仓库 |

## 指定知识库路径

优先级从高到低：

1. 命令行参数：`--kb /path/to/EmoChat-KB`
2. 环境变量：`EMOCHAT_KB=/path/to/EmoChat-KB`
3. 技能根目录的 `.emochat-kb` 文件（单行绝对路径）。
4. 从脚本位置向上查找包含 `索引/metadata.json` 或 `01-核心方法/` 的目录。

找不到时，脚本会返回错误与提示。不要猜路径，也不要扫描整个磁盘。

```bash
# Windows PowerShell
$env:EMOCHAT_KB = "D:\path\to\EmoChat-KB"
python scripts/emochat_search.py "FWB 公平" --top 5

# macOS / Linux
export EMOCHAT_KB="$HOME/EmoChat-KB"
python scripts/emochat_search.py "异地网恋 奔现" --top 5

# 可选：在技能根目录固定路径（优先级低于 --kb 和 EMOCHAT_KB）
echo "D:\path\to\EmoChat-KB" > .emochat-kb
```

## 分析脚本（快速通道）

`scripts/emochat_analyze.py` 把“解析 → 画像 → 风险 → 检索 → 输出”合成一次调用，避免把上百条聊天记录读进上下文再手写分析。

```bash
# 1) 长记录画像（100 条以上优先用这个）
python scripts/emochat_analyze.py profile chat.txt --me "我" --json --timing

# 2) 追加人物描述（用户补充对方信息时）
python scripts/emochat_analyze.py profile chat.txt --me "我" --notes "对方 28 岁，外地打工，回避型"
python scripts/emochat_analyze.py profile chat.txt --me "我" --notes-file notes.txt

# 3) 增量画像（用户又贴了新的一段记录）
python scripts/emochat_analyze.py profile chat.txt --me "我" --append

# 4) 单条消息回复（复用上一步的 profile，不重跑全量）
python scripts/emochat_analyze.py reply --message "我们到底算什么关系" --profile profile.json --json --timing
```

`profile` 输出：说话人识别、消息量与回复间隔、互惠度、话题与阶段、风险信号与等级、生成的检索词、带摘要的卡片包、以及用户 notes 提炼出的主题。`reply` 输出：意图判定、与画像合并后的风险、检索词、以及三版安全回复骨架。

常用参数：

| 参数 | 作用 |
|---|---|
| `--me "我"` | 指定用户自己在记录里的称呼，决定“谁说的”归属；默认第一位发言者 |
| `--notes` / `--notes-file` | 追加人物描述，可重复；参与风险与主题判断 |
| `--append` | 在已有 profile 上做增量，并给出变化摘要 |
| `--profile` | `reply` 复用画像，省去重新解析 |
| `--search-top` / `--top` | 卡片包条数（`profile` 用 `--search-top`，默认 6；`reply` 用 `--top`，默认 5） |
| `--excerpt` | 卡片摘要字数（`profile` 默认 700，`reply` 默认 650） |
| `--from other\|me` | `reply` 的消息来自对方还是用户自己 |
| `--no-search` | 只做解析与判断，不检索（公开版无知识库时用） |
| `--out` / `--no-save` | 画像 JSON 输出路径 / 不落盘 |
| `--format auto\|lines\|json` | 记录格式；`auto` 识别不了时手动指定 |
| `--session-gap` | 判定“新一次会话”的间隔分钟数，默认 360 |
| `--json` / `--timing` | 机器可读输出与耗时（耗时写 stderr，不会污染 JSON） |

支持的记录格式：`说话人: 内容`、`2026-01-01 20:00 说话人: 内容`、`[2026-01-01 20:00] 说话人: 内容`、说话人单独成行的导出格式，以及 JSON 数组（或含 `messages` 数组的对象）。识别不了会直接报错并提示格式，不会静默丢消息。

## 检索脚本

```bash
python scripts/emochat_search.py "查询词" --top 5
python scripts/emochat_search.py "查询词" --top 5 --board 06
python scripts/emochat_search.py "查询词" --tag 话术示例
python scripts/emochat_search.py "查询词" --json
python scripts/emochat_search.py "查询词" --kb /path/to/EmoChat-KB
```

输出字段：

- `score`：BM25 风格相关度
- `id` / `title` / `path` / `abs_path`
- `tags` / `type` / `stage` / `audience` / `severity`

## 仓库结构

```text
EmoChat-KB/
├── 00-语料原文/          # MIT 语料，按原始许可证使用
├── 01-核心方法/          # method-NNN
├── 02-话术库/            # script-NNN
├── 03-人群画像/          # persona-NNN
├── 04-性格星座/          # astro-NNN
├── 05-场景流程/          # scene-NNN
├── 06-风险与反收割/      # risk-NNN
├── 07-操控图谱/          # tactic-NNN
├── 08-书籍要点/          # book-NNN
├── 09-来源与许可/
├── 10-调研报告/          # research-NNN
├── 11-亲密与性/          # intimacy-NNN（18+）
├── 12-用户侧画像/        # user-NNN
└── 索引/
    ├── metadata.json     # 条目元数据
    ├── search.py         # 原库检索脚本
    └── acceptance_run.py # 检索验收
```

每个条目是带 YAML frontmatter 的 Markdown 文件，必填字段：

```yaml
id: risk-XXX
title: 示例标题
tags: [风险, 诈骗]
type: 方法论
source: "来源"
confidence: 高
```

可选字段：`audience`、`stage`、`direction`、`severity`、`license`。

## 检索策略

- 用 2-4 组不同关键词：用户原话、同义词、板块术语、风险类型。
- 先看 `id` 前缀判断板块，再看 `tags` 与 `severity`。
- 读 top 3-5 张卡片即可，不要把整个板块或整库读入上下文。
- 引用时使用 `id` + `title`，必要时给出仓库相对路径。
- 公开案例、合成案例、坏话术样本按原卡标注使用；不要改写成立场不明的“真实故事”。

## 自备知识库

公开框架版可以与任何同结构知识库配合使用。最小要求：

- 一个根目录，包含 `索引/metadata.json`；
- metadata 为数组，每项至少有 `id`、`title`、`file`、`tags`、`type`；
- `file` 为相对根目录的 Markdown 路径；
- 条目使用 YAML frontmatter。

如果结构不同，修改 `scripts/emochat_search.py` 的 `load_entries()` 即可。

## 安全

- 只读取用户明确授权的目录；不扫描主目录、不读取无关文件。
- 不把知识库全文复制到回答或外部服务。
- 不把用户聊天内容写回知识库或用于训练。
- 公开版不包含知识库正文；不要声称检索了未提供的资料。
