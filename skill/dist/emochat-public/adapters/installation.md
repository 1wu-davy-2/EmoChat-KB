# 各平台安装与适配

两版技能包：

| 版本 | 目录 | 适用 |
|---|---|---|
| 私有完整版 | `dist/emochat-private/` | 仓库作者本地使用，可检索 589 条卡片 |
| 公开框架版 | `dist/emochat-public/` | 分享给他人；不含知识库正文，只含框架与 playbooks |

`SKILL.md` 是通用入口；支持 Agent Skills 的平台直接安装整个目录即可。不支持技能目录的平台使用 `adapters/prompt-pack.md`。

## Claude Code

```bash
# 用户级（所有项目可用）
mkdir -p ~/.claude/skills
cp -r dist/emochat-private ~/.claude/skills/emochat

# 或项目级
mkdir -p .claude/skills
cp -r dist/emochat-private .claude/skills/emochat
```

重启会话，或在技能列表中确认。Claude Code 会读取 `SKILL.md` 的 `name` 与 `description` 决定是否触发。

## Qoder

```bash
# 用户级
mkdir -p ~/.qoder/skills
cp -r dist/emochat-private ~/.qoder/skills/emochat

# 或项目级
mkdir -p .qoder/skills
cp -r dist/emochat-private .qoder/skills/emochat
```

在 Qoder 中运行 `/skills reload` 刷新；用 `/skills` 查看；也可以 `/emochat` 手动触发。Qoder 要求 `name` 仅含小写字母、数字、连字符，长度 ≤64；`description` ≤1024 字符。

## Codex CLI

```bash
mkdir -p ~/.codex/skills
cp -r dist/emochat-private ~/.codex/skills/emochat
```

部分 Codex 版本也会发现 `~/.agents/skills/`。如果技能没有出现，检查当前版本的技能目录设置，或把 `adapters/AGENTS.md` 放到项目根目录作为兜底。

## Grok / Pi / WorkBuddy / 其他无技能目录的平台

这些平台通常没有统一的 `SKILL.md` 发现机制，或版本差异较大。使用单文件提示包：

1. 打开 `adapters/prompt-pack.md`。
2. 粘贴到系统提示、项目指令、角色设定或对话开头。
3. 如平台支持附件，把 `references/*.md` 一并上传；否则只保留 prompt pack。
4. 如果平台支持本地文件/命令，按 `references/kb-integration.md` 设置 `EMOCHAT_KB`。

## 通用 AGENTS.md 平台

把 `adapters/AGENTS.md` 复制到项目根目录，或把内容合并到已有的 `AGENTS.md`。它会让 agent 加载 `SKILL.md` 并遵守边界。

## 私有版路径配置

技能安装到知识库之外时，检索脚本需要知道仓库位置：

```bash
# Windows PowerShell
$env:EMOCHAT_KB = "D:\path\to\EmoChat-KB"

# macOS / Linux
export EMOCHAT_KB="$HOME/EmoChat-KB"
```

也可以每次传 `--kb`：

```bash
python scripts/emochat_search.py "FWB 公平" --top 5 --kb "E:/opt/Qoder/EmoChat-KB"
```

## 验证

```bash
# 在技能目录内
python scripts/emochat_search.py "FWB 公平" --top 3
python scripts/emochat_search.py "视频亲密 录屏 停止" --top 3
python scripts/emochat_search.py "异地网恋 奔现" --top 3
```

应返回对应板块的卡片与路径。若提示找不到知识库，按上面的 `EMOCHAT_KB` 配置。

## 更新

知识库内容变化后，在仓库根目录运行：

```bash
python skill/build.py
python skill/check.py
```

然后重新复制 `dist/emochat-private` 到技能目录。公开版重新生成 `dist/emochat-public`，不会包含知识库正文。

## 注意

- 两个版本不要同时安装为同名技能；公开版名为 `emochat-framework`，私有版为 `emochat`。
- 私有版含知识库正文索引，不得上传公共仓库、网盘、技能市场或对外服务。
- 公开版可以原样分享，但不得加入知识库正文、案例或话术。
