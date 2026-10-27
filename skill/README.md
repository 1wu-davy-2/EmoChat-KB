# EmoChat 通用 Agent Skill

把 EmoChat-KB 打包成跨平台 Agent Skill。采用「单入口 + 渐进披露」：

- `SKILL.md`：触发条件、工作流、输出格式、硬边界
- `references/`：四类 playbook、输出模板、安全边界、知识路由
- `scripts/emochat_search.py`：零依赖 BM25 检索，支持 `--kb` / `EMOCHAT_KB`
- `adapters/`：Claude Code、Qoder、Codex、AGENTS.md 与单文件 prompt pack

## 两个版本

| 版本 | 输出目录 | 内容 | 用途 |
|---|---|---|---|
| 私有完整版 | `dist/emochat-private/` | 589 条卡片索引 + 检索脚本 + playbooks | 仓库作者本地使用 |
| 公开框架版 | `dist/emochat-public/` | playbooks + 安全边界 + 输出模板，无知识库正文 | 分享给他人 |

私有版不得上传公共仓库、网盘、技能市场或对外服务；公开版不得加入知识库正文、案例或话术。

## 构建

在仓库根目录运行：

```bash
python skill/build.py
python skill/check.py
```

`build.py` 从 `索引/metadata.json` 生成板块索引、`entry-map.json` 与 `manifest.json`。知识库更新后重新构建即可。

## 安装

详细路径见 `src/adapters/installation.md`（构建后为 `dist/*/adapters/installation.md`）。

### Claude Code

```bash
cp -r skill/dist/emochat-private ~/.claude/skills/emochat
# 或项目级
cp -r skill/dist/emochat-private .claude/skills/emochat
```

### Qoder

```bash
cp -r skill/dist/emochat-private ~/.qoder/skills/emochat
# 或项目级
cp -r skill/dist/emochat-private .qoder/skills/emochat
```

安装后在 Qoder 中运行 `/skills reload`。

### Codex CLI

```bash
cp -r skill/dist/emochat-private ~/.codex/skills/emochat
```

部分版本也发现 `~/.agents/skills/`；如未出现，检查当前版本设置，或使用 `adapters/AGENTS.md` 兜底。

### Grok / Pi / WorkBuddy / 其他平台

把 `adapters/prompt-pack.md` 粘贴到系统提示、项目指令或对话开头。支持文件访问的平台可再配置 `EMOCHAT_KB` 使用检索脚本。

## 配置知识库路径

技能安装在仓库之外时：

```bash
# Windows PowerShell
$env:EMOCHAT_KB = "D:\path\to\EmoChat-KB"

# macOS / Linux
export EMOCHAT_KB="$HOME/EmoChat-KB"
```

或每次传 `--kb`。脚本也会从自身位置向上查找包含 `索引/metadata.json` 的目录。

## 验证

```bash
python skill/check.py
python skill/dist/emochat-private/scripts/emochat_search.py "FWB 公平" --top 3
```

`check.py` 会检查：

- `SKILL.md` frontmatter 与描述长度（Qoder 限制 1024 字符）
- 私有版 12 个板块索引是否覆盖全部条目
- `entry-map.json` / `manifest.json` 计数
- 内部链接与未替换占位符
- 4 组真实查询的检索命中
- 公开版不含卡片 ID、板块索引或 `entry-map.json`

## 目录

```text
skill/
├── README.md
├── build.py
├── check.py
├── src/
│   ├── SKILL.md
│   ├── NOTICE-private.md
│   ├── NOTICE-public.md
│   ├── references/
│   │   ├── index.md
│   │   ├── playbook-chat.md
│   │   ├── playbook-risk.md
│   │   ├── playbook-intimacy.md
│   │   ├── playbook-crisis.md
│   │   ├── output-templates.md
│   │   ├── safety-boundaries.md
│   │   └── kb-integration.md
│   ├── scripts/emochat_search.py
│   └── adapters/
│       ├── AGENTS.md
│       ├── installation.md
│       └── prompt-pack.md
└── dist/
    ├── emochat-private/
    └── emochat-public/
```

## 许可

- 私有版：受仓库根目录 `LICENSE.txt` 约束，仅供作者本地/私有环境使用。
- 公开版：`NOTICE.md` 给出分享范围；发布前请按你的意愿确认授权措辞。它不含知识库正文，但仍然是你的作品。

`00-语料原文/` 的 MIT 内容不进入公开版；私有版引用时保留原作者署名与来源。
