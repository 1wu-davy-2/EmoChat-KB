---
id: research-001
title: 调研 01:GitHub 可用于「情感聊天知识库」的开源项目与语料库
tags: [调研长文]
type: 调研长文
source: "本地调研笔记 调研/01-开源项目与语料.md(含全部来源URL)"
confidence: 高
---

> 调研长文层:知识库建库过程的原始调研报告,含完整来源链接,供深度检索与溯源。

# 调研 01:GitHub 可用于「情感聊天知识库」的开源项目与语料库

- 调研日期:2026-10-25
- 调研方式:WebSearch 多组关键词(中英文)+ WebFetch 抓取仓库页/README/raw 文件
- 边界执行:已排除 PUA/打压式/精神操控类内容项目(见 4.3);未评估任何涉诈骗项目

---

## 1. 概览表

| # | 仓库 | 星级 | 形态 | 许可证 | 可直接采集复用性 |
|---|------|------|------|--------|------------------|
| 1 | shengjidaguai-china/goutoujunshi(狗头军师) | 8.5k | 话术/知识文档库 + Skill | MIT | ★★★★★ 135 篇知识/话术文档,MIT,首推 |
| 2 | tomwong001/qingsheng-skill(情圣) | 187 | 话术文档 + 对话样本库 + Skill | MIT | ★★★★☆ 含 40 例实战对话样本库与 10 篇 reference 文档 |
| 3 | Mayuqi-crypto/HowToGetAlongWithGirls | 43 | 知识文档库 + Skill(中英双语) | MIT | ★★★★☆ knowledge-base 等多篇结构化中文文档 |
| 4 | Stanley-baby/love-expert(恋爱专家) | 27 | 话术模板/技巧文档 + Skill | MIT | ★★★☆☆ 含《恋爱技巧大全》《话术模板》两个 md,但术语偏 PUA 需筛选 |
| 5 | thu-coai/CDial-GPT(LCCC) | 2.0k | 对话语料数据集 | 代码 MIT;数据仅限科研 | 训练用,不适合检索库(记录) |
| 6 | scutcyr/CPED | 304 | 情感对话数据集 | Apache-2.0 | 训练用,带情感标注(记录) |
| 7 | linexjlin/GPTs | 32k | 泄露 GPTs prompt 合集 | 无许可证 | ★★☆☆☆ 仅作 prompt 设计思路参考,版权风险 |
| 8 | nanzh-19/LearnToLiveWithAGirl | 13 | 单篇 README 技巧长文 | 无许可证 | ★☆☆☆☆ 不建议直接复用,可作观点参考 |
| 9 | ixinzhi/loving-books-2022 | 308 | 电子书堆积(PDF/EPUB) | 无 | ✗ 含 PUA 资料+盗版书,排除 |
| 10 | hailiang-wang/chat-1(恋爱话术王) | 0 | Android App | 无 | ✗ 无可复用文本,排除 |

---

## 2. 项目详情

### 2.1 shengjidaguai-china/goutoujunshi(狗头军师)—— 首选采集源

- URL:https://github.com/shengjidaguai-china/goutoujunshi
- 星级:8.5k(870 forks),本调研中**质量与合规性最好的项目**
- 形态:Codex Skill 恋爱军师 + `references/` 知识库;工作流为「情绪承接 → 建档 → 检索知识 → 互惠/风险分析 → 给建议+话术+停止条件」
- 许可证:MIT(允许商用/修改/分发,需保留版权声明)
- 内容结构:
  - `references/knowledge/`:关系心理学、人格与情绪(MBTI/Big Five/依恋)、约会、沟通策略、PUA 风险与替代方案、性学亲密、婚姻家庭、法律安全(含中国婚姻家庭法律)、社会人文、恋爱哲学、分手特殊情境——共 135 条参考资料,按证据强度分级
  - `references/practical/`:23 篇实战话术文档(夸人、接话、化解尴尬、情绪价值回应、高情商拒绝、吵架理性处理、化被动为主动、退出决策等),含「三层话术编排、36 条话术骨架」
- 合规设计:明确「同意和退出权不可绕过」,PUA 手段必须同时交代风险与长期成本
- 采集建议:**优先采集 `references/practical/` 全部 23 篇 + `references/knowledge/` 中心理学/沟通类条目**,保留 MIT 版权声明

### 2.2 tomwong001/qingsheng-skill(情圣)

- URL:https://github.com/tomwong001/qingsheng-skill
- 星级:187(16 forks)
- 形态:Claude Code 中文恋爱教练 Skill(SKILL.md 约 170 行 + 10 篇 references);自述从私有课程语料蒸馏 5000+ 概念、1400+ 真实对话(原始语料**不在**仓库内)
- 许可证:MIT
- 内容结构(`skill/references/`):七阶段关系推进模型、IOI/IOD 信号、用户档案、7 平台 playbook(微信/探探/Soul/Bumble/青藤之恋等)、**40 个真实对话样本库(examples-library.md,按 7 阶段+挽回分类)**、心态概念、展示面诊断、挽回手册
- 采集建议:采集 `examples-library.md`(对话样本,适合做 few-shot/检索库)+ 七阶段与信号识别文档;个别样本含较强操控性话术,需按「尊重边界」标准过滤

### 2.3 Mayuqi-crypto/HowToGetAlongWithGirls(恋爱教练)

- URL:https://github.com/Mayuqi-crypto/HowToGetAlongWithGirls
- 星级:43
- 形态:Claude Skill 包,中文为主、每文件带英文镜像(`*.en.md`);自称 "coaching, not manipulation"
- 许可证:MIT
- 内容结构(`.claude/skills/dating-coach/references/`):knowledge-base(0 底层逻辑/1 认识搭讪/2 聊天/3 心理与信号/4 框架与废测/5 线下约会/6 形象展示面/7 确定关系)、lifecycle(全周期路线图)、chat-analysis、signal-patterns、damage-control(止损)、self-diagnosis、realistic-scenarios、hard-value-reality
- 合规设计:硬性底线——真诚优先、尊重意愿、没戏即止损,拒绝欺骗/操控/贬低/骚扰
- 采集建议:**`knowledge-base.md` 是现成的分主题知识库文本,可整篇采集**;signal-patterns、damage-control 亦佳

### 2.4 Stanley-baby/love-expert(恋爱专家)

- URL:https://github.com/Stanley-baby/love-expert
- 星级:27(4 forks)
- 形态:OpenCode/AI 助手 Skill;核心是 `references/恋爱技巧大全.md` 与 `references/话术模板.md` 两个 md 知识文件
- 许可证:MIT
- 内容:话术模板含开场白/推拉/约会/表白/高情商回复/冷读/框架等 14 节;术语体系明显借鉴 PUA 社区(推拉、废物测试、服从性测试、框架、冷读)
- 采集建议:可采集但**必须逐条筛除打压式/操控性条目**,保留开场白、话题展开、高情商回复等中性内容;优先级低于前三个

### 2.5 thu-coai/CDial-GPT(LCCC 中文对话语料)—— 数据集类,记录

- URL:https://github.com/thu-coai/CDial-GPT(HuggingFace:thu-coai/lccc;论文 arXiv:2008.03946)
- 星级:2.0k
- 形态:大规模清洗中文短文本对话语料 + 中文对话预训练模型。LCCC-base 约 680 万对话(微博来源);LCCC-large 约 1200 万对话(另合并豆瓣、贴吧、小黄鸡、青云等开源数据集),经脏词/颜文字/不连贯过滤
- 许可证:代码 MIT;数据与模型**仅限科研用途**
- 结论:体积大、噪声多,适合训练/微调,**不适合做检索知识库**;使用受科研限制,采集需谨慎

### 2.6 scutcyr/CPED(中文个性情感对话数据集)—— 数据集类,记录

- URL:https://github.com/scutcyr/CPED(论文 arXiv:2205.14727)
- 星级:304
- 形态:来自 40 部中国电视剧的 1.2 万对话/13.3 万语句,392 名说话人;标注 13 种情绪、3 类极性、大五人格、性别年龄、19 种对话行为、11 种场景
- 许可证:Apache-2.0(使用需引用论文)
- 结论:情感标注丰富,可用于训练情感识别/共情回复模型,或少量抽样做角色语气参考;非检索知识库素材

### 2.7 linexjlin/GPTs(泄露 GPTs prompt 合集)—— prompt 思路参考

- URL:https://github.com/linexjlin/GPTs
- 星级:32k
- 形态:`prompts/` 目录每 prompt 一个 md;情感相关包括 Girlfriend Emma、Virtual Sweetheart、AI Lover、子言女友、情感对话大师-帮你回复女生、骂醒恋爱脑等
- 许可证:**无许可证,且属未经授权泄露的系统提示词**
- 结论:不直接采集文本;只参考其 system prompt 的角色设定、边界设计、回复风格约束等设计思路。同类可参考 friuns2/BlackFriday-GPTs-Prompts(含「暖男生成器-快速回复女友消息」中文 prompt)

### 2.8 低价值/排除项

- **nanzh-19/LearnToLiveWithAGirl**(13★):单 README 技巧长文(聊天层次递进、三次邀约、肢体升级),无许可证默认保留所有权利;「设局制造情绪焦虑」等手法属操控性质,**不采集**,至多引述观点
- **ixinzhi/loving-books-2022**(308★)/getpua/lovebooks 等书仓:PDF/EPUB 电子书堆积,含大量 PUA 课程与盗版出版物,无许可证——**排除**
- **hailiang-wang/chat-1**(0★)、YangChengTeam/mplahs:Android/小程序应用代码,无可复用话术文本——排除
- she-love-me、goutoujunshi 等聊天记录**分析工具**是工具不是语料,不列入采集范围

---

## 3. 可采集内容清单(按优先级)

| 优先级 | 来源 | 采集目标 | 用途 | 许可要求 |
|--------|------|----------|------|----------|
| P0 | goutoujunshi `references/practical/`(23 篇) | 夸人/接话/情绪价值/高情商拒绝/吵架处理/化解尴尬/聊天引导等话术指南 | 检索知识库-沟通技巧类 | MIT,保留版权与许可声明 |
| P0 | goutoujunshi `references/knowledge/`(心理学/沟通/婚姻法律条目) | 依恋类型、互惠判断、冲突处理、关系心理学 | 检索知识库-原理类 | MIT,同上 |
| P1 | HowToGetAlongWithGirls `knowledge-base.md` | 分主题知识条目:底层逻辑/聊天/信号识别/约会/形象 | 检索知识库-按阶段分类 | MIT,保留声明 |
| P1 | qingsheng-skill `examples-library.md` | 40 例分阶段真实对话样本(场景→她说的→好回复→为什么) | few-shot 示例库/检索库-案例类 | MIT,保留声明;逐条过滤操控性样本 |
| P2 | qingsheng-skill 七阶段模型、IOI/IOD 信号、平台 playbook | 阶段框架与信号词典 | 知识库结构设计参考 | MIT |
| P2 | love-expert `references/` 两个 md | 开场白、话题展开、高情商回复(筛除推拉/废测/冷读条目) | 补充话术 | MIT,需二次筛选 |
| 记录 | LCCC / CPED | 大规模对话语料 | 仅训练用,不入检索库 | LCCC 数据科研限定;CPED Apache-2.0+引用 |
| 参考 | GPTs 情感类 prompt | system prompt 设计思路 | 不采集原文 | 无许可证,仅思路参考 |

---

## 4. 样例摘录(证明内容质量)

### 4.1 goutoujunshi — 《万能夸人的话术技巧:真诚认可的实用指南》

来源:https://raw.githubusercontent.com/shengjidaguai-china/goutoujunshi/main/references/practical/万能夸人的话术技巧:真诚认可的实用指南.md (实际抓取为 URL 编码路径)

```
### 一、底层逻辑(读懂"有效夸奖"的本质,避开敷衍陷阱)
#### 1. 认知基础:夸奖不是"客套",而是"精准看见对方的价值"
- 拆解4类常见夸人误区(附实例)
  - 空泛无细节:"你真棒""你太厉害了"(无具体指向,对方感受不到"你真的关注他",易觉得敷衍)
  - 过度夸张:"你这方案简直是完美,没人能比你做得更好"(夸大事实,反而让对方觉得不真实,甚至有压力)
  - 只夸"外在/结果",忽略"内在/过程":对方熬夜做方案,只说"方案通过了,真牛"(没看见对方的付出)
  - 对比式夸奖:"你比XX做得好多了,XX上次做的方案一团糟"(通过贬低他人抬高对方,既不尊重第三人,也让被夸者尴尬)
- 明确3类有效夸奖的核心原则:真诚优先、具体聚焦、贴合需求
```

评价:结构化、反操控、场景覆盖广(职场/家人/伴侣/朋友),直接可作为知识库「夸人与认可」条目。

### 4.2 qingsheng-skill — 《实战对话示例库》(examples-library.md)

来源:https://raw.githubusercontent.com/tomwong001/qingsheng-skill/main/skill/references/examples-library.md

```
# 实战对话示例库
给话术建议时,从对应阶段找相近场景做 few-shot 参考。每条:场景→她说的→好回复→为什么好。
先按真实互动目的和阶段筛选示例;示例中的'顺路'或邀约话术不能用来证明当前关系已经适合见面。
(分阶段:1开场搭讪 2制造吸引 3建立连接 4线上转线下 5约会升级 6约会中 7确立关系 + 挽回/冷激活)
```

评价:统一的「场景-原话-回复-理由」四元组格式,天然适合检索库;含「沉默不是同意,应停止动作」「拒绝见面后不再提」等边界条目,也混有少量强行升级话术,入库前需逐条审。

### 4.3 HowToGetAlongWithGirls — 《两性知识库》(knowledge-base.md)

来源:https://raw.githubusercontent.com/Mayuqi-crypto/HowToGetAlongWithGirls/HEAD/.claude/skills/dating-coach/references/knowledge-base.md

```
# 两性知识库
按主题组织,供「流程 B:知识问答」按需查阅。回答用户时**结合他的具体处境**重组这些知识,不要整段照搬。
> 这些方法源自恋爱教学流派,取其沟通/心态/形象的可借鉴部分。
> 运用时始终守 SKILL.md 的底线:真诚、尊重、自我成长为根。
(结构:0底层逻辑 / 1认识搭讪 / 2聊天 / 3女性心理与信号 / 4框架与废测 / 5线下约会 / 6形象展示面 / 7确定关系与长期相处)
```

评价:自带使用规范与伦理底线的分主题知识库,写作风格克制,适合整篇迁移后按条目拆分。

### 4.4 love-expert — 《恋爱话术模板大全》(references/话术模板.md)

来源:https://raw.githubusercontent.com/Stanley-baby/love-expert/main/references/话术模板.md (实际抓取为 URL 编码路径)

```
# 恋爱话术模板大全
本话术模板整理了追女生过程中常用的各类话术技巧,包含开场白、推拉句子、聊天话术、约会台词等。
建议结合具体场景灵活使用,切勿生搬硬套。
## 一、开场白话术
### 好奇心开场
> - "你知道吗,你和我认识的一个人好像。"
> - "我觉得你肯定没有男朋友。"
(共14节:开场白/推拉/聊天回复/话题展开/约会互动/废物测试应对/表白/高情商回复/禁忌/冷读/框架等)
```

评价:量大面广但推拉/废测/冷读/框架等章节偏 PUA 术语体系,只宜筛选性采集中性部分。

---

## 5. 结论

- **可直接采集**:goutoujunshi(MIT,8.5k★,135 篇知识+23 篇话术文档)为主干;HowToGetAlongWithGirls 的 knowledge-base.md 与 qingsheng-skill 的 examples-library.md 为两翼,三者均 MIT、均为结构化 Markdown、均自带伦理底线条款,可低成本人库。
- **需筛选后采集**:love-expert(MIT 但 PUA 术语浓度高)。
- **仅记录/参考**:LCCC、CPED(训练语料,非检索库);GPTs 泄露 prompt(仅借鉴设计思路,不采集原文)。
- **排除**:PUA/盗版电子书仓(loving-books-2022 等)、无许可证单篇长文(LearnToLiveWithAGirl)、纯应用代码仓(chat-1/mplahs)。
