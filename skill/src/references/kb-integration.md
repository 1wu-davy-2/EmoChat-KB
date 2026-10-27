# 接入本地知识库

## 两种运行方式

| 方式 | 适用 | 行为 |
|---|---|---|
| 私有完整版 + 本地仓库 | 仓库作者本人 | 通过 `scripts/emochat_search.py` 检索 589 条卡片，按需读取原文 |
| 公开框架版 | 没有知识库副本，或使用自己的知识库 | 使用内置 playbooks；若设置 `EMOCHAT_KB`，同样可以检索用户自备的仓库 |

## 指定知识库路径

优先级从高到低：

1. 命令行参数：`--kb /path/to/EmoChat-KB`
2. 环境变量：`EMOCHAT_KB=/path/to/EmoChat-KB`
3. 从脚本位置向上查找包含 `索引/metadata.json` 或 `01-核心方法/` 的目录。

找不到时，脚本会返回错误与提示。不要猜路径，也不要扫描整个磁盘。

```bash
# Windows PowerShell
$env:EMOCHAT_KB = "D:\path\to\EmoChat-KB"
python scripts/emochat_search.py "FWB 公平" --top 5

# macOS / Linux
export EMOCHAT_KB="$HOME/EmoChat-KB"
python scripts/emochat_search.py "异地网恋 奔现" --top 5
```

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
