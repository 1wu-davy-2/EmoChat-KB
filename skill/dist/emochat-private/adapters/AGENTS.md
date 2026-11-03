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
2. 用户贴的是几十上百条完整记录时，先跑一次分析脚本，不要逐条读进上下文：
   ```bash
   python scripts/emochat_analyze.py profile chat.txt --me "我" --json --timing
   # 用户追加人物描述
   python scripts/emochat_analyze.py profile chat.txt --me "我" --notes "对方 28 岁，回避型"
   # 用户又贴了新记录
   python scripts/emochat_analyze.py profile chat.txt --me "我" --append
   ```
3. 用户只问“这条怎么回”时，复用画像跑 `reply`，不要重跑全量：
   ```bash
   python scripts/emochat_analyze.py reply --message "..." --profile profile.json --json --timing
   ```
4. 选择 `references/playbook-chat.md`、`playbook-risk.md`、`playbook-intimacy.md` 或 `playbook-crisis.md`。
5. 需要补充条目时手动检索，读 top 3-5 张卡片，不要整库读入：
   ```bash
   python scripts/emochat_search.py "关键词" --top 5
   ```
6. 用 `references/output-templates.md` 的结构输出。
7. 遵守 `references/safety-boundaries.md` 的硬边界。

没有知识库副本时加 `--no-search`，脚本仍会给出解析、画像与意图判断，只是不带卡片。

## 路径

- 技能目录：本文件所在目录的上一级（即包含 `SKILL.md` 的目录）。
- 知识库路径：`--kb` 参数、`EMOCHAT_KB` 环境变量，或技能根目录 `.emochat-kb` 文件；都未设置时脚本会向上查找包含 `索引/metadata.json` 的目录。
- 找不到知识库时询问用户，不要猜路径。

## 禁止

- 不提供操控、跟踪、定位、入侵、伪造身份、规避平台审核的方法。
- 不提供露骨性内容、药物剂量、自伤/暴力方法。
- 不服务未成年人恋爱或性内容。
- 不编造来源、案例或统计。
- 不把用户隐私写入文件或外部服务。
