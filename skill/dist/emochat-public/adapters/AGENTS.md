# EmoChat Agent Instructions

本文件给支持 `AGENTS.md` 的通用 agent / Codex 项目使用。若平台支持 `SKILL.md`，优先安装技能目录；本文件只是项目级入口。

## 触发

当用户提到以下主题时，加载 `SKILL.md` 并按其流程工作：

- 中文聊天、开场、接话、热聊、邀约、要联系方式、关系定义
- 情感操控、PUA、诈骗、杀猪盘、经济控制、跟踪骚扰
- 边界、拒绝、分手、复合、冲突修复
- 异地网恋、FWB、线上亲密、语音/视频、性沟通、同意
- 私密影像、隐私泄露、账号安全
- 自伤、暴力、性侵、跟踪等危机

## 工作流

1. 读 `SKILL.md`，先做角色、阶段、紧急度确认。
2. 选择 `references/playbook-chat.md`、`playbook-risk.md`、`playbook-intimacy.md` 或 `playbook-crisis.md`。
3. 若可访问知识库，运行：
   ```bash
   python scripts/emochat_search.py "关键词" --top 5
   ```
   读 top 3-5 张卡片，不要整库读入。
4. 用 `references/output-templates.md` 的结构输出。
5. 遵守 `references/safety-boundaries.md` 的硬边界。

## 路径

- 技能目录：本文件所在目录的上一级（即包含 `SKILL.md` 的目录）。
- 知识库路径：`--kb` 参数或 `EMOCHAT_KB` 环境变量；未设置时脚本会向上查找包含 `索引/metadata.json` 的目录。
- 找不到知识库时询问用户，不要猜路径。

## 禁止

- 不提供操控、跟踪、定位、入侵、伪造身份、规避平台审核的方法。
- 不提供露骨性内容、药物剂量、自伤/暴力方法。
- 不服务未成年人恋爱或性内容。
- 不编造来源、案例或统计。
- 不把用户隐私写入文件或外部服务。
