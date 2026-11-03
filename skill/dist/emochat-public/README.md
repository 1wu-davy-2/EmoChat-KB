# EmoChat 公开框架版

- 入口：`SKILL.md`
- 内容：分析流程、风险/亲密/危机 playbook、输出模板、安全边界
- 不含：EmoChat-KB 的 589 条知识库正文、案例、话术或卡片索引
- 可选：如自备同结构知识库，设置 `EMOCHAT_KB` 后运行
  - 长记录画像：`python scripts/emochat_analyze.py profile chat.txt --me "我"`
  - 追加人物描述：`--notes "..."` / `--notes-file notes.txt`；增量用 `--append`
  - 单条回复：`python scripts/emochat_analyze.py reply --message "..."`
  - 手动检索：`python scripts/emochat_search.py "关键词" --top 5`
- 安装：见 `adapters/installation.md`

本版可原样分享；不得加入知识库正文、用于商业服务、训练/微调或修改后再分发。
