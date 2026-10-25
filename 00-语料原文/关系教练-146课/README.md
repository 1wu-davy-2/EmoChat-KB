---
id: raw-094
title: ❤️ Relationship Coach - 恋爱关系教练
tags: [语料原文, 关系教练-146课]
type: 语料原文
source: "https://github.com/cozer-1024/openclaw-relationship-coach (blob/HEAD/README.md)"
license: MIT
confidence: 中
---

> 语料原文层:整篇搬运自 MIT 许可仓库 cozer-1024/openclaw-relationship-coach(6★),原文路径 `README.md`。
> 版权归原仓库作者所有,依据 MIT 许可证复制(保留版权与许可声明)。

# ❤️ Relationship Coach - 恋爱关系教练

> **为 OpenClaw / Claude Code 打造的恋爱关系 Skill**  
> 整合 146 集课程精华（梁叔&谷医生、陶子老师、静姐、许诺团队等）  
> 核心理念：**真诚是基石，技巧是辅助，吸引是本质**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![OpenClaw Skill](https://img.shields.io/badge/OpenClaw-Skill-purple)](#)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/cozer-1024/openclaw-relationship-coach/pulls)

---

## 📦 安装

### 方式一：OpenClaw（推荐）

```bash
# 克隆到 skills 目录
git clone https://github.com/cozer-1024/openclaw-relationship-coach.git \
  ~/.openclaw/skills/relationship-coach

# 重启 OpenClaw
# openclaw gateway restart
```

> 或复制到 `workspace/skills/` 目录，OpenClaw 会自动加载。

### 方式二：Claude Code

```bash
# 克隆到 Claude Code skills 目录
git clone https://github.com/cozer-1024/openclaw-relationship-coach.git \
  ~/.claude/skills/relationship-coach
```

### 方式三：手动安装

1. 下载或克隆本仓库
2. 将 `relationship-coach/` 文件夹放入你的 AI 工具 skills 目录
3. 确保 `SKILL.md` 可被 AI 读取

---

## 🚀 快速开始

### 新手学习路径（推荐顺序）

```
第 1 步：阅读核心心法（5 分钟）
    ↓
第 2 步：学习万能回复四步法（10 分钟）
    ↓
第 3 步：掌握聊天基础技巧（30 分钟）
    ↓
第 4 步：了解女性分类（15 分钟）
    ↓
第 5 步：学习约会流程（20 分钟）
    ↓
第 6 步：实战练习 + 查阅具体问题
```

### 触发方式

安装后在 AI 对话框中直接描述你的场景，Skill 会自动判断并调用对应知识：

| 你说 | 它做什么 |
|------|----------|
| "她回复冷淡怎么办？" | 读取聊天技巧 → 判断好感度 → 给话术 |
| "她是什么类型？" | 读取女性分类 → 分析性格 → 给应对策略 |
| "怎么约她出来？" | 读取约会流程 → 给邀约时机和话术 |
| "怎么推进关系？" | 读取关系推进 → 给暧昧升温建议 |
| "异地恋怎么维持？" | 读取长期关系 → 给相处策略 |

---

## 📚 文件结构

```
relationship-coach/
├── README.md                        ← 导航入口
├── SKILL.md                         ← 技能主文件（AI 触发逻辑）
├── LICENSE                          ← MIT 开源许可
└── references/
    ├── chat-techniques.md           ← 聊天核心技巧
    ├── personality-types.md         ← 女性人格类型（六大 + 八型）
    ├── dating-flows.md              ← 约会流程与关系阶段
    ├── intimate-relationships.md    ← 亲密关系指导
    └── relationship-truths.md       ← 恋爱真相与自我提升
```

---

## 📖 内容导航

### 按场景查

| 场景 | 推荐文件 | 核心内容 |
|------|----------|----------|
| **刚认识/社交软件** | `references/personality-types.md` | 女性六大分类快速判断 |
| **日常聊天** | `references/chat-techniques.md` | 万能回复四步法、推拉曲解 |
| **约会规划** | `references/dating-flows.md` | 关系四阶段、约会流程 |
| **关系推进** | `references/intimate-relationships.md` | 暧昧升温、确定关系 |
| **长期关系** | `references/relationship-truths.md` | 恋爱真相、自我提升 |

### 按难度学

| 层级 | 文件 | 适合人群 |
|------|------|----------|
| **入门** | `README.md`（导航入口） | 所有人 |
| **基础** | `references/chat-techniques.md` §心法~情绪共鸣 | 新手 |
| **进阶** | `references/chat-techniques.md` §推拉~技巧补充 | 有一定经验 |
| **高级** | `references/dating-flows.md` | 需要约会指导 |

---

## 🎯 核心心法（必读）

### 聊天本质

> "聊天聊的是情绪，不是信息交换"

### 吸引公式

```
吸引 = 价值 + 需求 + 情绪
```

### 关系四阶段

| 阶段 | 目标 | 聊天尺度 |
|------|------|----------|
| 初期认识 | 消除陌生感 | 浅层话题 |
| 建立吸引 | 展示价值 | 适度深入 |
| 升高关系 | 制造暧昧 | 深入暧昧 |
| 维护关系 | 长期巩固 | 不限 |

### 万能回复四步法

```
明确当下关系 → 读懂对方意图 → 认清回复方向 → 斟酌回复措辞
```

---

## 🔍 常见问题速查

| 问题 | 查看位置 |
|------|----------|
| "怎么开场不尴尬？" | `chat-techniques.md` → 8.3 开场白模板 |
| "她回复冷淡怎么办？" | `chat-techniques.md` → 8.4 判断好感度 |
| "她是哪种类型的女生？" | `personality-types.md` → 六大分类/八型人格 |
| "怎么约她出来？" | `dating-flows.md` → 邀约技巧 |
| "怎么判断她喜不喜欢我？" | `dating-flows.md` → 好感度测试标准 |
| "怎么推进关系？" | `dating-flows.md` → 关系四阶段 |
| "怎么聊天不冷场？" | `chat-techniques.md` → 1. 延展话题万能框架 |
| "什么是推拉技巧？" | `chat-techniques.md` → 1. 情绪推拉技巧 |

---

## 📊 内容来源

| 课程系列 | 集数 | 主要内容 |
|----------|------|----------|
| 梁叔&谷医生 - 社交软件聊天 | 18 集 | 社交软件开场、框架、强化技术 |
| 陶子老师 - 聊天实战技巧 | 24 集 | 聊天框架、女性分类、调情手法 |
| 陶子老师 - 情绪沟通法 | 9 集 | 万能回复四步法、情绪共振 |
| 微信聊天实战课程 | 33 集 | 微信聊天心态、技巧、邀约 |
| 聊天技巧入门 - 许诺团队 | 26 集 | 聊天本质、价值展示、情绪波动 |
| 静姐（男性成长） | 若干 | 暧昧期心态、关系推进 |

---

## 🤝 贡献

欢迎提交 Issues 和 Pull Requests！

如果有更好的话术、技巧或场景分析，可以直接改 `references/` 下的文件。请保持内容结构统一。

---

## 📄 许可

MIT License — 欢迎自由使用、修改、分发。

---

## ⭐ 支持

如果对你有帮助，点个 Star 支持一下 🔥
