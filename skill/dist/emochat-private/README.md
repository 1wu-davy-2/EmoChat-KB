# EmoChat 私有完整版

- 条目：589 条，12 个板块
- 入口：`SKILL.md`
- 长记录画像：`python scripts/emochat_analyze.py profile chat.txt --me "我" --json --timing`
- 追加人物描述：`--notes "对方 28 岁，回避型"` 或 `--notes-file notes.txt`
- 增量画像：`python scripts/emochat_analyze.py profile chat.txt --append`
- 单条回复：`python scripts/emochat_analyze.py reply --message "..." --profile profile.json --json --timing`
- 手动检索：`python scripts/emochat_search.py "关键词" --top 5`
- 安装：见 `adapters/installation.md`
- 索引：`references/index.md`、`references/board-*.md`、`references/search-index.pkl.gz`
- 机器可读：`references/entry-map.json`

本版仅供仓库作者本地/私有环境使用，不得向第三方分发、上传公共平台或用于对外服务。
知识库正文仍受仓库根目录 `LICENSE.txt` 约束。
