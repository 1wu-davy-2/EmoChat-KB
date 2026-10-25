---
id: raw-101
title: 安装指南
tags: [语料原文, 军师]
type: 语料原文
source: "https://github.com/YXZ1211/junshi-skill (blob/HEAD/INSTALL.md)"
license: MIT
confidence: 中
---

> 语料原文层:整篇搬运自 MIT 许可仓库 YXZ1211/junshi-skill(5★),原文路径 `INSTALL.md`。
> 版权归原仓库作者所有,依据 MIT 许可证复制(保留版权与许可声明)。

# 安装指南

## 环境要求

- **Claude Code** 或 **OpenClaw**：免费安装（[Claude Code 安装指南](https://docs.anthropic.com/en/docs/claude-code)）
- **API 消耗**：每次分析约消耗 500-2000 tokens
- **付费方式**（二选一）：
  - Claude Pro / Max 订阅：在订阅额度内使用
  - Anthropic API Key：按量付费
- **不需要 GPU，不需要本地模型，不需要 Docker**

---

## 安装到 Claude Code

```bash
# 安装到当前项目（在 git 仓库根目录执行）
mkdir -p .claude/skills
git clone https://github.com/YXZ1211/junshi-skill .claude/skills/junshi

# 或安装到全局（所有项目都能用）
git clone https://github.com/YXZ1211/junshi-skill ~/.claude/skills/junshi
```

安装后重启 Claude Code，输入 `/junshi` 即可调用。

---

## 安装到 OpenClaw

1. 打开 OpenClaw
2. 进入 Skills 管理页面
3. 点击「导入 Skill」
4. 粘贴仓库地址：`https://github.com/YXZ1211/junshi-skill`

---

## 更新

```bash
cd ~/.claude/skills/junshi
git pull
```
