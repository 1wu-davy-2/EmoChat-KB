# -*- coding: utf-8 -*-
"""EmoChat 聊天记录画像与单条回复快速通道。

用法:
    python emochat_analyze.py profile chat.txt --me "我"
    python emochat_analyze.py profile chat.txt --me "我" --notes "对方 30 岁，回避型"
    python emochat_analyze.py profile chat.txt --append --json
    python emochat_analyze.py reply --message "先转 5000 保证金，晚上视频给我看看" --profile profile.json
    python emochat_analyze.py reply --message "嗯" --profile profile.json --json

设计目标:
- 100 条以上记录一次解析，输出压缩画像与卡片包，避免逐条读入上下文。
- 单条消息一次命令完成意图识别、风险判断、卡片检索与三版回复骨架。
- 默认打码手机号、身份证、银行卡、邮箱与微信号。
"""
import argparse
import hashlib
import json
import re
import sys
import time
from collections import Counter, OrderedDict
from datetime import datetime
from pathlib import Path

import emochat_core as core

SESSION_GAP_DEFAULT = 360
MAX_QUERIES = 6

QUESTION_RE = re.compile(
    r"[?？]|(?:吗|呢|怎么|为什么|要不要|是不是|能不能|好不好|行不行|有没有|多少|哪里|什么时候|谁)"
)
MEDIA_RE = re.compile(r"^\[(?:图片|表情|语音|视频|文件|位置|链接|动画表情|红包|转账|聊天记录|名片)\]$")
SYSTEM_RE = re.compile(r"撤回了一条消息|消息已发出|以下为新消息|加入了群聊|退出了群聊|你已添加了|现在可以开始聊天")
SEPARATOR_RE = re.compile(r"^\s*(?:-{2,}|={2,}|\*{2,})\s*$")
DATE_ONLY_RE = re.compile(
    r"^\s*(?:\d{4}[-/]\d{1,2}[-/]\d{1,2}(?:[ T]\d{1,2}:\d{2}(?::\d{2})?)?|\d{1,2}:\d{2}(?::\d{2})?)\s*$"
)
TS_PATTERN = (
    r"(?:\d{4}[-/]\d{1,2}[-/]\d{1,2}(?:[ T]\d{1,2}:\d{2}(?::\d{2})?)?"
    r"|\d{1,2}:\d{2}(?::\d{2})?)"
)
BRACKET_COLON_RE = re.compile(r"^\s*\[(?P<ts>[^\]]{1,40})\]\s*(?P<speaker>[^:：\n]{1,24})[:：]\s*(?P<text>.*)$")
TS_COLON_RE = re.compile(r"^\s*(?P<ts>" + TS_PATTERN + r")\s+(?P<speaker>[^:：\n]{1,24})[:：]\s*(?P<text>.*)$")
COLON_RE = re.compile(r"^\s*(?P<speaker>[^:：\n]{1,24})[:：]\s*(?P<text>.*)$")
TS_HEADER_RE = re.compile(r"^\s*(?P<ts>" + TS_PATTERN + r")\s+(?P<speaker>.{1,24})\s*$")
SPEAKER_TS_RE = re.compile(r"^\s*(?P<speaker>.{1,24})\s+(?P<ts>" + TS_PATTERN + r")\s*$")

NARRATIVE_PREFIXES = (
    "他说", "她说", "我说", "你说", "备注", "时间", "地点", "内容", "标题",
    "主题", "注意", "提示", "例如", "比如", "如果", "因为", "所以", "但是",
    "然后", "结果", "总结", "分析", "回复", "话术", "问题", "答案", "场景",
)
COLD_SET = {
    "嗯", "哦", "喔", "好", "行", "随便", "在忙", "忙", "睡了", "晚安",
    "哈哈", "呵", "没事", "算了", "知道了",
}
COMMIT_TERMS = ("见面", "下次", "周末", "哪天", "有空", "一起", "约", "来")
CANCEL_TERMS = ("改天", "下次吧", "再说", "最近忙", "没空", "去不了", "临时有事", "看情况")
SEXUAL_TERMS = (
    "视频", "裸聊", "裸照", "私密照", "发张照片", "看看你", "开房", "来我家",
    "睡觉", "做爱", "上床", "文爱", "语爱", "性关系", "亲密", "身体",
)
PRESSURE_TERMS = (
    "不拍就", "不发就", "不答应就", "不给我就", "不爱我", "不信任", "证明",
    "必须", "应该", "别人都", "扫兴", "拒绝我", "要你", "听话", "乖",
)
REFUSAL_TERMS = ("不要", "不想", "别", "停", "不舒服", "拒绝", "不可以", "到此为止", "别再")
HEARSAY_MARKERS = ("他", "她", "对方", "TA", "ta", "他们", "她们")
ACTOR_SIGNALS = {
    "threat", "sextortion", "scam", "stalking", "privacy", "control",
    "financial", "gaslight", "lovebomb", "transactional", "substance",
    "power_gap", "affair", "online_intimacy",
}

SIGNALS = OrderedDict([
    ("minor", {"label": "未成年人", "weight": 100, "severity": "紧急",
               "terms": ("未成年", "初中生", "小学生")}),
    ("selfharm", {"label": "自伤/自杀风险", "weight": 100, "severity": "紧急",
                  "terms": ("自杀", "不想活", "活着没意思", "割腕", "跳楼", "结束生命", "去死"),
                  "exclude": (r"(?:你|他|她|你们|让他|让她|让他们).{0,2}(?:去死|该死|活该|不想活)",)}),
    ("violence", {"label": "暴力/强迫", "weight": 85, "severity": "紧急",
                  "terms": ("打我", "动手", "掐我", "扇我", "砸东西", "家暴", "强迫我", "强奸", "迷药", "下药"),
                  "exclude": (r"(?:不|没)(?:会|敢|想|能)?打(?:我|你|人|过)",)}),
    ("crisis", {"label": "即时危险/极端威胁", "weight": 90, "severity": "紧急",
                "terms": ("杀了你", "弄死", "打死", "同归于尽", "堵你", "不让你走",
                          "现在就过来", "去死")}),
    ("threat", {"label": "威胁/曝光/勒索", "weight": 60, "severity": "高",
                "terms": ("曝光", "发出去", "传播", "告诉你家人", "去你单位", "举报你",
                          "不转就", "不拍就", "给钱", "删图费", "你等着")}),
    ("sextortion", {"label": "私密影像/录屏/传播", "weight": 55, "severity": "高",
                    "terms": ("录屏", "截图", "偷拍", "偷录", "投屏", "裸聊", "裸照", "私密照")}),
    ("scam", {"label": "诈骗/转账/投资", "weight": 50, "severity": "高",
              "terms": ("转账", "借钱", "投资", "充值", "提现", "验证码",
                        "屏幕共享", "刷单", "博彩", "虚拟币", "保证金", "手续费",
                        "内部消息", "稳赚", "安全账户", "公检法", "解冻", "代付", "垫付",
                        "转我", "打钱", "汇款", "先付", "周转")}),
    ("stalking", {"label": "跟踪/定位/骚扰", "weight": 45, "severity": "高",
                  "terms": ("跟踪", "蹲守", "楼下", "公司门口", "查岗", "小号", "换号",
                            "联系你朋友", "定位", "共享位置")}),
    ("privacy", {"label": "隐私/账号/影像边界", "weight": 30, "severity": "中",
                 "terms": ("密码", "账号", "登录", "摄像头", "隐私", "共享屏幕")}),
    ("control", {"label": "控制/占有", "weight": 25, "severity": "中",
                 "terms": ("不许", "必须", "只能", "报备", "删好友", "查手机", "穿什么",
                           "管你", "不准", "听我的", "离开我")}),
    ("financial", {"label": "经济控制/索取", "weight": 25, "severity": "中",
                   "terms": ("工资", "上交", "共同账户", "花我的钱", "经济控制", "生活费")}),
    ("gaslight", {"label": "煤气灯/否定感受", "weight": 20, "severity": "中",
                  "terms": ("你想多了", "你太敏感", "你记错了", "没有的事", "你疯了",
                            "别小题大做", "我都是为你好", "你太情绪化")}),
    ("power_gap", {"label": "权力不对等", "weight": 20, "severity": "中",
                   "terms": ("老师", "导师", "上司", "老板", "领导", "教练", "咨询师",
                             "房东", "实习生", "下属")}),
    ("substance", {"label": "酒精/药物风险", "weight": 40, "severity": "高",
                   "terms": ("喝醉", "灌酒", "下药", "迷药", "断片")}),
    ("transactional", {"label": "交易型关系", "weight": 20, "severity": "中",
                       "terms": ("包养", "给钱", "付费", "赞助", "价格", "交易", "生活费")}),
    ("lovebomb", {"label": "爱轰炸/过快承诺", "weight": 15, "severity": "中",
                  "terms": ("命中注定", "灵魂伴侣", "你是唯一", "一辈子", "马上结婚",
                            "从没这么", "完美", "一见钟情")}),
    ("affair", {"label": "第三者/已婚结构", "weight": 10, "severity": "灰色",
                "terms": ("已婚", "老婆", "老公", "第三者", "出轨", "婚外", "原配", "开放关系")}),
    ("online_intimacy", {"label": "线上亲密/视频语音", "weight": 5, "severity": "灰色",
                         "terms": ("视频", "语音", "裸聊", "文爱", "语爱", "屏幕共享", "直播", "私密")}),
])

THEMES = [
    {"name": "FWB/休闲关系",
     "terms": ("FWB", "炮友", "休闲关系", "不承诺", "各取所需", "开放式", "暧昧"),
     "queries": ("FWB 公平 情绪劳动", "休闲关系 边界 退出", "FWB 转正 关系定义")},
    {"name": "异地/网恋",
     "terms": ("异地", "网恋", "奔现", "见不到", "距离"),
     "queries": ("异地 网恋 奔现 安全", "异地 关系 节奏 信任")},
    {"name": "线上亲密",
     "terms": ("语音", "视频", "裸聊", "文爱", "语爱", "屏幕共享", "直播", "私密"),
     "queries": ("线上亲密 语音 视频 边界", "视频亲密 录屏 停止")},
    {"name": "性沟通/同意",
     "terms": ("做爱", "上床", "性关系", "避孕", "安全套", "同意", "拒绝", "疼", "不舒服"),
     "queries": ("性沟通 同意 拒绝 话术", "性沟通 同意 边界 停止")},
    {"name": "冲突/修复",
     "terms": ("吵架", "生气", "误会", "道歉", "冷战", "冲突", "修复"),
     "queries": ("冲突 道歉 修复", "冷战 沟通 边界")},
    {"name": "分手/止损",
     "terms": ("分手", "断联", "拉黑", "复合", "止损", "退出"),
     "queries": ("分手 断联 止损", "复合 判断 边界")},
    {"name": "金钱/交易",
     "terms": ("转账", "借钱", "投资", "包养", "付费", "保证金", "代付", "刷单"),
     "queries": ("诈骗 转账 杀猪盘 识别", "交易型 关系 边界")},
    {"name": "操控/情感勒索",
     "terms": ("PUA", "打压", "忽冷忽热", "爱轰炸", "煤气灯", "情感勒索", "控制", "威胁"),
     "queries": ("情感操控 识别 回应", "忽冷忽热 推拉 边界")},
    {"name": "隐私/影像",
     "terms": ("照片", "视频", "录屏", "截图", "密码", "定位", "隐私", "账号"),
     "queries": ("私密影像 录屏 隐私", "账号 定位 边界")},
    {"name": "权力差",
     "terms": ("老师", "导师", "上司", "老板", "领导", "教练", "咨询师", "房东", "实习生", "下属"),
     "queries": ("权力差 师生 上下级 边界", "权力不对等 同意 投诉")},
    {"name": "第三者/关系结构",
     "terms": ("已婚", "老婆", "老公", "第三者", "出轨", "开放关系", "形婚"),
     "queries": ("第三者 已婚 边界", "开放关系 契约 沟通")},
    {"name": "依恋/性格",
     "terms": ("回避型", "焦虑型", "依恋", "MBTI", "星座", "内向", "外向"),
     "queries": ("依恋 回避 焦虑 沟通", "性格 沟通 适配")},
]

RISK_QUERIES = {
    "minor": ("未成年人 保护 报警 转介", "中国法律 安全 危机转介 报警"),
    "selfharm": ("自杀风险 识别 转介 陪伴", "心理援助 12356 危机"),
    "violence": ("暴力 安全 求助 110", "家暴 安全计划"),
    "crisis": ("威胁 取证 报警 安全", "人身安全 求助 110 证据"),
    "threat": ("威胁 曝光 取证 报警", "私密影像 勒索 应对"),
    "sextortion": ("私密影像 录屏 传播 应对", "视频亲密 录屏 停止"),
    "scam": ("诈骗 转账 杀猪盘 识别", "借钱 边界 拒绝 话术"),
    "stalking": ("跟踪 定位 骚扰 报警", "隐私 账号 安全"),
    "privacy": ("隐私 账号 影像 边界", "私密影像 录屏 停止"),
    "control": ("控制 占有 边界 回应", "冷暴力 情感操控 识别"),
    "financial": ("经济控制 借钱 边界", "金钱 关系 公平"),
    "gaslight": ("煤气灯 否定 感受 识别", "情感操控 回应 边界"),
    "power_gap": ("权力差 师生 上下级 边界", "权力不对等 同意 投诉"),
    "substance": ("酒精 迷药 安全 求助", "喝醉 同意 边界"),
    "transactional": ("交易型 关系 边界", "包养 资源 边界"),
    "lovebomb": ("爱轰炸 过快承诺 识别", "暧昧 推进 节奏"),
    "affair": ("第三者 已婚 边界", "开放关系 契约 沟通"),
    "online_intimacy": ("线上亲密 语音 视频 边界", "视频亲密 录屏 停止"),
    "consent": ("性沟通 同意 拒绝 话术", "同意 撤回 边界 停止"),
    "sexual_pressure": ("性沟通 同意 拒绝 话术", "线上性沟通 停止 边界"),
}

STAGE_QUERIES = {
    "初识/早期": ("开场 接话 聊天 节奏", "兴趣信号 判断 互惠"),
    "暧昧": ("暧昧 推进 关系定义", "兴趣信号 判断 邀约"),
    "休闲关系/暧昧": ("FWB 公平 情绪劳动", "休闲关系 边界 退出"),
    "异地/网恋": ("异地 网恋 奔现 安全", "异地 关系 节奏 信任"),
    "亲密/同意": ("性沟通 同意 拒绝 话术", "性沟通 同意 边界 停止"),
    "冲突修复": ("冲突 道歉 修复", "冷战 沟通 边界"),
    "分手/降温": ("分手 断联 止损", "复合 判断 边界"),
    "关系定义/结构": ("关系定义 专一 期待", "第三者 已婚 边界"),
    "危机/止损": ("危机 安全 求助", "威胁 曝光 取证 报警"),
    "熟悉/稳定": ("长期关系 沟通 边界", "关系节奏 维护"),
}

INTENTS = [
    {"id": "crisis", "label": "危机/安全风险", "risk": 5,
     "terms": ("自杀", "不想活", "活着没意思", "割腕", "跳楼", "杀", "弄死", "打死",
               "家暴", "打我", "掐我", "强奸", "强迫", "迷药", "下药", "同归于尽"),
     "patterns": (r"不.*就.*(?:死|自杀|弄死|杀|同归于尽)", r"(?:杀了你|弄死|打死|同归于尽|堵你|不让你走)"),
     "queries": ("危机 安全 求助 110 120", "自伤 风险 陪伴 转介", "威胁 曝光 取证 报警"),
     "strategy": "先确认当前是否安全，再处理聊天；不在危险环境里摊牌。",
     "moves": ("确认人身安全与是否有人陪同", "保留威胁、影像、转账证据", "联系 110/120/12356 或可信亲友"),
     "avoid": ("不要单独见面", "不要满足勒索或转账", "不要以暴制暴或反向跟踪"),
     "drafts": (),
     "needs": ("你现在安全吗？是否有人在你身边？", "对方是否掌握你的住址、单位或影像？")},
    {"id": "threat", "label": "威胁/曝光/勒索", "risk": 4,
     "terms": ("曝光", "发出去", "告诉你家人", "去你单位", "举报你", "你等着", "不转就",
               "不拍就", "给钱", "删除", "弄死"),
     "patterns": (r"不.*(?:转|给|拍|发).*(?:就|的话).*(?:发|曝光|传播|告诉你|弄死)",
                  r"(?:已经|马上|现在).*(?:发|曝光|传播)"),
     "queries": ("威胁 曝光 取证 报警", "私密影像 勒索 应对", "敲诈 勒索 保留证据"),
     "strategy": "不按威胁做事，先保留证据、评估传播风险，再决定平台举报或报警。",
     "moves": ("截图保存威胁内容、账号与时间", "不转账、不继续发送影像", "平台举报并咨询 110/96110"),
     "avoid": ("不要单独见面谈判", "不要删除证据", "不要反向曝光对方"),
     "drafts": ("我不会因为威胁做任何事。",
                "我已经保存了记录；如果内容被传播，我会平台举报并报警。",
                "不要再联系我，有事通过平台或警方。"),
     "needs": ("对方是否已经传播？传播到哪里？", "你是否已转账或发送影像？")},
    {"id": "money", "label": "金钱/转账/投资", "risk": 3,
     "terms": ("转账", "借钱", "借我", "转我", "打钱", "汇款", "手头紧", "周转", "急用",
               "投资", "平台", "充值", "提现", "验证码", "保证金", "手续费", "代付",
               "垫付", "刷单", "博彩", "虚拟币", "稳赚", "内部消息",
               "一起投", "带你赚", "包赚", "保本", "高回报"),
     "patterns": (r"(?:借|转|打|汇|付|给).*(?:\d+|钱|块|千|万)",
                  r"(?:投资|平台).*(?:稳|收益|内部)",
                  r"(?:手头紧|周转|急用|保证金|手续费|验证码|屏幕共享)",
                  r"(?:稳赚|包赚|保本|高回报|带你赚|一起投)",
                  r"(?:发|转|要).{0,3}红包.{0,4}(?:给我|来|吧)"),
     "queries": ("诈骗 转账 杀猪盘 识别", "借钱 边界 拒绝 话术", "金钱 关系 公平"),
     "strategy": "先停止任何转账与验证码操作；关系问题和资金安全分开处理。",
     "moves": ("明确不转账、不代付、不给验证码", "核实对方身份与资金用途", "已转账则联系银行/96110"),
     "avoid": ("不要为了证明信任转账", "不要屏幕共享", "不要按对方指引去陌生平台投资"),
     "drafts": ("钱的事我不参与，也不会转账。",
                "我不会给验证码、不会屏幕共享，也不会代付。",
                "如果你继续提钱，我只能停止联系并向平台或警方咨询。"),
     "needs": ("你是否已经转账？金额与平台是什么？", "对方是否引导你投资、刷单或共享屏幕？")},
    {"id": "sexual_request", "label": "性/影像请求或施压", "risk": 3,
     "terms": ("视频", "裸聊", "裸照", "私密照", "发张照片", "看看你", "开房", "来我家",
               "睡觉", "做爱", "上床", "文爱", "语爱", "别人都", "保守", "扫兴",
               "不够爱我", "不够喜欢我", "不信任我", "脱光", "脱掉", "不穿"),
     "patterns": (r"(?:发|给).*(?:照片|视频).*(?:看看|证明)",
                  r"(?:不|别).*(?:就|就是|才).*(?:不爱|不喜欢|不信任)",
                  r"别人都", r"(?:必须|应该).*(?:视频|照片|拍|发|做|上床)",
                  r"(?:脱|裸).{0,3}(?:光|聊|体|照)"),
     "queries": ("性沟通 同意 拒绝 话术", "性沟通 同意 边界 停止", "私密影像 录屏 停止"),
     "strategy": "把同意与影像边界说清楚；拒绝不需要理由，也不需要补偿。",
     "moves": ("确认双方自愿、清醒、可随时停止", "不接受录屏、截图、投屏", "对方施压时结束话题"),
     "avoid": ("不要用影像证明信任", "不要因为已经聊得深就默认同意", "不要在被施压时妥协"),
     "drafts": ("这个话题我暂时不想聊，换个话题吧。",
                "我需要先确认我们都在自愿、清醒、可随时停止的前提下再谈这个。",
                "不做、不拍、不录，这是我的边界；越界我会结束对话。"),
     "needs": ("对方是否在施压或要求影像？", "你们是否已经确认过彼此的边界？")},
    {"id": "boundary", "label": "对方在设边界", "risk": 1,
     "terms": ("不要", "不想", "别再", "别这样", "别发", "别拍", "别碰", "别说", "别继续",
               "停止", "不舒服", "拒绝", "不可以", "到此为止"),
     "patterns": (r"(?:我)?(?:不想|不要|别再|停止|不舒服|不可以|拒绝|到此为止)",
                  r"(?:^|[\s，。！!？?]|你|我|请|先|现在|马上)别(?!人|处|的)"),
     "queries": ("尊重 拒绝 停止 话术", "边界 重申 沟通", "接受 拒绝 不追问"),
     "strategy": "把这句话当成完整答案：不追问、不谈判、不换角度施压。",
     "moves": ("先明确收到并尊重", "停止当前话题或动作", "必要时道歉并说明不会再提"),
     "avoid": ("不要追问理由", "不要说对方欲擒故纵", "不要用礼物或情绪换同意"),
     "drafts": ("好，我知道了，不会继续。",
                "谢谢你说清楚，我尊重你的边界。",
                "如果是我让你不舒服了，我道歉，并且不会再提。"),
     "needs": ("对方具体不想继续的是哪件事？", "你是否已经停止并给出空间？")},
    {"id": "control", "label": "控制/占有", "risk": 2,
     "terms": ("不许", "必须", "只能", "报备", "删好友", "查手机", "穿什么", "管你",
               "不准", "听我的", "离开我", "定位", "共享位置", "秒回", "随时回"),
     "patterns": (r"(?:必须|只能|不许|不准).*(?:听|做|去|见|穿)",
                  r"(?:定位|位置).{0,6}(?:开着|给我|发我|一直|共享)"),
     "queries": ("控制 占有 边界 回应", "情感操控 识别 边界", "查手机 定位 隐私"),
     "strategy": "把控制行为和关心分开；先设具体边界，再看对方是否尊重。",
     "moves": ("指出具体行为与你的感受", "明确哪些信息与社交由你自己决定", "重复越界时拉开距离"),
     "avoid": ("不要用服从换和平", "不要逐条自证", "不要让对方替你删朋友"),
     "drafts": ("关心可以，但查手机和删好友我不接受。",
                "我需要保留自己的社交和隐私；如果你不放心，我们可以谈信任，但不能用控制解决。",
                "如果继续用离开或惩罚来要求我服从，我会先暂停这段关系。"),
     "needs": ("对方具体控制了哪些事？", "你拒绝后对方如何反应？")},
    {"id": "gaslight", "label": "煤气灯/否定感受", "risk": 2,
     "terms": ("你想多了", "你太敏感", "你记错了", "没有的事", "你疯了", "别小题大做",
               "我都是为你好", "你太情绪化"),
     "patterns": (r"(?:你|别).*(?:想多|敏感|记错|小题大做|情绪化)",),
     "queries": ("煤气灯 否定 感受 识别", "情感操控 回应 边界", "自证 停止 边界"),
     "strategy": "不争论谁记性好；把事实写下来，减少自证，观察对方是否持续否定。",
     "moves": ("记录具体时间与原话", "用“我看到/我听到”陈述事实", "重复发生时拉开距离"),
     "avoid": ("不要反复解释到崩溃", "不要接受“你太敏感”作为结论", "不要为对方的情绪负责"),
     "drafts": ("我们可以对事实有不同记忆，但我不接受‘你想多了’这种说法。",
                "我把当时的话记下来了，我们可以按事实核对，而不是互相指责。",
                "如果每次我表达感受都被说成敏感，我会先暂停这段对话。"),
     "needs": ("对方是否反复否定你的记忆或感受？", "你是否保留了具体原话与时间？")},
    {"id": "guilt", "label": "情感勒索/愧疚施压", "risk": 2,
     "terms": ("你都不", "你是不是不爱我", "我都为你", "你欠我", "随便你", "算了",
               "你走吧", "我为你付出", "你没良心"),
     "patterns": (r"(?:你|我).*(?:都为你|欠我|没良心|不爱我)", r"(?:算了|随便你|你走吧)",
                  r"求你了?.{0,8}(?:机会|原谅|别走|别报|别说|最后一次)",
                  r"再给.{0,4}一次机会"),
     "queries": ("情感勒索 识别 回应", "愧疚 边界 沟通", "付出 公平 关系"),
     "strategy": "理解对方失望，但不因为愧疚承诺做不到的事；把具体问题与情绪施压分开。",
     "moves": ("先承认对方不舒服", "明确你能做与不能做的", "把“你欠我”换成具体请求"),
     "avoid": ("不要用补偿换平静", "不要接受无限期自责", "不要承诺做不到的事"),
     "drafts": ("我理解你不高兴，但我不会因为愧疚承诺我做不到的事。",
                "我们可以讨论具体问题，但不用‘你欠我’的方式。",
                "如果继续用这种方式，我会先暂停对话。"),
     "needs": ("对方具体在要求你做什么？", "你是否因为愧疚答应了不想做的事？")},
    {"id": "withdraw", "label": "分手/断联/降温", "risk": 1,
     "terms": ("分手", "冷静", "分开", "别再联系", "拉黑", "删了", "消失", "断联",
               "不合适", "到此为止"),
     "patterns": (r"(?:别再|不要).*(?:联系|找我)", r"(?:我们)?(?:分手|冷静|分开)"),
     "queries": ("分手 断联 止损", "复合 判断 边界", "接受 结束 退出"),
     "strategy": "先确认这是明确决定还是情绪表达；无论哪种，都不追加消息、不逼对方立刻回答。",
     "moves": ("用一句话确认收到", "给彼此空间，不在深夜谈判", "需要结束就明确结束方式"),
     "avoid": ("不要连发消息", "不要用自伤或威胁挽留", "不要通过朋友施压"),
     "drafts": ("好，我尊重你的决定。",
                "我需要一个明确的结束，而不是消失；如果这是你的决定，我会接受。",
                "那我们先停在这里；如果以后想联系，再说。"),
     "needs": ("对方是明确分手，还是在情绪中说的？", "你们是否还有共同事务需要处理？")},
    {"id": "apology", "label": "道歉/修复", "risk": 0,
     "terms": ("对不起", "抱歉", "我错了", "是我的问题", "我不该"),
     "patterns": (r"(?:对不起|抱歉|我错了|我不该)",),
     "queries": ("道歉 修复 冲突", "接受 道歉 边界", "修复 行为 改变"),
     "strategy": "接受道歉不等于立刻恢复信任；看具体行为是否改变。",
     "moves": ("说清你受到的影响", "区分道歉与保证", "设定观察期与停止条件"),
     "avoid": ("不要立刻说没事", "不要用原谅换对方回头", "不要反复翻旧账而不设边界"),
     "drafts": ("我听到了你的道歉。",
                "我需要的是以后不再发生，而不只是这句话。",
                "我可以继续聊，但如果再出现同样的事，我会退出。"),
     "needs": ("对方是否说清了自己做错了什么？", "你需要的修复动作是什么？")},
    {"id": "test", "label": "试探/关系确认", "risk": 1,
     "terms": ("你是不是", "你老实说", "你和她", "你和他", "谁重要", "如果我和",
               "你是不是喜欢", "你到底", "你老婆", "你老公", "你女朋友", "你男朋友",
               "你对象", "你前任", "你 ex"),
     "patterns": (r"(?:你|他|她).*(?:谁重要|老实说|到底)",),
     "queries": ("关系定义 沟通 专一", "试探 边界 回应", "嫉妒 前任 边界"),
     "strategy": "不接无限试探；把问题换成可直接回答的关系定义与边界。",
     "moves": ("回答能回答的部分", "说明你不接受试探式审问", "直接谈专一与期待"),
     "avoid": ("不要编故事安抚", "不要反问式攻击", "不要用嫉妒证明爱"),
     "drafts": ("我不想用试探来确认关系，我们可以直接说各自要什么。",
                "我和对方之间没有你担心的那种关系；但你如果一直不信，我们需要谈信任。",
                "如果你需要的是专一，我们可以明确；如果不是，也请直接说。"),
     "needs": ("对方具体在担心什么？", "你们是否谈过专一与公开？")},
    {"id": "define", "label": "关系定义/确认", "risk": 0,
     "terms": ("算什么关系", "什么关系", "啥关系", "确认关系", "官宣", "男女朋友",
               "在一起吗", "是不是在一起", "我们算"),
     "patterns": (r"算(?:什么|啥)[^，。？?]{0,6}关系",
                  r"我们(?:是|算)[^，。？?]{0,8}(?:朋友|关系|什么)",
                  r"(?:确认|公开|官宣)[^，。？?]{0,4}关系"),
     "queries": ("关系定义 沟通 专一", "确认关系 表白 时机", "关系 阶段 推进 节奏"),
     "strategy": "直接给定义，不用暧昧替代答案；说清你要什么、能接受什么、什么时候要答复。",
     "moves": ("先说你自己的定义与期待", "问对方要同一个明确答复", "给出可接受的时间点"),
     "avoid": ("不要用“随便你”回避", "不要用试探或嫉妒逼答案", "不要在定义前继续升级亲密"),
     "drafts": ("我想明确一下：我理解我们是 [你的定义]。你是怎么看的？",
                "我不太想停在模糊里。如果你也想认真交往，我们就确认；如果不想，也请直接说。",
                "我需要一句明确的话：我们是男女朋友，还是只是朋友？我按你的答案决定下一步。"),
     "needs": ("你们线下见过几次、聊了多久？", "对方此前是否回避过这个话题？")},
    {"id": "cancel", "label": "取消/推迟见面", "risk": 0,
     "terms": ("改天", "下次", "最近忙", "没空", "去不了", "临时有事", "再说吧", "看情况"),
     "patterns": (r"(?:改天|下次|最近忙|没空|去不了|临时有事|再说)",
                  r"(?:加班|忙|有事|累了).{0,6}(?:改天|下次|去不了|不去了|再说|取消)"),
     "queries": ("邀约 取消 低压力 回复", "被拒绝 邀约 体面 退出", "兴趣信号 判断 邀约"),
     "strategy": "接受这次取消，不追问、不施压；给一次具体的替代时间，再观察是否兑现。",
     "moves": ("表示收到并给空间", "给一个具体替代时间", "连续取消则降低投入"),
     "avoid": ("不要连发质问", "不要用“你不来就是不喜欢我”施压", "不要立刻换更贵的安排"),
     "drafts": ("好，知道了。你先忙，等你有空再约。",
                "有点失望，不过理解。你大概什么时候方便？",
                "如果最近都不方便，就先不安排了；等你想见再说。"),
     "needs": ("这是第几次取消？", "对方是否给过替代时间并兑现？")},
    {"id": "invite", "label": "邀约/推进见面", "risk": 0,
     "terms": ("出来", "见面", "吃饭", "看电影", "周末", "有空", "一起", "来我家",
               "去酒店", "哪天", "约"),
     "patterns": (r"(?:周末|哪天|有空).*(?:见|吃|看电影|出来)", r"(?:一起|来我家|去酒店)"),
     "queries": ("邀约 见面 具体 时间 地点", "邀约 安全 公共场所", "关系推进 节奏 退路"),
     "strategy": "具体、轻量、可拒绝；首次见面优先公共场所，并给彼此退路。",
     "moves": ("给时间、地点、活动三个要素", "明确可以拒绝", "首次见面安排在公共场所"),
     "avoid": ("不要把见面当考核", "不要临时改到私密空间", "不要用接送掌握对方行踪"),
     "drafts": ("可以呀，[时间] 我方便，[地点/活动] 你更想哪个？",
                "我想见你，不过这周只有 [时间] 有空；如果那天不行，我们换下周。",
                "见面可以，但我想先在公共场所，时间地点定好再去。"),
     "needs": ("你们是否已经线下见过？", "对方对见面是主动还是回避？")},
    {"id": "flirt", "label": "暧昧/好感表达", "risk": 0,
     "terms": ("想你", "喜欢你", "宝贝", "亲爱的", "抱抱", "亲亲", "可爱", "好看",
               "心动", "暧昧", "想见你"),
     "patterns": (r"(?:喜欢|想|爱).*(?:你)", r"(?:宝贝|亲爱的|抱抱|亲亲)",
                  r"(?:你|我)(?:是不是)?(?:喜欢|爱|想)(?:我|你)"),
     "queries": ("暧昧 回应 推进", "兴趣信号 判断 互惠", "关系定义 沟通 节奏"),
     "strategy": "接住情绪，但不用暧昧替代关系定义；推进时保持小步与可撤回。",
     "moves": ("回应具体的好感", "给一个轻量下一步", "需要时直接谈关系定义"),
     "avoid": ("不要用忽冷忽热制造焦虑", "不要用暧昧吊着对方", "不要承诺做不到的未来"),
     "drafts": ("你这么说我会当真的。",
                "我也挺喜欢和你聊的；不过我想慢慢来。",
                "我可以接住你的暧昧，但不想只停在暧昧；你怎么看？"),
     "needs": ("你们是否谈过关系定义？", "对方是否只在自己方便时出现？")},
    {"id": "cold", "label": "冷淡/短回复", "risk": 0,
     "terms": ("嗯", "哦", "喔", "随便", "在忙", "睡了", "晚安",
               "没事", "算了", "知道了"),
     "patterns": (r"^(?:嗯+|哦+|喔+|好+|行+|呵+|哈+|在忙|忙|睡了|晚安|随便|算了|没事|知道了)[。.!！?？]*$",),
     "queries": ("已读不回 变冷 判断", "低压力 确认 不连发", "停止 追加 消息"),
     "strategy": "先区分忙、累和持续降温；只做一次低压确认，不连发、不质问。",
     "moves": ("给一次低压确认", "停止追加消息", "把注意力收回自己的生活"),
     "avoid": ("不要连发", "不要用消失或吃醋制造失去感", "不要把一次短回复定性为不爱"),
     "drafts": ("好，那你先忙。",
                "感觉你今天不太想聊，我就不追问了；想说的时候找我。",
                "我需要一点回应来知道你的想法。如果现在不方便，晚点再说；一直这样我会按降温处理。"),
     "needs": ("这是单次还是持续 1-2 周的模式？", "对方最近是否有明确的外部压力？")},
    {"id": "question", "label": "询问/信息确认", "risk": 0,
     "terms": (),
     "patterns": (),
     "queries": ("聊天 接话 延续 话题", "回答 问题 具体 追问", "兴趣信号 判断 互惠"),
     "strategy": "先直接回答，再补一个具体细节，最后给一个轻量反问；不要绕。",
     "moves": ("正面回答", "给具体信息", "用一个轻问题延续"),
     "avoid": ("不要答非所问", "不要用试探回击", "不要长篇解释"),
     "drafts": ("可以，[具体回答]。你呢？",
                "我这边是 [具体情况]；你是想了解哪一部分？",
                "这个问题我想直接说：[回答]。如果我有没说清的，你再问。"),
     "needs": ("对方问的是事实、态度还是关系定义？",)},
    {"id": "neutral", "label": "普通对话", "risk": 0,
     "terms": (),
     "patterns": (),
     "queries": ("聊天 回复 推进 兴趣 判断", "互惠 主动性 关系节奏"),
     "strategy": "接住对方说的具体内容，给一个真实回应，再加一个轻量下一步。",
     "moves": ("回应具体内容", "表达你的感受或立场", "给一个可拒绝的下一步"),
     "avoid": ("不要背模板", "不要过度解读单条消息", "不要用操控性话术"),
     "drafts": ("[接住对方的具体内容]，我这边是 [你的真实想法]。",
                "我理解你的意思；对我来说，[明确表达]。",
                "如果继续这样，我需要 [边界]；你可以接受吗？"),
     "needs": ("你希望这条对话往哪里走？",)},
]


def setup_streams():
    core.setup_streams()


def read_text_auto(path):
    data = Path(path).read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def parse_timestamp(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        try:
            seconds = value / 1000.0 if value > 1e11 else value
            return datetime.fromtimestamp(seconds)
        except (OverflowError, OSError, ValueError):
            return None
    text = str(value).strip().strip("[]")
    if not text:
        return None
    text = text.replace("年", "-").replace("月", "-").replace("日", "")
    text = text.replace("/", "-").replace("T", " ")
    text = re.sub(r"\.\d+$", "", text).strip()
    formats = (
        "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d",
        "%m-%d %H:%M:%S", "%m-%d %H:%M",
        "%H:%M:%S", "%H:%M",
    )
    for fmt in formats:
        try:
            parsed = datetime.strptime(text, fmt)
        except ValueError:
            continue
        if fmt.startswith("%m"):
            parsed = parsed.replace(year=2000)
        if fmt.startswith("%H"):
            parsed = parsed.replace(year=2000, month=1, day=1)
        return parsed
    return None


def plausible_name(name):
    name = name.strip()
    if not name or len(name) > 20:
        return False
    if any(token in name.lower() for token in ("http", "www.", "@")):
        return False
    if any(char in name for char in "，。！？；、,.!?;"):
        return False
    if name.startswith(NARRATIVE_PREFIXES):
        return False
    return True


def parse_json_transcript(text):
    try:
        data = json.loads(text)
    except ValueError:
        return None
    if isinstance(data, dict):
        for key in ("messages", "chat", "data", "records", "items"):
            value = data.get(key)
            if isinstance(value, list):
                data = value
                break
        else:
            return None
    if not isinstance(data, list):
        return None
    messages = []
    for item in data:
        if not isinstance(item, dict):
            continue
        speaker = (
            item.get("speaker") or item.get("sender") or item.get("from")
            or item.get("name") or item.get("role") or item.get("user")
        )
        if isinstance(speaker, dict):
            speaker = speaker.get("name") or speaker.get("nickname") or speaker.get("id")
        content = item.get("content") or item.get("text") or item.get("message") or item.get("msg")
        if isinstance(content, list):
            parts = []
            for part in content:
                if isinstance(part, dict):
                    parts.append(str(part.get("text") or part.get("content") or ""))
                else:
                    parts.append(str(part))
            content = "".join(parts)
        content = str(content or "").strip()
        if not content:
            continue
        timestamp = (
            item.get("timestamp") or item.get("time") or item.get("date")
            or item.get("created_at") or item.get("ts")
        )
        messages.append({
            "speaker": str(speaker or "未知").strip()[:24] or "未知",
            "text": content,
            "ts": parse_timestamp(timestamp),
            "break_before": False,
            "system": bool(SYSTEM_RE.search(content)) or str(item.get("role") or "").lower() == "system",
        })
    return messages or None


def parse_lines(text):
    lines = text.splitlines()
    candidates = Counter()
    for line in lines:
        for regex in (BRACKET_COLON_RE, TS_COLON_RE, COLON_RE):
            match = regex.match(line)
            if match:
                name = match.group("speaker").strip()
                if plausible_name(name):
                    candidates[name] += 1
                break
    known = set()
    if len(candidates) <= 6:
        known = {name for name, count in candidates.items() if count >= 1}
    else:
        known = {name for name, count in candidates.items() if count >= 2}
    if not known:
        raise SystemExit(
            "未识别到聊天格式。请使用 `说话人: 内容`、`2026-01-01 20:00 说话人: 内容`，"
            "或 JSON 数组；也可以先用 --format json 检查文件。"
        )

    messages = []
    warnings = []
    current = None
    pending_speaker = None
    pending_ts = None
    break_pending = False

    def flush():
        nonlocal current
        if current and current["text"].strip():
            current["text"] = current["text"].strip()
            messages.append(current)
        current = None

    def start(speaker, ts, text_value="", break_flag=False):
        nonlocal current
        current = {
            "speaker": speaker.strip()[:24],
            "text": text_value,
            "ts": ts,
            "break_before": break_flag,
            "system": False,
        }

    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if SEPARATOR_RE.match(line) or DATE_ONLY_RE.match(line):
            flush()
            pending_speaker = None
            pending_ts = None
            break_pending = True
            continue

        match = BRACKET_COLON_RE.match(line) or TS_COLON_RE.match(line)
        if match and match.group("speaker").strip() in known:
            flush()
            start(match.group("speaker"), parse_timestamp(match.group("ts")),
                  match.group("text"), break_pending)
            break_pending = False
            pending_speaker = None
            pending_ts = None
            continue

        match = COLON_RE.match(line)
        if match and match.group("speaker").strip() in known:
            flush()
            start(match.group("speaker"), pending_ts, match.group("text"), break_pending)
            break_pending = False
            pending_speaker = None
            pending_ts = None
            continue

        match = TS_HEADER_RE.match(line)
        if match:
            flush()
            pending_ts = parse_timestamp(match.group("ts"))
            pending_speaker = match.group("speaker").strip()[:24]
            start(pending_speaker, pending_ts, "", break_pending)
            break_pending = False
            continue

        match = SPEAKER_TS_RE.match(line)
        if match:
            flush()
            pending_ts = parse_timestamp(match.group("ts"))
            pending_speaker = match.group("speaker").strip()[:24]
            start(pending_speaker, pending_ts, "", break_pending)
            break_pending = False
            continue

        if line in known and len(line) <= 20:
            flush()
            pending_speaker = line
            start(line, pending_ts, "", break_pending)
            break_pending = False
            continue

        if current is None:
            if pending_speaker:
                start(pending_speaker, pending_ts, "", break_pending)
                break_pending = False
            else:
                warnings.append("跳过无法归属的行：%s" % core.mask_pii(line[:40]))
                continue
        current["text"] += ("\n" if current["text"] else "") + line

    flush()
    return messages, warnings


def parse_transcript(text, me=None, session_gap=SESSION_GAP_DEFAULT, fmt="auto"):
    messages = None
    warnings = []
    if fmt in ("auto", "json"):
        messages = parse_json_transcript(text)
    if messages is None:
        if fmt == "json":
            raise SystemExit("JSON 解析失败：需要数组或包含 messages 数组的对象。")
        messages, warnings = parse_lines(text)
    cleaned = []
    for message in messages:
        content = core.normalize_text(str(message.get("text") or "")).strip()
        if not content:
            continue
        system = bool(message.get("system")) or bool(SYSTEM_RE.search(content))
        cleaned.append({
            "speaker": str(message.get("speaker") or "未知").strip()[:24] or "未知",
            "text": content,
            "ts": message.get("ts"),
            "break_before": bool(message.get("break_before")),
            "system": system,
            "media": bool(MEDIA_RE.match(content)),
        })
    cleaned = [message for message in cleaned if not message["system"]]
    if not cleaned:
        raise SystemExit("没有解析到有效消息。")
    counts = Counter(message["speaker"] for message in cleaned)
    speakers = [name for name, _ in counts.most_common()]
    if me:
        match = next((name for name in speakers if name == me), None)
        if match is None:
            match = next((name for name in speakers if name.casefold() == str(me).casefold()), None)
        if match is None:
            warnings.append("未找到说话人 %r，已使用第一位发言者 %r 作为“我”。" % (me, speakers[0]))
            me = speakers[0]
        else:
            me = match
    else:
        me = speakers[0]
        warnings.append("未指定 --me，默认第一位发言者 %r 为“我”。" % me)
    other = next((name for name in speakers if name != me), None)
    if other is None:
        warnings.append("只识别到一位说话人，互惠与对方回应指标不可用。")
    if len([name for name in speakers if name != me]) > 1:
        warnings.append("识别到多位对方，方向性指标只取发言最多的一位。")
    if not any(message["ts"] for message in cleaned):
        warnings.append("没有可用时间戳，回复间隔与会话节奏指标受限。")
    return {
        "messages": cleaned,
        "speakers": speakers,
        "me": me,
        "other": other,
        "warnings": warnings,
        "session_gap": session_gap,
    }


def format_duration(seconds):
    if seconds is None:
        return "-"
    seconds = float(seconds)
    if seconds < 60:
        return "%ds" % round(seconds)
    if seconds < 3600:
        return "%dm" % round(seconds / 60)
    if seconds < 86400:
        return "%.1fh" % (seconds / 3600)
    return "%.1fd" % (seconds / 86400)


def median(values):
    if not values:
        return None
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[middle])
    return (ordered[middle - 1] + ordered[middle]) / 2.0


def blank_stats():
    return {
        "messages": 0, "chars": 0, "questions": 0, "exclamations": 0, "emoji": 0,
        "cold": 0, "long": 0, "late_night": 0, "initiations": 0, "last_word": 0,
        "commit": 0, "cancel": 0, "latency": [], "replyable": 0, "got_reply": 0,
        "replied": 0, "double_text": 0, "questions_answered": 0,
    }


def is_cold(text):
    clean = re.sub(r"[^\w\u4e00-\u9fff]+", "", text).lower()
    if not clean:
        return True
    if clean in COLD_SET:
        return True
    if len(clean) <= 2 and not QUESTION_RE.search(text):
        return True
    return bool(re.fullmatch(r"(?:嗯+|哦+|喔+|好+|行+|呵+|哈+|在忙|忙|睡了|晚安|随便|算了|没事|知道了)", clean))


def count_emoji(text):
    count = 0
    for char in text:
        code = ord(char)
        if 0x1F300 <= code <= 0x1FAFF or 0x2600 <= code <= 0x27BF:
            count += 1
    count += len(re.findall(r"\[[^\]]{1,8}\]", text))
    return count


def summary_stats(stats):
    messages = stats["messages"]
    latency = stats["latency"]
    return {
        "messages": messages,
        "chars": stats["chars"],
        "avg_len": round(stats["chars"] / messages, 1) if messages else 0.0,
        "questions": stats["questions"],
        "question_rate": round(stats["questions"] / messages, 3) if messages else 0.0,
        "cold": stats["cold"],
        "cold_rate": round(stats["cold"] / messages, 3) if messages else 0.0,
        "initiations": stats["initiations"],
        "last_word": stats["last_word"],
        "median_latency_seconds": round(median(latency), 1) if latency else None,
        "replyable": stats["replyable"],
        "got_reply": stats["got_reply"],
        "reply_rate": round(stats["got_reply"] / stats["replyable"], 3) if stats["replyable"] else 0.0,
        "replied": stats["replied"],
        "double_text": stats["double_text"],
        "questions_answered": stats["questions_answered"],
        "commit": stats["commit"],
        "cancel": stats["cancel"],
        "late_night": stats["late_night"],
        "long": stats["long"],
    }


def compute_stats(parsed):
    messages = parsed["messages"]
    me = parsed["me"]
    other = parsed["other"]
    session_gap = parsed["session_gap"]
    speakers = parsed["speakers"]
    stats = {name: blank_stats() for name in speakers}

    session_ranges = []
    start = 0
    for index, message in enumerate(messages):
        if index == 0:
            continue
        previous = messages[index - 1]
        new_session = message.get("break_before")
        if not new_session and previous.get("ts") and message.get("ts"):
            gap = (message["ts"] - previous["ts"]).total_seconds()
            new_session = gap >= session_gap * 60 or gap < 0
        if new_session:
            session_ranges.append((start, index - 1))
            start = index
    session_ranges.append((start, len(messages) - 1))
    session_of = [0] * len(messages)
    for session_id, (first, last) in enumerate(session_ranges):
        for index in range(first, last + 1):
            session_of[index] = session_id

    for index, message in enumerate(messages):
        speaker = message["speaker"]
        if speaker not in stats:
            stats[speaker] = blank_stats()
        entry = stats[speaker]
        text = message["text"]
        entry["messages"] += 1
        entry["chars"] += len(text)
        if QUESTION_RE.search(text):
            entry["questions"] += 1
        if "!" in text or "！" in text:
            entry["exclamations"] += 1
        entry["emoji"] += count_emoji(text)
        if is_cold(text):
            entry["cold"] += 1
        if len(text) >= 80:
            entry["long"] += 1
        if message.get("ts") and (message["ts"].hour >= 23 or message["ts"].hour < 5):
            entry["late_night"] += 1
        entry["commit"] += sum(1 for term in COMMIT_TERMS if term in text)
        entry["cancel"] += sum(1 for term in CANCEL_TERMS if term in text)

        if index > 0 and session_of[index - 1] == session_of[index]:
            previous = messages[index - 1]
            if previous["speaker"] != speaker:
                entry["replied"] += 1
                if previous.get("ts") and message.get("ts"):
                    delta = (message["ts"] - previous["ts"]).total_seconds()
                    if 0 <= delta <= 86400:
                        entry["latency"].append(delta)
        if index + 1 < len(messages) and session_of[index + 1] == session_of[index]:
            entry["replyable"] += 1
            if messages[index + 1]["speaker"] != speaker:
                entry["got_reply"] += 1
            if messages[index + 1]["speaker"] == speaker:
                entry["double_text"] += 1
        if QUESTION_RE.search(text):
            for lookahead in (1, 2):
                if index + lookahead >= len(messages):
                    break
                if session_of[index + lookahead] != session_of[index]:
                    break
                if messages[index + lookahead]["speaker"] != speaker:
                    entry["questions_answered"] += 1
                    break

    for first, last in session_ranges:
        if first <= last:
            stats[messages[first]["speaker"]]["initiations"] += 1
            stats[messages[last]["speaker"]]["last_word"] += 1

    timestamps = [message["ts"] for message in messages if message.get("ts")]
    span_hours = None
    if len(timestamps) >= 2:
        span_hours = (max(timestamps) - min(timestamps)).total_seconds() / 3600.0
    gaps = []
    for index in range(1, len(session_ranges)):
        last_ts = messages[session_ranges[index - 1][1]].get("ts")
        first_ts = messages[session_ranges[index][0]].get("ts")
        if last_ts and first_ts:
            gaps.append((first_ts - last_ts).total_seconds() / 3600.0)

    summary = {name: summary_stats(entry) for name, entry in stats.items()}
    reciprocity = compute_reciprocity(summary, me, other, bool(timestamps))
    trend = compute_trend(messages, other or me, bool(timestamps))
    return {
        "stats": summary,
        "sessions": len(session_ranges),
        "span_hours": round(span_hours, 1) if span_hours is not None else None,
        "span_days": round(span_hours / 24.0, 1) if span_hours is not None else None,
        "gaps": gaps,
        "median_gap_hours": round(median(gaps), 1) if gaps else None,
        "reciprocity": reciprocity,
        "trend": trend,
        "has_timestamps": bool(timestamps),
    }


def compute_reciprocity(stats, me, other, has_timestamps):
    if not other or me not in stats or other not in stats:
        return {"score": 0, "label": "不可用", "metrics": {}}
    a = stats[me]
    b = stats[other]
    msg_balance = 1.0 - abs(a["messages"] - b["messages"]) / max(1, a["messages"] + b["messages"])
    char_balance = 1.0 - abs(a["chars"] - b["chars"]) / max(1, a["chars"] + b["chars"])
    init_a, init_b = a["initiations"], b["initiations"]
    if init_a + init_b:
        initiative_balance = 1.0 - abs(init_a - init_b) / (init_a + init_b)
    else:
        initiative_balance = 0.5
    latency_a = a.get("median_latency_seconds")
    latency_b = b.get("median_latency_seconds")
    if latency_a and latency_b:
        latency_balance = min(latency_a, latency_b) / max(latency_a, latency_b)
    else:
        latency_balance = 0.5
    rate_a = a.get("reply_rate") or 0.0
    rate_b = b.get("reply_rate") or 0.0
    if rate_a or rate_b:
        reply_balance = min(rate_a, rate_b) / max(rate_a, rate_b) if max(rate_a, rate_b) else 0.0
    else:
        reply_balance = 0.5
    if has_timestamps:
        score = 100 * (
            0.30 * msg_balance + 0.20 * char_balance + 0.25 * initiative_balance
            + 0.15 * latency_balance + 0.10 * reply_balance
        )
    else:
        score = 100 * (
            0.35 * msg_balance + 0.25 * char_balance + 0.30 * initiative_balance
            + 0.10 * reply_balance
        )
    score = round(score)
    label = "高" if score >= 70 else ("中" if score >= 45 else "低")
    return {
        "score": score,
        "label": label,
        "metrics": {
            "message_balance": round(msg_balance, 2),
            "char_balance": round(char_balance, 2),
            "initiative_balance": round(initiative_balance, 2),
            "latency_balance": round(latency_balance, 2),
            "reply_balance": round(reply_balance, 2),
        },
    }


def slice_metrics(messages):
    if not messages:
        return {"messages": 0, "avg_len": 0.0, "question_rate": 0.0,
                "cold_rate": 0.0, "median_latency_seconds": None}
    chars = sum(len(message["text"]) for message in messages)
    questions = sum(1 for message in messages if QUESTION_RE.search(message["text"]))
    cold = sum(1 for message in messages if is_cold(message["text"]))
    latencies = []
    for index in range(1, len(messages)):
        if messages[index]["speaker"] == messages[index - 1]["speaker"]:
            continue
        if messages[index].get("ts") and messages[index - 1].get("ts"):
            delta = (messages[index]["ts"] - messages[index - 1]["ts"]).total_seconds()
            if 0 <= delta <= 86400:
                latencies.append(delta)
    return {
        "messages": len(messages),
        "avg_len": round(chars / len(messages), 1),
        "question_rate": round(questions / len(messages), 3),
        "cold_rate": round(cold / len(messages), 3),
        "median_latency_seconds": round(median(latencies), 1) if latencies else None,
    }


def compute_trend(messages, focus, has_timestamps):
    if len(messages) < 20:
        return {"label": "样本不足", "summary": "少于 20 条，暂不判断趋势。", "evidence": []}
    middle = len(messages) // 2
    early_all = messages[:middle]
    late_all = messages[middle:]
    early = slice_metrics([message for message in early_all if message["speaker"] == focus])
    late = slice_metrics([message for message in late_all if message["speaker"] == focus])
    if not early["messages"] or not late["messages"]:
        return {"label": "样本不足", "summary": "前后半段缺少对方消息，暂不判断趋势。", "evidence": []}

    warm = 0
    cool = 0
    evidence = []
    if early["avg_len"] and late["avg_len"]:
        change = late["avg_len"] / early["avg_len"] - 1
        if change >= 0.15:
            warm += 1
            evidence.append("平均字数 +%.0f%%" % (change * 100))
        elif change <= -0.15:
            cool += 1
            evidence.append("平均字数 %.0f%%" % (change * 100))
    question_change = late["question_rate"] - early["question_rate"]
    if question_change >= 0.08:
        warm += 1
        evidence.append("提问率 +%.0f%%" % (question_change * 100))
    elif question_change <= -0.08:
        cool += 1
        evidence.append("提问率 %.0f%%" % (question_change * 100))
    cold_change = late["cold_rate"] - early["cold_rate"]
    if cold_change <= -0.08:
        warm += 1
        evidence.append("冷回复 -%.0f%%" % (abs(cold_change) * 100))
    elif cold_change >= 0.08:
        cool += 1
        evidence.append("冷回复 +%.0f%%" % (cold_change * 100))
    latency_change = None
    if has_timestamps and early["median_latency_seconds"] and late["median_latency_seconds"]:
        latency_change = late["median_latency_seconds"] / early["median_latency_seconds"] - 1
        if latency_change <= -0.2:
            warm += 1
            evidence.append("回复间隔 %.0f%%" % (latency_change * 100))
        elif latency_change >= 0.25:
            cool += 1
            evidence.append("回复间隔 +%.0f%%" % (latency_change * 100))

    if warm >= 2 and warm > cool:
        label = "升温"
        summary = "对方在后半段的投入与回应增加，可以小步推进，但每次升级都要给退路。"
    elif cool >= 2 and cool > warm:
        label = "降温"
        summary = "对方在后半段的投入与回应下降，先停止追加，观察是否主动。"
    else:
        label = "稳定/波动"
        summary = "前后半段没有一致的方向变化，先看具体事件与单次异常。"
    return {
        "label": label,
        "summary": summary,
        "evidence": evidence,
        "early": early,
        "late": late,
        "latency_change": round(latency_change, 2) if latency_change is not None else None,
    }


def scan_terms(messages, terms, roles=None, require_hearsay=False, excludes=()):
    count = 0
    examples = []
    for message in messages:
        if message.get("media"):
            continue
        if roles is not None and message.get("speaker") not in roles:
            continue
        text = message["text"]
        if require_hearsay and not any(marker in text for marker in HEARSAY_MARKERS):
            continue
        if excludes and any(re.search(pattern, text) for pattern in excludes):
            continue
        lowered = text.lower()
        for term in terms:
            hits = lowered.count(term.lower())
            if not hits:
                continue
            count += min(2, hits)
            if len(examples) < 3:
                examples.append(core.mask_pii(text)[:80])
            break
    return count, examples


def note_messages(notes):
    return [{
        "speaker": "用户补充",
        "text": note,
        "ts": None,
        "break_before": False,
        "system": False,
        "media": False,
    } for note in notes if note and note.strip()]


def detect_signals(messages, notes, me=None, other=None):
    categories = OrderedDict()
    other_messages = [item for item in messages if not other or item["speaker"] == other]
    mine_disclosures = [
        item for item in messages
        if me and item["speaker"] == me
        and any(marker in item["text"] for marker in HEARSAY_MARKERS)
    ]
    for key, spec in SIGNALS.items():
        excludes = spec.get("exclude", ())
        if key in ACTOR_SIGNALS:
            count, examples = scan_terms(other_messages, spec["terms"], excludes=excludes)
            if me:
                extra_count, extra_examples = scan_terms(
                    mine_disclosures, spec["terms"], roles={me}, excludes=excludes
                )
                count += extra_count
                examples.extend(extra_examples)
                examples = examples[:3]
        else:
            count, examples = scan_terms(messages, spec["terms"], excludes=excludes)
        categories[key] = {
            "label": spec["label"],
            "count": count,
            "weight": spec["weight"],
            "severity": spec["severity"],
            "examples": examples,
        }
    note_items = note_messages(notes)
    for key, spec in SIGNALS.items():
        count, examples = scan_terms(note_items, spec["terms"],
                                     excludes=spec.get("exclude", ()))
        if count:
            categories[key]["count"] += count
            categories[key]["examples"].extend(examples)
            categories[key]["examples"] = categories[key]["examples"][:3]

    all_items = messages + note_items
    minor_age = False
    ages = []
    for message in all_items:
        for match in re.finditer(r"(?<!\d)(\d{1,2})\s*(?:岁|周岁)(?!\d)", message["text"]):
            age = int(match.group(1))
            if age < 18:
                minor_age = True
                ages.append(age)
                if len(categories["minor"]["examples"]) < 3:
                    categories["minor"]["examples"].append(core.mask_pii(message["text"])[:80])
    if minor_age:
        categories["minor"]["count"] += 2

    minor_context = False
    if categories["minor"]["count"]:
        romantic_terms = ("喜欢", "恋爱", "在一起", "约会", "见面", "视频", "照片", "亲密", "FWB", "网恋")
        for message in all_items:
            if "未成年" in message["text"] and any(term in message["text"] for term in romantic_terms):
                minor_context = True
                break

    consent_context = 0
    sexual_pressure = 0
    consent_examples = []
    pressure_examples = []
    last_consent_index = -10
    last_pressure_index = -10
    for index, message in enumerate(messages):
        window = messages[max(0, index - 1):index + 2]
        window_text = " ".join(item["text"] for item in window)
        has_sexual = any(term in window_text for term in SEXUAL_TERMS)
        if not has_sexual:
            continue
        has_refusal = any(term in window_text for term in REFUSAL_TERMS)
        if other:
            pressure_source = [item["text"] for item in window if item["speaker"] == other]
        else:
            pressure_source = [item["text"] for item in window]
        has_pressure = any(
            term in text for text in pressure_source for term in PRESSURE_TERMS
        )
        if has_refusal and index - last_consent_index >= 2:
            consent_context += 1
            last_consent_index = index
            if len(consent_examples) < 3:
                sample = next(
                    (item for item in window
                     if any(term in item["text"] for term in REFUSAL_TERMS)),
                    message,
                )
                consent_examples.append(
                    "%s: %s" % (sample["speaker"], core.mask_pii(sample["text"])[:70])
                )
        if has_pressure and index - last_pressure_index >= 2:
            sexual_pressure += 1
            last_pressure_index = index
            if len(pressure_examples) < 3:
                sample = next(
                    (item for item in window
                     if any(term in item["text"] for term in PRESSURE_TERMS)),
                    message,
                )
                pressure_examples.append(
                    "%s: %s" % (sample["speaker"], core.mask_pii(sample["text"])[:70])
                )
    categories["consent"] = {
        "label": "同意/拒绝信号",
        "count": min(consent_context, 6),
        "weight": 30,
        "severity": "高" if consent_context else "灰色",
        "examples": consent_examples,
    }
    if not consent_context:
        categories.pop("consent")
    categories["sexual_pressure"] = {
        "label": "性压力/交换同意",
        "count": min(sexual_pressure, 6),
        "weight": 35,
        "severity": "高" if sexual_pressure else "灰色",
        "examples": pressure_examples,
    }
    if not sexual_pressure:
        categories.pop("sexual_pressure")

    for item in categories.values():
        item["examples"] = list(OrderedDict.fromkeys(item["examples"]))[:3]

    return {
        "categories": categories,
        "minor_age": minor_age,
        "minor_context": minor_context,
        "ages": ages,
    }


def assess_risk(signal_result):
    categories = signal_result["categories"]
    score = 0
    reasons = []
    for key, item in categories.items():
        if not item["count"]:
            continue
        score += min(item["count"], 3) * item["weight"]
        reasons.append({
            "key": key,
            "label": item["label"],
            "count": item["count"],
            "severity": item["severity"],
            "weight": item["weight"],
            "examples": item["examples"][:2],
        })
    reasons.sort(key=lambda item: -(item["weight"] * min(item["count"], 3)))
    critical = any(
        categories.get(key, {}).get("count", 0)
        for key in ("selfharm", "violence", "crisis")
    )
    hard_stop = signal_result["minor_age"] or signal_result["minor_context"]
    if hard_stop or critical:
        level = "紧急"
    elif score >= 80:
        level = "高"
    elif score >= 40:
        level = "中"
    elif score >= 12:
        level = "灰色"
    else:
        level = "无"
    if signal_result["minor_age"] or signal_result["minor_context"]:
        level = "紧急"
        hard_stop = True
    summary = "无显著风险信号。"
    if reasons:
        summary = "、".join(
            "%s×%d" % (item["label"], item["count"]) for item in reasons[:3]
        )
    return {
        "level": level,
        "score": score,
        "reasons": reasons,
        "summary": summary,
        "hard_stop": hard_stop,
        "minor_age": signal_result["minor_age"],
        "minor_context": signal_result["minor_context"],
    }


def detect_themes(messages, notes):
    note_items = note_messages(notes)
    all_items = messages + note_items
    themes = []
    for theme in THEMES:
        count = 0
        examples = []
        for message in all_items:
            if message.get("media"):
                continue
            text = message["text"]
            lowered = text.lower()
            hit = False
            for term in theme["terms"]:
                if term.lower() in lowered:
                    count += 1
                    hit = True
                    break
            if hit and len(examples) < 2:
                examples.append(core.mask_pii(text)[:80])
        if count:
            themes.append({
                "name": theme["name"],
                "count": count,
                "queries": list(theme["queries"]),
                "examples": examples,
            })
    themes.sort(key=lambda item: -item["count"])
    return themes[:5]


def infer_stage(themes, risk, message_count):
    names = {theme["name"]: theme["count"] for theme in themes}
    if risk["level"] == "紧急":
        return "危机/止损"
    if risk["level"] == "高":
        return "危机/止损"
    if names.get("分手/止损", 0) >= 2:
        return "分手/降温"
    if names.get("冲突/修复", 0) >= 2:
        return "冲突修复"
    if names.get("第三者/关系结构", 0) >= 2:
        return "关系定义/结构"
    if names.get("FWB/休闲关系", 0) >= 2:
        return "休闲关系/暧昧"
    if names.get("异地/网恋", 0) >= 2:
        return "异地/网恋"
    if names.get("性沟通/同意", 0) >= 2:
        return "亲密/同意"
    if names.get("操控/情感勒索", 0) >= 2:
        return "冲突/降温"
    if message_count < 20:
        return "初识/早期"
    if names.get("性沟通/同意", 0) or names.get("线上亲密", 0):
        return "暧昧"
    return "熟悉/稳定"


def build_queries(themes, risk, stage, notes_themes):
    plan = []

    def add(query, weight, reason):
        normalized = re.sub(r"\s+", " ", query).strip()
        if not normalized:
            return
        for item in plan:
            if item["query"] == normalized:
                if weight > item["weight"]:
                    item["weight"] = weight
                return
        plan.append({"query": normalized, "weight": weight, "reason": reason})

    risk_queries = 0
    risk_budget = 3 if len(themes) >= 2 else 4
    for reason in risk["reasons"]:
        if risk_queries >= risk_budget:
            break
        for query in RISK_QUERIES.get(reason["key"], ())[:1]:
            add(query, 1.3, "风险:" + reason["label"])
            risk_queries += 1
    if risk["reasons"] and risk_queries < risk_budget:
        for query in RISK_QUERIES.get(risk["reasons"][0]["key"], ())[1:2]:
            add(query, 1.25, "风险:" + risk["reasons"][0]["label"])
            risk_queries += 1
    for theme in themes[:2]:
        for query in theme["queries"][:1]:
            add(query, 1.0, "主题:" + theme["name"])
    for theme in notes_themes[:1]:
        for query in theme["queries"][:1]:
            add(query, 0.9, "补充:" + theme["name"])
    for query in STAGE_QUERIES.get(stage, ()):
        add(query, 0.8, "阶段:" + stage)
    if not plan:
        add("聊天 回复 推进 兴趣 判断", 1.0, "默认")
        add("互惠 主动性 关系节奏", 0.9, "默认")
    plan.sort(key=lambda item: -item["weight"])
    return plan[:MAX_QUERIES]


def tail_fingerprint(messages, size=3):
    tail = []
    for message in messages[-size:]:
        digest = hashlib.sha1(message["text"].encode("utf-8")).hexdigest()[:10]
        tail.append([message["speaker"], digest])
    return tail


def recent_messages(messages, limit=10):
    output = []
    for message in messages[-limit:]:
        output.append({
            "speaker": message["speaker"],
            "text": core.mask_pii(message["text"])[:160],
            "ts": message["ts"].isoformat(sep=" ") if message.get("ts") else None,
        })
    return output


def conclusion_text(profile):
    risk = profile["risk"]
    if risk["hard_stop"]:
        return "涉及未成年人或即时安全风险，停止恋爱/性相关分析；先确认安全并按求助流程处理。"
    if risk["level"] in ("紧急", "高"):
        return "主要问题不是聊天技巧，而是%s；先按风险止损，不要继续加码投入。" % risk["summary"]
    reciprocity = profile["metrics"]["reciprocity"]
    trend = profile["trend"]["label"]
    themes = profile["themes"]
    theme_text = themes[0]["name"] if themes else "关系节奏"
    if reciprocity["score"] < 45:
        return "投入与回应明显不对称；先降低投入，做一次低压确认，再观察对方是否主动。"
    if trend == "降温":
        return "近期互动在降温；停止追加，给对方一次主动空间，不追问、不连发。"
    if trend == "升温":
        return "互动在升温，可以小步推进；每次升级都给退路和明确的同意节点。"
    return "互动基本稳定，当前重点在%s；先明确期待与边界，再看对方是否兑现。" % theme_text


def build_profile(parsed, notes, kb, search_top, excerpt_chars, cache_dir, rebuild, no_search):
    messages = parsed["messages"]
    me = parsed["me"]
    other = parsed["other"]
    stats_result = compute_stats(parsed)
    themes = detect_themes(messages, notes)
    notes_themes = detect_themes([], notes)
    signal_result = detect_signals(messages, notes, me=me, other=other)
    risk = assess_risk(signal_result)
    stage = infer_stage(themes, risk, len(messages))
    queries = build_queries(themes, risk, stage, notes_themes)
    pack = []
    pack_note = ""
    if no_search:
        pack_note = "已跳过检索（--no-search）。"
    elif kb is None:
        pack_note = "未连接知识库；以下仅基于内置框架与画像指标。"
    else:
        engine = core.SearchEngine(kb, cache_dir=cache_dir, rebuild=rebuild)
        specs = [{"query": item["query"], "weight": item["weight"]} for item in queries]
        results, _ = engine.batch(specs, top=search_top, per_query=6)
        query_text = " ".join(item["query"] for item in queries)
        for result in results:
            result["excerpt"] = engine.excerpt(result, query=query_text,
                                               max_chars=excerpt_chars, safe=True)
        pack = results
        pack_note = "检索自本地知识库。"

    profile = {
        "format": "emochat-profile-v1",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source": {
            "file": Path(parsed.get("source_file") or "").name if parsed.get("source_file") else "",
            "messages": len(messages),
            "speakers": parsed["speakers"],
            "span_days": stats_result["span_days"],
            "span_hours": stats_result["span_hours"],
            "sessions": stats_result["sessions"],
            "has_timestamps": stats_result["has_timestamps"],
        },
        "me": me,
        "other": other,
        "stage": stage,
        "metrics": {
            "stats": stats_result["stats"],
            "reciprocity": stats_result["reciprocity"],
            "sessions": stats_result["sessions"],
            "span_days": stats_result["span_days"],
            "median_gap_hours": stats_result["median_gap_hours"],
        },
        "trend": stats_result["trend"],
        "themes": themes,
        "notes_themes": notes_themes,
        "signals": {
            key: item for key, item in signal_result["categories"].items() if item["count"]
        },
        "risk": risk,
        "notes": notes,
        "queries": queries,
        "recent": recent_messages(messages),
        "pack": pack,
        "pack_note": pack_note,
        "warnings": parsed["warnings"],
        "tail": tail_fingerprint(messages),
    }
    profile["conclusion"] = conclusion_text(profile)
    return profile


def format_latency(value):
    return format_duration(value)


def render_profile(profile, profile_file, delta_text=""):
    source = profile["source"]
    metrics = profile["metrics"]
    stats = metrics["stats"]
    me = profile["me"]
    other = profile["other"]
    lines = [
        "# 对话画像",
        "",
        "- 样本：%d 条 / %d 人 / %s 段会话%s" % (
            source["messages"], len(source["speakers"]), source["sessions"],
            (" / %.1f 天" % source["span_days"]) if source["span_days"] is not None else "",
        ),
        "- 角色：我=%s；对方=%s" % (me, other or "未识别"),
        "- 阶段：%s" % profile["stage"],
        "- 风险：%s（%s）" % (profile["risk"]["level"], profile["risk"]["summary"]),
        "- 互惠度：%s/100（%s）" % (
            metrics["reciprocity"]["score"], metrics["reciprocity"]["label"]
        ),
        "- 趋势：%s" % profile["trend"]["label"],
        "",
        "## 一句话",
        profile["conclusion"],
        "",
        "## 互惠与节奏",
    ]
    if other and me in stats and other in stats:
        left = stats[me]
        right = stats[other]
        lines.extend([
            "| 指标 | 我 | 对方 |",
            "|---|---|---|",
            "| 消息数 | %d | %d |" % (left["messages"], right["messages"]),
            "| 平均字数 | %.1f | %.1f |" % (left["avg_len"], right["avg_len"]),
            "| 提问 | %d | %d |" % (left["questions"], right["questions"]),
            "| 主动开启 | %d | %d |" % (left["initiations"], right["initiations"]),
            "| 中位回复间隔 | %s | %s |" % (
                format_latency(left["median_latency_seconds"]),
                format_latency(right["median_latency_seconds"]),
            ),
            "| 冷回复比例 | %.0f%% | %.0f%% |" % (
                left["cold_rate"] * 100, right["cold_rate"] * 100
            ),
            "| 回复率 | %.0f%% | %.0f%% |" % (
                left["reply_rate"] * 100, right["reply_rate"] * 100
            ),
        ])
    else:
        only = stats.get(me, {})
        lines.append("- 只有一方消息：%d 条，平均 %.1f 字。" % (
            only.get("messages", 0), only.get("avg_len", 0)
        ))
    trend = profile["trend"]
    if trend.get("evidence"):
        lines.append("- 趋势证据：%s" % "；".join(trend["evidence"]))
    if metrics.get("median_gap_hours") is not None:
        lines.append("- 会话间隔中位数：%.1f 小时" % metrics["median_gap_hours"])
    lines.extend(["", "## 关系主题"])
    if profile["themes"]:
        for theme in profile["themes"]:
            lines.append("- %s ×%d" % (theme["name"], theme["count"]))
    else:
        lines.append("- 未识别到稳定主题。")
    lines.extend(["", "## 风险信号"])
    if profile["risk"]["reasons"]:
        for reason in profile["risk"]["reasons"]:
            lines.append("- [%s] %s ×%d" % (
                reason["severity"], reason["label"], reason["count"]
            ))
            if reason["examples"]:
                lines.append("  例：%s" % reason["examples"][0].replace("\n", " ")[:90])
    else:
        lines.append("- 未发现明确风险信号；仍需结合线下行为与时间线判断。")
    lines.extend(["", "## 建议检索"])
    for index, item in enumerate(profile["queries"], 1):
        lines.append("%d. `%s`（%s）" % (index, item["query"], item["reason"]))
    lines.extend(["", "## 卡片包"])
    if profile["pack"]:
        for card in profile["pack"]:
            lines.append("### [%s] %s" % (card.get("id"), card.get("title")))
            if card.get("matched_queries"):
                lines.append("- 命中：%s" % "；".join(card["matched_queries"][:2]))
            if card.get("excerpt"):
                lines.append("- 摘要：%s" % card["excerpt"].replace("\n", " ")[:600])
            lines.append("")
    else:
        lines.append(profile.get("pack_note") or "未返回卡片。")
    if profile.get("notes"):
        lines.extend(["", "## 用户补充"])
        for note in profile["notes"]:
            lines.append("- %s" % core.mask_pii(note))
    lines.extend(["", "## 安全提示"])
    if profile["risk"]["hard_stop"]:
        lines.append("- 涉及未成年人或即时危险：停止恋爱/性相关内容，优先 110/120/12356；未成年人可拨 12355。")
    elif profile["risk"]["level"] in ("紧急", "高"):
        lines.append("- 先止损与保留证据；不要单独见面、不要转账、不要发送影像。紧急 110/120，反诈 96110，心理援助 12356。")
    else:
        lines.append("- 这是模式分析，不是诊断；重要决定请结合线下行为与专业意见。")
    if profile.get("warnings"):
        lines.extend(["", "## 解析提示"])
        for warning in profile["warnings"]:
            lines.append("- %s" % warning)
    if delta_text:
        lines.extend(["", delta_text])
    if profile_file:
        lines.extend(["", "profile_file: `%s`" % profile_file])
    return "\n".join(lines).rstrip() + "\n"


def save_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
    temporary.replace(path)


def default_profile_path(transcript, cache_dir):
    digest = hashlib.sha1(str(Path(transcript).resolve()).encode("utf-8")).hexdigest()[:16]
    return core.resolve_cache_dir(cache_dir) / "profiles" / (digest + ".json")


def compute_delta(previous, current, messages):
    if not previous or previous.get("format") != "emochat-profile-v1":
        return ""
    previous_count = int(previous.get("source", {}).get("messages") or 0)
    previous_tail = previous.get("tail") or []
    if previous_count <= 0 or previous_count > len(messages):
        return "## 增量\n- 缓存与当前记录不一致，已全量重算。"
    if previous_tail and previous_count >= len(previous_tail):
        expected = tail_fingerprint(messages[:previous_count], size=len(previous_tail))
        if expected != previous_tail:
            return "## 增量\n- 缓存与当前记录前缀不一致，已全量重算。"
    new_messages = messages[previous_count:]
    if not new_messages:
        return "## 增量\n- 没有新增消息。"
    by_speaker = Counter(message["speaker"] for message in new_messages)
    lines = [
        "## 增量（新增 %d 条）" % len(new_messages),
        "- 新增发言：%s" % "，".join("%s %d 条" % (name, count) for name, count in by_speaker.most_common()),
    ]
    previous_signals = previous.get("signals") or {}
    new_signals = []
    for key, item in (current.get("signals") or {}).items():
        old_count = int((previous_signals.get(key) or {}).get("count") or 0)
        difference = item["count"] - old_count
        if difference > 0:
            new_signals.append("%s +%d" % (item["label"], difference))
    lines.append("- 新增信号：%s" % ("；".join(new_signals) if new_signals else "无新增类别"))
    lines.append("- 当前风险：%s（%s）" % (
        current["risk"]["level"], current["risk"]["summary"]
    ))
    lines.append("- 当前趋势：%s；互惠度 %s/100" % (
        current["trend"]["label"], current["metrics"]["reciprocity"]["score"]
    ))
    return "\n".join(lines)


def load_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def collect_notes(args, previous=None):
    notes = []
    if previous:
        for note in previous.get("notes") or []:
            if note not in notes:
                notes.append(note)
    for note in args.notes or []:
        if note and note not in notes:
            notes.append(note)
    if getattr(args, "notes_file", None):
        try:
            text = read_text_auto(args.notes_file)
        except OSError as exc:
            raise SystemExit("无法读取 --notes-file: %s" % exc)
        for line in text.splitlines():
            line = line.strip()
            if line and line not in notes:
                notes.append(line)
    return notes


def classify_intent(message, profile=None):
    text = core.normalize_text(message).strip()
    if not text:
        return {"id": "neutral", "label": "普通对话", "score": 0, "confidence": "低",
                "evidence": [], "secondary": []}
    lowered = text.lower()
    clean = re.sub(r"[^\w\u4e00-\u9fff]+", "", text)
    previous_me_question = False
    if profile:
        for item in reversed(profile.get("recent") or []):
            if item.get("speaker") == profile.get("me"):
                previous_me_question = bool(QUESTION_RE.search(item.get("text") or ""))
                break

    scored = []
    for priority, intent in enumerate(INTENTS):
        score = 0
        evidence = []
        for term in intent.get("terms", ()):
            if term.lower() in lowered:
                score += 2
                evidence.append(term)
        for pattern in intent.get("patterns", ()):
            if re.search(pattern, text):
                score += 3
                evidence.append("pattern:" + pattern[:18])
        if intent["id"] == "crisis" and evidence:
            score += 4
        if intent["id"] == "threat" and evidence:
            score += 2
        if intent["id"] == "cold":
            if is_cold(text):
                score += 3
            if len(clean) <= 4:
                score += 2
            if previous_me_question:
                score += 2
        if intent["id"] == "boundary" and len(clean) <= 20 and evidence:
            score += 2
        if intent["id"] == "invite" and QUESTION_RE.search(text) and evidence:
            score += 2
        if intent["id"] == "money" and re.search(r"转.*\d", text):
            score += 2
        if intent["id"] == "sexual_request" and re.search(r"(?:发|给).*(?:照片|视频)", text):
            score += 2
        if intent["id"] == "question" and QUESTION_RE.search(text):
            score += 2
        scored.append({
            "intent": intent,
            "score": score,
            "evidence": evidence[:5],
            "priority": priority,
        })
    scored.sort(key=lambda item: (-item["score"], item["priority"]))
    critical = next((item for item in scored if item["intent"]["id"] == "crisis"), None)
    top = critical if critical and critical["score"] > 0 else scored[0]
    low_risk_ids = {"question", "cold", "neutral", "flirt", "invite", "apology", "test",
                    "cancel", "define"}
    if top["intent"]["id"] in low_risk_ids:
        high_risk = next(
            (item for item in scored
             if item["intent"]["risk"] >= 3 and item["score"] >= 4),
            None,
        )
        if high_risk:
            top = high_risk
    if top["score"] < 2:
        top = next(item for item in scored if item["intent"]["id"] == "neutral")
    secondary = [
        item for item in scored[1:]
        if item["score"] >= max(2, top["score"] * 0.6)
        and item["intent"]["id"] != top["intent"]["id"]
    ][:2]
    if top["score"] >= 6:
        confidence = "高"
    elif top["score"] >= 3:
        confidence = "中"
    else:
        confidence = "低"
    intent = dict(top["intent"])
    return {
        "id": intent["id"],
        "label": intent["label"],
        "risk": intent["risk"],
        "strategy": intent["strategy"],
        "moves": list(intent["moves"]),
        "avoid": list(intent["avoid"]),
        "drafts": list(intent["drafts"]),
        "queries": list(intent["queries"]),
        "needs": list(intent["needs"]),
        "score": top["score"],
        "confidence": confidence,
        "evidence": top["evidence"],
        "secondary": [
            {"id": item["intent"]["id"], "label": item["intent"]["label"], "score": item["score"]}
            for item in secondary
        ],
    }


def risk_level_from_score(score):
    return {5: "紧急", 4: "高", 3: "中", 2: "灰色", 1: "灰色", 0: "无"}.get(score, "无")


def combine_risk(profile_risk, intent, message_signals):
    levels = ["无", "灰色", "中", "高", "紧急"]
    profile_level = (profile_risk or {}).get("level", "无")
    intent_level = risk_level_from_score(intent.get("risk", 0))
    message_risk = assess_risk(message_signals)
    candidates = [profile_level, intent_level, message_risk["level"]]
    level = max(candidates, key=lambda value: levels.index(value) if value in levels else 0)
    reasons = []
    if profile_risk:
        reasons.extend(profile_risk.get("reasons") or [])
    for reason in message_risk.get("reasons") or []:
        if reason["key"] not in {item["key"] for item in reasons}:
            reasons.append(reason)
    hard_stop = bool((profile_risk or {}).get("hard_stop")) or message_risk["hard_stop"]
    if hard_stop:
        level = "紧急"
    return {
        "level": level,
        "score": max((profile_risk or {}).get("score", 0), message_risk["score"]),
        "reasons": reasons,
        "summary": "、".join("%s×%d" % (item["label"], item["count"]) for item in reasons[:3]) or "无显著新增风险",
        "hard_stop": hard_stop,
        "minor_age": message_risk.get("minor_age", False),
        "minor_context": message_risk.get("minor_context", False),
    }


def select_intent_queries(intent, message):
    queries = list(intent.get("queries", []))
    intent_id = intent.get("id")
    lowered = message.lower()

    def has(terms):
        return any(term.lower() in lowered for term in terms)

    if intent_id == "money":
        if has(SIGNALS["scam"]["terms"]):
            queries = ["诈骗 转账 杀猪盘 识别", "借钱 边界 拒绝 话术"]
            if has(SIGNALS["sextortion"]["terms"] + ("视频", "照片", "影像", "摄像头")):
                queries.append("私密影像 勒索 应对")
        else:
            queries = ["借钱 边界 拒绝 话术", "金钱 关系 公平", "经济控制 索取 边界"]
    elif intent_id == "sexual_request":
        if has(SIGNALS["sextortion"]["terms"] + ("视频", "照片", "影像", "摄像头")):
            queries = ["性沟通 同意 拒绝 话术", "私密影像 录屏 停止", "视频亲密 录屏 停止"]
        else:
            queries = ["性沟通 同意 拒绝 话术", "性沟通 同意 边界 停止"]
    elif intent_id == "threat":
        if has(SIGNALS["sextortion"]["terms"]):
            queries = ["私密影像 勒索 应对", "威胁 曝光 取证 报警"]
        else:
            queries = ["威胁 曝光 取证 报警", "敲诈 勒索 保留证据"]
    elif intent_id == "crisis":
        if has(("我不想活", "不想活", "我要死", "自杀", "割腕", "跳楼", "活着没意思", "结束生命")):
            queries = ["自杀风险 识别 转介 陪伴", "心理援助 12356 危机"]
        else:
            queries = ["威胁 取证 报警 安全", "人身安全 求助 110 证据"]
    return queries


def build_reply_queries(intent, message, profile, risk=None):
    plan = []

    def add(query, weight, reason):
        normalized = re.sub(r"\s+", " ", query).strip()
        if not normalized:
            return
        for item in plan:
            if item["query"] == normalized:
                item["weight"] = max(item["weight"], weight)
                return
        plan.append({"query": normalized, "weight": weight, "reason": reason})

    if risk and risk.get("hard_stop"):
        if risk.get("minor_age") or risk.get("minor_context"):
            hard = ("未成年人 保护 报警 转介", "中国法律 安全 危机转介 报警",
                    "求助资源 心理 法律 危机干预")
            label = "硬边界:未成年"
        else:
            hard = ("威胁 取证 报警 安全", "人身安全 求助 110 证据",
                    "求助资源 心理 法律 危机干预")
            label = "硬边界:紧急"
        for query in hard:
            add(query, 1.5, label)
        return plan[:MAX_QUERIES]

    for query in select_intent_queries(intent, message):
        add(query, 1.5, "意图:" + intent["label"])
    theme_list = detect_themes([{
        "speaker": "对方", "text": message, "ts": None, "break_before": False,
        "system": False, "media": False,
    }], [])
    for theme in theme_list[:1]:
        for query in theme["queries"][:1]:
            add(query, 0.8, "主题:" + theme["name"])
    if intent.get("confidence") != "高" and len(re.sub(r"\s+", "", message)) >= 4:
        add(message[:60], 0.9, "消息原文")
    if profile:
        for item in (profile.get("queries") or [])[:2]:
            add(item["query"], 0.5, "画像")
        risk = profile.get("risk") or {}
        if risk.get("level") in ("高", "紧急"):
            for reason in (risk.get("reasons") or [])[:2]:
                for query in RISK_QUERIES.get(reason["key"], ())[:1]:
                    add(query, 0.9, "画像风险:" + reason["label"])
    if not plan:
        add("聊天 回复 推进 兴趣 判断", 1.0, "默认")
    plan.sort(key=lambda item: -item["weight"])
    return plan[:MAX_QUERIES]


def retrieve_cards(kb, queries, top, excerpt_chars, cache_dir, rebuild):
    if kb is None:
        return [], "未连接知识库；以下策略来自内置框架。"
    engine = core.SearchEngine(kb, cache_dir=cache_dir, rebuild=rebuild)
    specs = [{"query": item["query"], "weight": item["weight"]} for item in queries]
    results, _ = engine.batch(specs, top=top, per_query=6)
    query_text = " ".join(item["query"] for item in queries)
    for result in results:
        result["excerpt"] = engine.excerpt(result, query=query_text,
                                          max_chars=excerpt_chars, safe=True)
    return results, "检索自本地知识库。"


def merge_profile_pack(cards, profile, limit):
    if not profile:
        return cards
    seen = {card.get("id") for card in cards}
    for card in profile.get("pack") or []:
        if len(cards) >= limit:
            break
        if card.get("id") in seen:
            continue
        cards.append(card)
        seen.add(card.get("id"))
    return cards


def build_reply(message, profile, notes, kb, top, excerpt_chars, cache_dir, rebuild,
                no_search, from_role):
    message_signals = detect_signals([{
        "speaker": "对方" if from_role == "other" else "我",
        "text": message,
        "ts": None,
        "break_before": False,
        "system": False,
        "media": False,
    }], notes, me="我", other="对方")
    intent = classify_intent(message, profile)
    risk = combine_risk((profile or {}).get("risk"), intent, message_signals)
    if risk["hard_stop"] or risk["level"] == "紧急":
        intent = dict(intent)
        intent["drafts"] = []
        if risk["hard_stop"]:
            intent["strategy"] = "先停止恋爱/性相关推进，确认安全与年龄；优先求助与转介。"
            intent["moves"] = ["确认当前是否安全", "涉及未成年人：停止并联系监护人/学校/12355",
                               "涉及即时危险：110/120，心理援助 12356"]
            intent["avoid"] = ["不要再推进见面、影像或性话题", "不要转账", "不要单独见面"]
        else:
            intent["strategy"] = "当前判断为紧急风险，先安全和求助，不生成关系推进话术。"
            intent["moves"] = ["确认人身安全与是否有人陪同", "保留威胁、影像、转账证据",
                               "联系 110/120/12356 或可信亲友"]
            intent["avoid"] = ["不要单独见面", "不要满足勒索或转账", "不要以暴制暴或反向跟踪"]
    queries = build_reply_queries(intent, message, profile, risk)
    cards = []
    pack_note = ""
    if no_search:
        pack_note = "已跳过检索（--no-search）。"
    else:
        cards, pack_note = retrieve_cards(kb, queries, top, excerpt_chars, cache_dir, rebuild)
    if profile and not risk["hard_stop"]:
        cards = merge_profile_pack(cards, profile, top)
        if profile.get("pack") and not cards:
            pack_note = "使用画像缓存中的卡片包。"
    context = {}
    if profile:
        context = {
            "stage": profile.get("stage"),
            "trend": (profile.get("trend") or {}).get("label"),
            "risk": (profile.get("risk") or {}).get("level"),
            "reciprocity": (profile.get("metrics") or {}).get("reciprocity", {}).get("score"),
            "summary": profile.get("conclusion"),
            "recent": (profile.get("recent") or [])[-5:],
        }
    return {
        "format": "emochat-reply-v1",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "from": from_role,
        "message": core.mask_pii(message),
        "intent": intent,
        "risk": risk,
        "queries": queries,
        "cards": cards,
        "pack_note": pack_note,
        "context": context,
        "notes": notes,
    }


def render_reply(payload):
    intent = payload["intent"]
    risk = payload["risk"]
    lines = [
        "# 单条回复包",
        "",
        "- 消息：%s" % payload["message"].replace("\n", " ")[:180],
    ]
    context = payload.get("context") or {}
    if context:
        lines.append("- 画像：阶段=%s；趋势=%s；风险=%s；互惠度=%s/100" % (
            context.get("stage"), context.get("trend"), context.get("risk"),
            context.get("reciprocity"),
        ))
    lines.extend([
        "- 判断：%s（%s置信）%s" % (
            intent["label"], intent["confidence"],
            ("；次要：" + "、".join(item["label"] for item in intent.get("secondary") or []))
            if intent.get("secondary") else "",
        ),
        "- 风险：%s（%s）" % (risk["level"], risk["summary"]),
        "",
        "## 回复策略",
        intent["strategy"],
        "",
    ])
    for index, move in enumerate(intent.get("moves") or [], 1):
        lines.append("%d. %s" % (index, move))
    lines.extend(["", "## 依据卡片"])
    if payload["cards"]:
        for card in payload["cards"][:5]:
            lines.append("### [%s] %s" % (card.get("id"), card.get("title")))
            if card.get("excerpt"):
                lines.append("- 摘要：%s" % card["excerpt"].replace("\n", " ")[:600])
            lines.append("")
    else:
        lines.append(payload.get("pack_note") or "未返回卡片。")
    lines.extend(["", "## 三版草稿（骨架，按你的语气改）"])
    drafts = intent.get("drafts") or []
    labels = ("轻量版", "明确版", "边界/停止版")
    if drafts:
        for label, draft in zip(labels, drafts):
            lines.append("### %s" % label)
            lines.append(draft)
            lines.append("")
    else:
        lines.append("当前判断为高风险/危机，不生成关系推进话术；先按下面的安全动作处理。")
        lines.append("")
    lines.extend(["## 不要做"])
    for item in intent.get("avoid") or []:
        lines.append("- %s" % item)
    lines.extend(["", "## 还需要确认"])
    for item in intent.get("needs") or []:
        lines.append("- %s" % item)
    lines.extend(["", "## 安全提示"])
    if risk["hard_stop"]:
        lines.append("- 涉及未成年人或即时危险：停止恋爱/性相关内容；110/120/12356，未成年人 12355。")
    elif risk["level"] in ("紧急", "高"):
        lines.append("- 先安全与止损：不转账、不发送影像、不单独见面；紧急 110/120，反诈 96110。")
    else:
        lines.append("- 这是沟通建议，不保证结果；对方说“不”时停止推进。")
    if payload.get("queries"):
        lines.extend(["", "## 本次检索词"])
        for item in payload["queries"]:
            lines.append("- `%s`（%s）" % (item["query"], item["reason"]))
    return "\n".join(lines).rstrip() + "\n"


def command_profile(args):
    started = time.perf_counter()
    text = read_text_auto(args.transcript)
    parsed = parse_transcript(
        text, me=args.me, session_gap=args.session_gap, fmt=args.format
    )
    parsed["source_file"] = str(args.transcript)
    total_started = time.perf_counter() - started

    out_path = Path(args.out) if args.out else default_profile_path(args.transcript, args.cache_dir)
    previous = load_json(out_path) if args.append else None
    notes = collect_notes(args, previous)
    kb = None if args.no_search else core.resolve_kb(args.kb)
    if not args.no_search and kb is None:
        parsed["warnings"].append(
            "未找到知识库，已跳过卡片检索；可设置 EMOCHAT_KB 或传 --kb。"
        )

    build_started = time.perf_counter()
    profile = build_profile(
        parsed, notes, kb, args.search_top, args.excerpt, args.cache_dir,
        args.rebuild_index, args.no_search,
    )
    build_elapsed = time.perf_counter() - build_started

    delta_text = compute_delta(previous, profile, parsed["messages"]) if args.append else ""
    profile_file = ""
    if not args.no_save:
        save_json(out_path, profile)
        profile_file = str(out_path)
    if args.json:
        payload = dict(profile)
        payload["profile_file"] = profile_file
        if delta_text:
            payload["delta"] = delta_text
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(render_profile(profile, profile_file, delta_text), end="")
    if args.timing:
        print(
            "timing: total=%.0fms parse=%.1fms profile+search=%.1fms messages=%d pack=%d"
            % (
                (time.perf_counter() - started) * 1000,
                total_started * 1000,
                build_elapsed * 1000,
                len(parsed["messages"]),
                len(profile["pack"]),
            ),
            file=sys.stderr,
        )
    return 0


def command_reply(args):
    started = time.perf_counter()
    message = args.message
    if not message or message == "-":
        message = sys.stdin.read()
    message = core.normalize_text(message).strip()
    if not message:
        raise SystemExit("请用 --message 提供一条消息，或从 stdin 传入。")
    profile = None
    if args.profile:
        profile = load_json(args.profile)
        if profile is None:
            raise SystemExit("无法读取画像文件: %s" % args.profile)
        if profile.get("format") != "emochat-profile-v1":
            raise SystemExit("画像文件格式不匹配: %s" % args.profile)
    notes = list(profile.get("notes") or []) if profile else []
    for note in args.notes or []:
        if note and note not in notes:
            notes.append(note)
    kb = None if args.no_search else core.resolve_kb(args.kb)
    payload = build_reply(
        message, profile, notes, kb, max(3, args.top), args.excerpt,
        args.cache_dir, args.rebuild_index, args.no_search, args.from_role,
    )
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(render_reply(payload), end="")
    if args.timing:
        print(
            "timing: total=%.0fms cards=%d intent=%s"
            % ((time.perf_counter() - started) * 1000, len(payload["cards"]), payload["intent"]["id"]),
            file=sys.stderr,
        )
    return 0


def build_parser():
    parser = argparse.ArgumentParser(description="EmoChat 聊天记录画像与单条回复快速通道")
    subparsers = parser.add_subparsers(dest="command")

    profile = subparsers.add_parser("profile", help="分析一段聊天记录，生成画像与卡片包")
    profile.add_argument("transcript", help="UTF-8 文本或 JSON 聊天记录")
    profile.add_argument("--me", help="我在记录中的显示名；默认第一位发言者")
    profile.add_argument("--notes", action="append", default=[], help="人物/背景补充，可重复")
    profile.add_argument("--notes-file", help="人物/背景补充文件，一行一条")
    profile.add_argument("--session-gap", type=int, default=SESSION_GAP_DEFAULT,
                         help="会话切分间隔（分钟），默认 360")
    profile.add_argument("--format", choices=("auto", "lines", "json"), default="auto")
    profile.add_argument("--out", help="画像 JSON 输出路径")
    profile.add_argument("--append", action="store_true", help="与上次画像比较并输出增量")
    profile.add_argument("--no-save", action="store_true", help="不写画像 JSON")
    profile.add_argument("--no-search", action="store_true", help="只做画像，不检索卡片")
    profile.add_argument("--search-top", type=int, default=6, help="卡片包条数，默认 6")
    profile.add_argument("--excerpt", type=int, default=700, help="卡片摘要字数，默认 700")
    profile.add_argument("--json", action="store_true", help="输出 JSON")
    profile.add_argument("--timing", action="store_true", help="向 stderr 输出耗时")
    profile.add_argument("--kb", help="知识库根目录")
    profile.add_argument("--cache-dir", help="索引/画像缓存目录")
    profile.add_argument("--rebuild-index", action="store_true", help="重建检索索引")

    reply = subparsers.add_parser("reply", help="针对一条消息生成回复包")
    reply.add_argument("--message", help="对方发来的消息；用 - 从 stdin 读取")
    reply.add_argument("--profile", help="profile 命令生成的 JSON 画像")
    reply.add_argument("--notes", action="append", default=[], help="临时补充背景，可重复")
    reply.add_argument("--from", dest="from_role", choices=("other", "me"), default="other",
                       help="消息来自对方（默认）还是自己")
    reply.add_argument("--top", type=int, default=5, help="卡片条数，默认 5")
    reply.add_argument("--excerpt", type=int, default=650, help="卡片摘要字数，默认 650")
    reply.add_argument("--no-search", action="store_true", help="只做判断，不检索卡片")
    reply.add_argument("--json", action="store_true", help="输出 JSON")
    reply.add_argument("--timing", action="store_true", help="向 stderr 输出耗时")
    reply.add_argument("--kb", help="知识库根目录")
    reply.add_argument("--cache-dir", help="索引缓存目录")
    reply.add_argument("--rebuild-index", action="store_true", help="重建检索索引")
    return parser


def main():
    setup_streams()
    argv = sys.argv[1:]
    if argv and argv[0] not in ("profile", "reply") and not argv[0].startswith("-"):
        argv.insert(0, "profile")
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 1
    if args.command == "profile":
        return command_profile(args)
    return command_reply(args)


if __name__ == "__main__":
    sys.exit(main())
