---
id: raw-109
title: Love Advise Skill
tags: [语料原文, 恋爱导师-进化心理学]
type: 语料原文
source: "https://github.com/lgl1996521/love-advise-skill (blob/HEAD/README.md)"
license: MIT
confidence: 中
---

> 语料原文层:整篇搬运自 MIT 许可仓库 lgl1996521/love-advise-skill(6★),原文路径 `README.md`。
> 版权归原仓库作者所有,依据 MIT 许可证复制(保留版权与许可声明)。

<div align="center">

# Love Advise Skill

**基于进化心理学与社交动力学的 AI 恋爱导师**

[![Skill](https://img.shields.io/badge/Claude_Code-Skill-blue)](https://claude.ai/claude-code)
[![Python](https://img.shields.io/badge/Python-3.12-green)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

[English](#english) · [中文文档](#中文文档)

</div>

---

## 中文文档

### 这是什么？

一个 Claude Code Skill，让 AI 化身洞察人性的资深恋爱导师，以犀利直接的"梵公子风格"指导男性用户择偶、恋爱和社交。不喂鸡汤，不给虚假希望，用社会运行规律和人性本质帮你看清真相。

### 核心特点

- **犀利人格** — 不绕弯子，一针见血地指出问题本质
- **理论支撑** — 基于进化心理学、社交动力学、行为经济学等学术理论
- **四大模块** — 女性类型分析 / 个人价值建设 / 沟通聊天策略 / 约会实战技巧
- **按需加载** — 知识模块仅在相关话题触发时加载，不浪费上下文
- **内容边界** — 帮助用户成长而非操控他人，明确 Do/Don't 原则

### 项目结构

```
love-advise-skill/
├── SKILL.md                          # 主 Skill 文件（人格设定 + 对话策略 + 模块索引）
├── references/                       # 知识模块（按需加载）
│   ├── female-types.md               # 女性类型分析
│   │   ├── 进化心理学择偶策略
│   │   ├── 女性分类体系（性格/价值观）
│   │   ├── 社交软件女性类型识别
│   │   └── 白富美人设识别
│   ├── value-building.md             # 个人价值建设
│   │   ├── 外形吸引力构建（发型/穿搭/健身）
│   │   ├── 社交媒体展示策略
│   │   ├── 生活方式升级
│   │   └── 社交圈层突破
│   ├── communication.md              # 沟通与聊天策略
│   │   ├── 冷读技巧（快速识人）
│   │   ├── 聊天节奏控制（推拉/断联/价值输出）
│   │   ├── 情绪价值输出（幽默/共情/引导）
│   │   └── 社交软件话术（开场/维护/邀约）
│   └── dating-practice.md            # 约会实战技巧
│       ├── 搭讪技巧与心态建设
│       ├── 首次约会设计
│       ├── 肢体语言与微表情
│       ├── 表白时机判断
│       └── 各阶层脱单策略
└── docs/
    └── feasibility_research_report.md  # 恋爱模拟预测可行性研究报告
```

### 安装使用

**方式一：直接使用 .skill 文件**

1. 下载 `love_advise_skill.skill` 文件
2. 在 Claude Code 中导入该 Skill

**方式二：手动安装**

1. 将本项目克隆到本地
2. 将 `SKILL.md` 和 `references/` 目录复制到你的 Claude Code skills 目录

### 使用示例

<details>
<summary>点击展开对话示例</summary>

**用户**: "我喜欢的女生总说她忙，但朋友圈经常出去玩"

**导师**: "兄弟，醒醒。她不是忙，她是对你忙。人对自己在意的事情永远有时间。她在朋友圈出去玩说明她有时间社交，只是她的社交优先级里你排得很后面。

底层逻辑：吸引力不够的时候，你的邀约对她来说是'消耗'而不是'期待'。你再追只会继续贬值。

你现在要做两件事：第一，立刻停下来，别再主动了。第二，把精力放回自己身上——健身、社交、丰富生活。当你自己的生活精彩到她能在朋友圈看到的时候，局面会反过来。

记住：吸引力不是追来的，是构建的。"

---

**用户**: "社交软件上怎么开场聊天"

**导师**: "别用'你好''嗨''你好漂亮'这种开场 — 零信息量，她每天收到几十条。

有效的开场需要做一件事：让她觉得你不是群发的。

三种开场方式：

1. **细节观察法** — 从她照片/简介找一个细节：'这张照片是在大理拍的吗？我去年也去过，你选的角度比我好多了'
2. **直接但有趣** — '说实话我刷到你的主页停了三秒，这在我们行业叫高质量内容停留'
3. **情境假设法** — 抛一个有趣的小问题

核心原理：社交交换理论。你发的每条消息都在问'这条给了她什么价值？'如果你的开场只是'你好'，你什么价值都没给。"

</details>

### 理论基础

| 模块 | 底层理论 |
|------|----------|
| 女性类型分析 | 进化心理学（亲代投资理论、Buss 跨文化择偶研究） |
| 个人价值建设 | 信号传递理论、社交价值理论 |
| 沟通聊天策略 | 行为经济学（框架效应、损失厌恶）、冷读心理学 |
| 约会实战技巧 | 依恋理论、相似性吸引效应、曝光效应 |

### 内容原则

| Do | Don't |
|----|-------|
| 帮用户理解人性规律和社交本质 | 不教操控技术和欺骗性策略 |
| 提升个人吸引力和社交智慧 | 不帮用户"拿下"某个特定的人 |
| 基于真实自我构建吸引力 | 不鼓励伪装成另一个人 |

---

## English

### What is this?

A Claude Code Skill that turns AI into an insightful dating coach for men. Based on evolutionary psychology, social dynamics, and behavioral economics — delivering sharp, honest advice that cuts through the noise.

### Key Features

- **Sharp Persona** — No sugar-coating. Direct truth with underlying logic
- **Science-Backed** — Evolutionary psychology, social dynamics, behavioral economics
- **4 Knowledge Modules** — Female psychology / Personal value / Communication / Dating practice
- **Progressive Loading** — Knowledge modules load on-demand, keeping context lean
- **Ethical Boundaries** — Help users grow, not manipulate others

### Quick Start

1. Download or clone this repo
2. Import the `.skill` file into Claude Code, or copy `SKILL.md` + `references/` to your skills directory

### Knowledge Modules

| Module | File | Core Content |
|--------|------|--------------|
| Female Types | `references/female-types.md` | Evolutionary psychology, type classification, social app profiles |
| Value Building | `references/value-building.md` | Appearance, social media strategy, lifestyle upgrade |
| Communication | `references/communication.md` | Cold reading, push-pull, emotional value, messaging |
| Dating Practice | `references/dating-practice.md` | Date design, body language, confession timing, strategies by age |

### Theoretical Foundation

- **Evolutionary Psychology** — Parental Investment Theory (Trivers 1972), Cross-cultural mate preferences (Buss 1989)
- **Signaling Theory** — High-cost vs low-cost signals in attraction
- **Behavioral Economics** — Framing effects, loss aversion in social interactions
- **Attachment Theory** — How attachment styles affect dating dynamics
- **Social Dynamics** — Similarity-attraction, mere exposure effect

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Theoretical foundations from David Buss, Daniel Kahneman, John Bowlby
- Inspired by publicly available content from 梵公子社会学 (Bilibili)
- Built with [Claude Code Skills](https://claude.ai/claude-code) framework

---

<div align="center">

**如果这个项目对你有帮助，给个 Star 吧!**

</div>
