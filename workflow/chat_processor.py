"""Chat Processor Module

Handles the complete chat flow with memory and emotion system integration.
Provides prompt templates and LLM output parsing.
Integrates multi-layer intent recognition for token optimization.
"""

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import chat_db
import memory_manager
from emotion_detector import (
    EmotionResult,
    LLMOutputResult,
    apply_confidence_threshold,
    parse_llm_output,
)
from intent_types import IntentCategory, IntentResult
from response_strategy import (
    ResponseStrategy,
    build_strategy_prompt,
    get_tone_description,
    select_strategy,
)


# ============ Configuration ============

def _get_system_setting(key: str, default: bool) -> bool:
    """Get a boolean system setting from database."""
    value = chat_db.get_setting(key)
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("true", "1", "yes")
    return bool(value)


def _get_system_threshold(key: str, default: float) -> float:
    """Get a numeric system setting from database."""
    value = chat_db.get_setting(key)
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def is_memory_emotion_enabled() -> bool:
    """Check if memory/emotion system is enabled."""
    return _get_system_setting("system.memory_emotion_enabled", True)


def is_hitl_enabled() -> bool:
    """Check if HITL system is enabled."""
    return _get_system_setting("system.hitl_enabled", True)


def is_intent_recognition_enabled() -> bool:
    """Check if intent recognition system is enabled."""
    return _get_system_setting("system.intent_recognition_enabled", True)


def get_emotion_confidence_threshold() -> float:
    """Get emotion confidence threshold."""
    return _get_system_threshold("system.emotion_confidence_threshold", 0.5)


def is_deep_thinking_enabled() -> bool:
    """Check if deep thinking mode is enabled."""
    return _get_system_setting("llm.deep_thinking_enabled", False)


# 深度思考关闭时追加的提示词
DISABLE_THINKING_PROMPT_SUFFIX = "\n\n请直接回答问题，不需要展示思考过程。保持简洁明了。\n /no_think"


# Logger for this module
logger = logging.getLogger(__name__)


# ============ Prompt Templates ============

CHAT_PROMPT_TEMPLATE = """你是一个友好的 AI 助手。

用户消息: {user_message}

上下文信息:
- 工作记忆: {working_memory_summary}
- 相关记忆: {relevant_long_term_memory}

回复要求:
{strategy_prompt}

你必须以纯 JSON 格式回复，不要包含任何其他文字或 markdown 标记。JSON 格式如下:
{{"emotion":{{"primary":"neutral","category":"neutral","confidence":0.8,"indicators":[]}},"response":"你的回复内容","memory_update":{{"should_store":false,"entries":[]}}}}

emotion.primary 可选值: neutral, happy, excited, grateful, curious, sad, anxious, frustrated, confused, help_seeking, info_seeking, validation_seeking
emotion.category 可选值: neutral, positive, negative, seeking

【记忆保存格式】
memory_update 用于保存用户信息，格式：
- should_store: true/false
- entries: [{{"category":"preference|fact|pattern","key":"简洁标签","value":"具体内容"}}]
示例：{{"should_store":true,"entries":[{{"category":"fact","key":"用户姓名","value":"小明"}}]}}

{mcp_instruction}

{hitl_instruction}

现在请直接输出 JSON:"""


# ============ HITL Instruction Template ============

HITL_INSTRUCTION = """
人机交互表单 (HITL) - 重要：请积极使用表单收集用户信息！

hitl_request 格式:
{{
  "hitl_request": {{
    "type": "form",
    "title": "表单标题",
    "description": "可选的描述文字",
    "fields": [
      {{
        "name": "字段名",
        "type": "select|multiselect|text|textarea|radio|checkbox|number|slider",
        "label": "显示标签",
        "required": true/false,
        "options": [{{"value": "值", "label": "显示文字"}}]  // select/radio/checkbox 需要
      }}
    ],
    "context": {{
      "intent": "collect_preference",
      "memory_category": "preference"
    }}
  }}
}}

【积极触发策略 - 请主动使用表单！】

1. 主动询问策略 (Proactive Inquiry):
   - 当相关记忆较少或为空时，主动通过表单了解用户
   - 对话开始时，可以用表单收集用户基本偏好
   示例：用户说"你好"，相关记忆为空
   {{"response":"你好！让我更好地了解你","hitl_request":{{"type":"form","title":"认识你","fields":[{{"name":"name","type":"text","label":"怎么称呼你","required":false}},{{"name":"interests","type":"multiselect","label":"你感兴趣的话题","required":false,"options":[{{"value":"tech","label":"科技"}},{{"value":"music","label":"音乐"}},{{"value":"sports","label":"运动"}},{{"value":"food","label":"美食"}},{{"value":"travel","label":"旅行"}}]}}],"context":{{"intent":"collect_preference","memory_category":"preference"}}}}}}

2. 话题深化触发 (Topic Deepening):
   - 用户提到某个领域但未详细说明时，用表单深入了解
   - 用户表达模糊喜好时（如"我喜欢..."），用表单收集具体偏好
   示例：用户说"我喜欢听音乐"
   {{"response":"音乐是很棒的爱好！让我了解你的音乐品味","hitl_request":{{"type":"form","title":"音乐偏好","fields":[{{"name":"genre","type":"multiselect","label":"喜欢的音乐类型","required":true,"options":[{{"value":"pop","label":"流行"}},{{"value":"rock","label":"摇滚"}},{{"value":"classical","label":"古典"}},{{"value":"jazz","label":"爵士"}},{{"value":"electronic","label":"电子"}}]}},{{"name":"when","type":"select","label":"通常什么时候听","required":false,"options":[{{"value":"work","label":"工作时"}},{{"value":"commute","label":"通勤时"}},{{"value":"relax","label":"休息时"}},{{"value":"exercise","label":"运动时"}}]}}],"context":{{"intent":"collect_preference","memory_category":"preference"}}}}}}

3. 情感驱动触发 (Emotion-driven):
   - 检测到积极情绪时，收集让用户开心的事物
   - 检测到消极情绪时，了解用户的困扰
   示例：用户说"今天心情很好，刚看完一部好电影"
   {{"response":"听起来很棒！好奇你喜欢什么类型的电影","hitl_request":{{"type":"form","title":"电影偏好","fields":[{{"name":"genre","type":"multiselect","label":"喜欢的电影类型","required":true,"options":[{{"value":"action","label":"动作片"}},{{"value":"comedy","label":"喜剧片"}},{{"value":"scifi","label":"科幻片"}},{{"value":"romance","label":"爱情片"}},{{"value":"thriller","label":"悬疑片"}}]}}],"context":{{"intent":"collect_preference","memory_category":"preference"}}}}}}

4. 记忆补全触发 (Memory Gap Detection):
   - 对话涉及某话题但相关记忆为空时，通过表单补全
   - 用户行为暗示某偏好但记忆中没有记录时，主动确认
   示例：用户问"推荐一本书"，但记忆中没有阅读偏好
   {{"response":"我来帮你推荐！先了解下你的阅读口味","hitl_request":{{"type":"form","title":"阅读偏好","fields":[{{"name":"genre","type":"multiselect","label":"喜欢的书籍类型","required":true,"options":[{{"value":"fiction","label":"小说"}},{{"value":"nonfiction","label":"非虚构"}},{{"value":"tech","label":"技术"}},{{"value":"selfhelp","label":"自我提升"}},{{"value":"history","label":"历史"}}]}},{{"name":"format","type":"select","label":"偏好的阅读方式","required":false,"options":[{{"value":"paper","label":"纸质书"}},{{"value":"ebook","label":"电子书"}},{{"value":"audio","label":"有声书"}}]}}],"context":{{"intent":"collect_preference","memory_category":"preference"}}}}}}

5. 问答转表单 (Question-to-Form) - 核心策略:
   - 当你想问用户问题时，优先用表单而非纯文本提问
   - 任何可以转化为选项的问题，都应该用表单收集
   - 这样用户回答更方便，数据也更结构化
   示例：想问用户想去日本哪个城市
   {{"response":"听说你想去日本，真不错呢！那边的科技和电影文化也很有意思","hitl_request":{{"type":"form","title":"日本旅行计划","fields":[{{"name":"city","type":"select","label":"最想去的城市","required":false,"options":[{{"value":"tokyo","label":"东京"}},{{"value":"osaka","label":"大阪"}},{{"value":"kyoto","label":"京都"}},{{"value":"hokkaido","label":"北海道"}},{{"value":"okinawa","label":"冲绳"}}]}},{{"name":"experience","type":"multiselect","label":"想体验的活动","required":false,"options":[{{"value":"food","label":"美食探店"}},{{"value":"anime","label":"动漫圣地巡礼"}},{{"value":"temple","label":"寺庙神社"}},{{"value":"shopping","label":"购物"}},{{"value":"nature","label":"自然风光"}},{{"value":"tech","label":"科技体验"}}]}}],"context":{{"intent":"collect_preference","memory_category":"preference"}}}}}}
   示例：想问用户周末计划
   {{"response":"周末快到了！","hitl_request":{{"type":"form","title":"周末计划","fields":[{{"name":"activity","type":"select","label":"周末打算做什么","required":false,"options":[{{"value":"rest","label":"在家休息"}},{{"value":"outdoor","label":"户外活动"}},{{"value":"social","label":"和朋友聚会"}},{{"value":"study","label":"学习充电"}},{{"value":"entertainment","label":"看电影/追剧"}}]}}],"context":{{"intent":"collect_preference","memory_category":"pattern"}}}}}}

【核心原则】
凡是你想向用户提问的内容，都应该优先考虑用表单收集！表单比纯文本提问更友好、更高效。

6. 计划提醒触发 (Plan/Reminder Detection) - 重要:
   - 当用户提到时间相关的计划、安排、提醒时，触发计划表单
   - 时间关键词：明天、后天、下周、下月、X点、X日、X号、周X、月X
   - 计划关键词：提醒、记得、别忘了、要、需要、打算、计划、安排、会议、开会、约、预约
   - 识别到时间意图后，提取标题、描述和预估时间，预填到表单
   示例1：用户说"提醒我明天下午3点开会"
   {{"response":"好的，让我帮你设置这个提醒","hitl_request":{{"type":"form","title":"创建计划提醒","description":"请确认或修改以下计划信息，系统将在指定时间提醒您。","fields":[{{"name":"title","type":"text","label":"计划标题","required":true,"default":"开会"}},{{"name":"description","type":"textarea","label":"详细描述","required":false}},{{"name":"target_datetime","type":"datetime","label":"目标时间","required":true}},{{"name":"reminder_offset","type":"select","label":"提前提醒","required":true,"default":"10","options":[{{"value":"0","label":"准时提醒"}},{{"value":"5","label":"提前5分钟"}},{{"value":"10","label":"提前10分钟"}},{{"value":"30","label":"提前30分钟"}},{{"value":"60","label":"提前1小时"}}]}},{{"name":"repeat_type","type":"select","label":"重复","required":true,"default":"none","options":[{{"value":"none","label":"不重复"}},{{"value":"daily","label":"每天"}},{{"value":"weekly","label":"每周"}},{{"value":"monthly","label":"每月"}}]}}],"context":{{"intent":"collect_plan","memory_category":"plan"}}}}}}
   示例2：用户说"下周三10点要交报告，别让我忘了"
   {{"response":"没问题，我来帮你记住这件事","hitl_request":{{"type":"form","title":"创建计划提醒","description":"请确认或修改以下计划信息，系统将在指定时间提醒您。","fields":[{{"name":"title","type":"text","label":"计划标题","required":true,"default":"交报告"}},{{"name":"description","type":"textarea","label":"详细描述","required":false}},{{"name":"target_datetime","type":"datetime","label":"目标时间","required":true}},{{"name":"reminder_offset","type":"select","label":"提前提醒","required":true,"default":"10","options":[{{"value":"0","label":"准时提醒"}},{{"value":"5","label":"提前5分钟"}},{{"value":"10","label":"提前10分钟"}},{{"value":"30","label":"提前30分钟"}},{{"value":"60","label":"提前1小时"}}]}},{{"name":"repeat_type","type":"select","label":"重复","required":true,"default":"none","options":[{{"value":"none","label":"不重复"}},{{"value":"daily","label":"每天"}},{{"value":"weekly","label":"每周"}},{{"value":"monthly","label":"每月"}}]}}],"context":{{"intent":"collect_plan","memory_category":"plan"}}}}}}
   示例3：用户说"每天早上8点提醒我吃药"
   {{"response":"好的，我来帮你设置每日提醒","hitl_request":{{"type":"form","title":"创建计划提醒","description":"请确认或修改以下计划信息，系统将在指定时间提醒您。","fields":[{{"name":"title","type":"text","label":"计划标题","required":true,"default":"吃药"}},{{"name":"description","type":"textarea","label":"详细描述","required":false}},{{"name":"target_datetime","type":"datetime","label":"目标时间","required":true}},{{"name":"reminder_offset","type":"select","label":"提前提醒","required":true,"default":"0","options":[{{"value":"0","label":"准时提醒"}},{{"value":"5","label":"提前5分钟"}},{{"value":"10","label":"提前10分钟"}},{{"value":"30","label":"提前30分钟"}},{{"value":"60","label":"提前1小时"}}]}},{{"name":"repeat_type","type":"select","label":"重复","required":true,"default":"daily","options":[{{"value":"none","label":"不重复"}},{{"value":"daily","label":"每天"}},{{"value":"weekly","label":"每周"}},{{"value":"monthly","label":"每月"}}]}}],"context":{{"intent":"collect_plan","memory_category":"plan"}}}}}}

7. 图形化展示触发 (Visual Display) - 重要:
   - 当用户请求比较、对比、列表、表格、流程图、架构图等可视化内容时，使用 visual_display 类型
   - visual_display 用于向用户展示结构化数据，不收集用户输入
   - 支持两种组件: table（表格）和 ascii（ASCII艺术/流程图）

   visual_display 格式:
   {{"hitl_request":{{"type":"visual_display","title":"展示标题","description":"可选描述","displays":[{{"type":"table|ascii","data":{{...}}}}],"dismiss_label":"关闭"}}}}

   table 组件格式:
   {{"type":"table","data":{{"headers":["列1","列2","列3"],"rows":[["值1","值2","值3"],["值4","值5","值6"]],"alignment":["left","center","right"],"caption":"可选表格标题"}}}}

   ascii 组件格式:
   {{"type":"ascii","data":{{"content":"ASCII艺术内容","title":"可选标题"}}}}

   触发场景示例:
   示例1：用户说"比较一下 iPhone 和 Android 的优缺点"
   {{"response":"好的，让我用表格为你展示对比","hitl_request":{{"type":"visual_display","title":"iPhone vs Android 对比","displays":[{{"type":"table","data":{{"headers":["特性","iPhone","Android"],"rows":[["系统流畅度","优秀","因设备而异"],["生态系统","封闭统一","开放多样"],["价格区间","较高","覆盖全价位"],["自定义程度","有限","高度自由"]],"caption":"主要特性对比"}}}}]}}}}

   示例2：用户说"画一个简单的流程图说明登录过程"
   {{"response":"好的，这是登录流程的示意图","hitl_request":{{"type":"visual_display","title":"登录流程图","displays":[{{"type":"ascii","data":{{"content":"┌─────────┐\\n│  开始   │\\n└────┬────┘\\n     │\\n     v\\n┌─────────┐\\n│输入账号 │\\n└────┬────┘\\n     │\\n     v\\n┌─────────┐\\n│输入密码 │\\n└────┬────┘\\n     │\\n     v\\n◇ 验证 ◇──否──> [错误提示]\\n     │\\n    是\\n     │\\n     v\\n┌─────────┐\\n│登录成功 │\\n└─────────┘","title":"用户登录流程"}}}}]}}}}

   示例3：用户说"列出常用的 Git 命令"
   {{"response":"好的，这是常用 Git 命令汇总","hitl_request":{{"type":"visual_display","title":"常用 Git 命令","displays":[{{"type":"table","data":{{"headers":["命令","用途","示例"],"rows":[["git init","初始化仓库","git init"],["git clone","克隆仓库","git clone url"],["git add","添加文件","git add ."],["git commit","提交更改","git commit -m 'msg'"],["git push","推送到远程","git push origin main"],["git pull","拉取更新","git pull"]]}}}}]}}}}

【visual_display 触发关键词】
- 比较、对比、VS、versus、哪个好
- 列出、列表、清单、汇总
- 表格、用表格展示、以表格形式
- 流程图、架构图、示意图
- 画一个、展示一下结构

【不要使用表单的情况】
- 用户正在寻求帮助解决紧急问题（如"帮我快速解决..."）
- 用户已在消息中给出明确答案（如"我要Python"、"选A"）
- 简单的是/否确认问题
"""

HITL_INSTRUCTION_DISABLED = ""

# Simplified HITL instruction for continuation scenarios
# Much shorter than full HITL_INSTRUCTION (~300 chars vs ~3K chars)
HITL_CONTINUATION_INSTRUCTION = """
如果需要继续收集信息，可使用 hitl_request 表单:
{{"hitl_request":{{"type":"form","title":"表单标题","fields":[{{"name":"字段名","type":"select|text|textarea|radio","label":"标签","required":true,"options":[{{"value":"值","label":"文字"}}]}}]}}}}

注意：只有确实需要追问时才发起新表单，避免过度打扰用户。
"""

SIMPLE_SYSTEM_PROMPT = """你是一个友好的 AI 助手。"""


# ============ Intent-Specific Prompt Snippets ============
# These are much smaller (~200-400 chars) than the full HITL_INSTRUCTION (~3K chars)
# Used when intent recognition matches a specific intent type

# HITL base format - included with all HITL snippets
HITL_BASE_FORMAT = """
hitl_request 格式:
{{"hitl_request":{{"type":"form","title":"表单标题","description":"可选描述","fields":[{{"name":"字段名","type":"select|multiselect|text|textarea|radio|checkbox|number|slider|datetime","label":"显示标签","required":true/false,"options":[{{"value":"值","label":"显示文字"}}],"default":"默认值"}}],"context":{{"intent":"意图","memory_category":"类别"}}}}}}
"""

# Memory intent snippets (for 4 memory save rules)
MEMORY_INTENT_SNIPPETS = {
    "preference": """【记忆保存指令】用户正在表达偏好。请在 memory_update 中保存:
- category: "preference"
- key: 简洁的偏好标签（如"编程语言偏好"、"音乐类型偏好"）
- value: 具体的偏好内容""",

    "fact": """【记忆保存指令】用户正在分享个人事实。请在 memory_update 中保存:
- category: "fact"
- key: 简洁的事实标签（如"用户姓名"、"用户职业"、"工作地点"）
- value: 具体的事实信息""",

    "pattern": """【记忆保存指令】用户正在描述行为模式。请在 memory_update 中保存:
- category: "pattern"
- key: 简洁的模式标签（如"上班时间"、"学习习惯"）
- value: 具体的行为模式""",

    "opinion": """【记忆保存指令】用户正在表达个人观点。请在 memory_update 中保存:
- category: "preference"
- key: 简洁的观点标签（如"对AI的看法"、"对学习的理解"）
- value: 观点的核心要点""",
}

# HITL intent snippets (for 6 HITL strategies)
HITL_INTENT_SNIPPETS = {
    "proactive_inquiry": HITL_BASE_FORMAT + """
【HITL指令】检测到问候意图。必须生成 hitl_request 表单主动了解用户:
示例：{{"response":"你好！让我更好地了解你","hitl_request":{{"type":"form","title":"认识你","fields":[{{"name":"name","type":"text","label":"怎么称呼你","required":false}},{{"name":"interests","type":"multiselect","label":"你感兴趣的话题","required":false,"options":[{{"value":"tech","label":"科技"}},{{"value":"music","label":"音乐"}},{{"value":"sports","label":"运动"}},{{"value":"food","label":"美食"}},{{"value":"travel","label":"旅行"}}]}}],"context":{{"intent":"collect_preference","memory_category":"preference"}}}}}}""",

    "topic_deepening": HITL_BASE_FORMAT + """
【HITL指令】用户提到感兴趣的话题。必须生成 hitl_request 表单深入了解该话题的具体偏好:
- 根据用户提到的话题类型设计合适的 fields
- 使用 multiselect 收集多个选项
- context.intent: "collect_preference"
示例（音乐话题）：{{"response":"音乐是很棒的爱好！让我了解你的音乐品味","hitl_request":{{"type":"form","title":"音乐偏好","fields":[{{"name":"genre","type":"multiselect","label":"喜欢的音乐类型","required":true,"options":[{{"value":"pop","label":"流行"}},{{"value":"rock","label":"摇滚"}},{{"value":"classical","label":"古典"}},{{"value":"jazz","label":"爵士"}}]}}],"context":{{"intent":"collect_preference","memory_category":"preference"}}}}}}""",

    "emotion_driven": HITL_BASE_FORMAT + """
【HITL指令】检测到用户情绪表达。必须生成 hitl_request 表单:
- 积极情绪: 用表单了解让用户开心的事物
- 消极情绪: 用表单了解用户的困扰
- context.intent: "collect_preference"
示例：{{"response":"听起来很棒！好奇你喜欢什么类型的电影","hitl_request":{{"type":"form","title":"电影偏好","fields":[{{"name":"genre","type":"multiselect","label":"喜欢的电影类型","required":true,"options":[{{"value":"action","label":"动作片"}},{{"value":"comedy","label":"喜剧片"}},{{"value":"scifi","label":"科幻片"}}]}}],"context":{{"intent":"collect_preference","memory_category":"preference"}}}}}}""",

    "memory_gap": HITL_BASE_FORMAT + """
【HITL指令】用户请求推荐/建议，但相关记忆不足。必须生成 hitl_request 表单收集偏好:
示例（推荐书）：{{"response":"我来帮你推荐！先了解下你的阅读口味","hitl_request":{{"type":"form","title":"阅读偏好","fields":[{{"name":"genre","type":"multiselect","label":"喜欢的书籍类型","required":true,"options":[{{"value":"fiction","label":"小说"}},{{"value":"nonfiction","label":"非虚构"}},{{"value":"tech","label":"技术"}},{{"value":"selfhelp","label":"自我提升"}}]}},{{"name":"format","type":"select","label":"偏好的阅读方式","required":false,"options":[{{"value":"paper","label":"纸质书"}},{{"value":"ebook","label":"电子书"}},{{"value":"audio","label":"有声书"}}]}}],"context":{{"intent":"collect_preference","memory_category":"preference"}}}}}}""",

    "question_to_form": HITL_BASE_FORMAT + """
【HITL指令】用户的问题可以转化为表单。必须将问题转换为结构化的 hitl_request 表单:
- 使用 select/multiselect 提供选项
- 比纯文本提问更友好高效
示例（旅行计划）：{{"response":"听说你想去日本，真不错呢！","hitl_request":{{"type":"form","title":"日本旅行计划","fields":[{{"name":"city","type":"select","label":"最想去的城市","required":false,"options":[{{"value":"tokyo","label":"东京"}},{{"value":"osaka","label":"大阪"}},{{"value":"kyoto","label":"京都"}}]}},{{"name":"experience","type":"multiselect","label":"想体验的活动","required":false,"options":[{{"value":"food","label":"美食探店"}},{{"value":"anime","label":"动漫圣地巡礼"}},{{"value":"temple","label":"寺庙神社"}}]}}],"context":{{"intent":"collect_preference","memory_category":"preference"}}}}}}""",

    "plan_reminder": HITL_BASE_FORMAT + """
【HITL指令】检测到时间相关的计划/提醒意图。必须生成计划提醒表单:
- 从用户消息中提取标题和时间信息预填到 default
- context.intent: "collect_plan", memory_category: "plan"
示例：{{"response":"好的，让我帮你设置这个提醒","hitl_request":{{"type":"form","title":"创建计划提醒","description":"请确认或修改以下计划信息","fields":[{{"name":"title","type":"text","label":"计划标题","required":true,"default":"开会"}},{{"name":"description","type":"textarea","label":"详细描述","required":false}},{{"name":"target_datetime","type":"datetime","label":"目标时间","required":true}},{{"name":"reminder_offset","type":"select","label":"提前提醒","required":true,"default":"10","options":[{{"value":"0","label":"准时提醒"}},{{"value":"5","label":"提前5分钟"}},{{"value":"10","label":"提前10分钟"}},{{"value":"30","label":"提前30分钟"}},{{"value":"60","label":"提前1小时"}}]}},{{"name":"repeat_type","type":"select","label":"重复","required":true,"default":"none","options":[{{"value":"none","label":"不重复"}},{{"value":"daily","label":"每天"}},{{"value":"weekly","label":"每周"}},{{"value":"monthly","label":"每月"}}]}}],"context":{{"intent":"collect_plan","memory_category":"plan"}}}}}}""",

    "visual_display": """
【HITL指令】检测到图形化展示意图。必须生成 visual_display 类型的 hitl_request:
- 用于展示结构化数据（表格、流程图等），不收集用户输入
- 支持 table（表格）和 ascii（ASCII艺术/流程图）两种组件

visual_display 格式:
{{"hitl_request":{{"type":"visual_display","title":"展示标题","description":"可选描述","displays":[{{"type":"table|ascii","data":{{...}}}}],"dismiss_label":"关闭"}}}}

table 格式: {{"type":"table","data":{{"headers":["列1","列2"],"rows":[["值1","值2"]],"caption":"可选标题"}}}}
ascii 格式: {{"type":"ascii","data":{{"content":"ASCII内容","title":"可选标题"}}}}

示例1（对比）：{{"response":"好的，让我用表格为你展示对比","hitl_request":{{"type":"visual_display","title":"对比分析","displays":[{{"type":"table","data":{{"headers":["特性","选项A","选项B"],"rows":[["优点","xxx","yyy"],["缺点","aaa","bbb"]]}}}}]}}}}
示例2（列表）：{{"response":"这是常用命令汇总","hitl_request":{{"type":"visual_display","title":"命令列表","displays":[{{"type":"table","data":{{"headers":["命令","用途"],"rows":[["cmd1","描述1"],["cmd2","描述2"]]}}}}]}}}}
示例3（流程图）：{{"response":"这是流程示意图","hitl_request":{{"type":"visual_display","title":"流程图","displays":[{{"type":"ascii","data":{{"content":"[开始] -> [步骤1] -> [步骤2] -> [结束]","title":"流程"}}}}]}}}}""",
}


# MCP tool call intent snippet
# This is a template - actual tool descriptions are injected dynamically
MCP_INTENT_SNIPPET_TEMPLATE = """
【MCP工具调用指令】检测到用户想要使用工具。

{mcp_tools_description}

如果你需要调用工具，在JSON响应中添加 tool_call 字段:
{{"response":"你的回复","tool_call":{{"name":"服务名称","method":"方法名","arguments":{{"参数名":"参数值"}}}}}}

tool_call 字段说明:
- name: MCP服务名称（如上述服务列表中的服务名）
- method: 要调用的方法名（必须使用上述工具列表中的"方法名"，而不是服务名）
- arguments: 传递给工具的参数对象（根据上述"必需参数"填写）

重要：method 必须使用工具列表中给出的实际方法名，而不是服务名称。
"""


def get_mcp_intent_snippet(service_name: Optional[str] = None) -> str:
    """Get MCP intent snippet with tool descriptions.

    Uses cached tool information if available (populated when service starts).
    Falls back to service-level description if cache is empty.

    Args:
        service_name: Specific service name if known

    Returns:
        MCP intent snippet with tool descriptions
    """
    import mcp_tool_executor

    logger.info(f"[MCP Intent] Getting intent snippet: service_name={service_name}")

    if service_name:
        # Try to get cached tools for specific service
        cached_desc = mcp_tool_executor.get_executor().get_cached_tools_description(service_name)
        if cached_desc:
            tools_desc = cached_desc
            logger.info(f"[MCP Intent] Using cached tools for service: {service_name}")
        else:
            # Fallback to service-level description
            desc = mcp_tool_executor.get_executor().get_tool_description_level1(service_name)
            if desc:
                tools_desc = desc
                logger.info(f"[MCP Intent] Found specific service description: {service_name}")
            else:
                tools_desc = f"[工具] {service_name}: MCP服务"
                logger.info(f"[MCP Intent] Using default description for: {service_name}")
    else:
        # Try to get cached tools for all services
        cached_desc = mcp_tool_executor.get_executor().get_all_cached_tools_description()
        if cached_desc:
            tools_desc = cached_desc
            logger.info(f"[MCP Intent] Using all cached tools description: {len(cached_desc)} chars")
        else:
            # Fallback to service-level descriptions
            tools_desc = mcp_tool_executor.get_mcp_tools_prompt_snippet()
            if not tools_desc:
                tools_desc = "（当前没有可用的MCP工具）"
                logger.info("[MCP Intent] No available MCP tools")
            else:
                logger.info(f"[MCP Intent] Got all tools description: {len(tools_desc)} chars")

    snippet = MCP_INTENT_SNIPPET_TEMPLATE.format(mcp_tools_description=tools_desc)
    logger.info(f"[MCP Intent] Generated snippet: {len(snippet)} chars")
    return snippet


def get_intent_snippet(intent_result: Optional[IntentResult]) -> str:
    """Get the appropriate prompt snippet for an intent.

    Args:
        intent_result: Result from intent recognition

    Returns:
        Intent-specific prompt snippet, or empty string if no match
    """
    if not intent_result or intent_result.is_normal():
        logger.info("[Intent Snippet] No intent or normal intent, returning empty")
        return ""

    intent_type = intent_result.intent_type
    logger.info(f"[Intent Snippet] Getting snippet for: category={intent_result.category}, type={intent_type}")

    if intent_result.is_memory():
        snippet = MEMORY_INTENT_SNIPPETS.get(intent_type, "")
        logger.info(f"[Intent Snippet] Memory intent snippet: {len(snippet)} chars")
        return snippet
    elif intent_result.is_hitl():
        snippet = HITL_INTENT_SNIPPETS.get(intent_type, "")
        logger.info(f"[Intent Snippet] HITL intent snippet: {len(snippet)} chars")
        return snippet
    elif intent_result.is_mcp():
        logger.info(f"[Intent Snippet] MCP intent, service_name={intent_result.mcp_service_name}")
        return get_mcp_intent_snippet(intent_result.mcp_service_name)

    logger.info("[Intent Snippet] Unknown intent category, returning empty")
    return ""


# ============ Data Classes ============

@dataclass
class ChatContext:
    """Context for a chat request."""
    session_id: str
    user_message: str
    working_memory: Optional[memory_manager.WorkingMemory] = None
    relevant_memories: List[memory_manager.RetrievalResult] = None
    previous_emotion: Optional[str] = None
    strategy: Optional[ResponseStrategy] = None
    intent_result: Optional[IntentResult] = None  # Result from intent recognition

    def __post_init__(self):
        if self.relevant_memories is None:
            self.relevant_memories = []


@dataclass
class ChatResult:
    """Result from processing a chat message."""
    response: str
    emotion: Optional[EmotionResult] = None
    strategy: Optional[ResponseStrategy] = None
    memories_used: List[str] = None
    memories_to_store: List[Dict[str, Any]] = None

    def __post_init__(self):
        if self.memories_used is None:
            self.memories_used = []
        if self.memories_to_store is None:
            self.memories_to_store = []


# ============ Context Building ============

def build_chat_context(session_id: str, user_message: str) -> ChatContext:
    """Build complete chat context with memory and previous emotion.

    Args:
        session_id: Session UUID
        user_message: User's message

    Returns:
        ChatContext with all relevant information
    """
    import logging
    logger = logging.getLogger(__name__)

    # Get or create working memory
    working_memory = memory_manager.get_or_create_working_memory(session_id)

    # Retrieve relevant long-term memories
    relevant_memories = memory_manager.retrieve_relevant_memories(
        user_message,
        working_memory=working_memory,
    )

    # Debug: log retrieved memories
    if relevant_memories:
        logger.info(f"[Memory] 检索到 {len(relevant_memories)} 条相关记忆:")
        for r in relevant_memories:
            logger.info(f"  - [{r.memory.category}] {r.memory.key}: {r.memory.value} (score={r.score:.2f})")
    else:
        keywords = memory_manager.extract_keywords(user_message)
        logger.info(f"[Memory] 未检索到相关记忆。提取的关键词: {keywords}")

    # Get previous emotion for strategy selection
    previous_emotion = working_memory.last_emotion

    # Select strategy based on previous emotion (two-phase strategy)
    if previous_emotion:
        prev_emotion_result = EmotionResult(primary=previous_emotion)
        strategy = select_strategy(prev_emotion_result)
    else:
        # First turn: use neutral strategy
        strategy = select_strategy(EmotionResult(primary="neutral"))

    return ChatContext(
        session_id=session_id,
        user_message=user_message,
        working_memory=working_memory,
        relevant_memories=relevant_memories,
        previous_emotion=previous_emotion,
        strategy=strategy,
    )


def format_working_memory_summary(working_memory: Optional[memory_manager.WorkingMemory]) -> str:
    """Format working memory as a summary string.

    Args:
        working_memory: WorkingMemory instance

    Returns:
        Summary string for prompt injection
    """
    if not working_memory:
        return "无"

    parts = []

    if working_memory.current_topic:
        parts.append(f"当前话题: {working_memory.current_topic}")

    parts.append(f"对话轮次: {working_memory.turn_count}")

    if working_memory.last_emotion:
        parts.append(f"上轮情绪: {working_memory.last_emotion}")

    if working_memory.context_variables:
        # Format context variables with special handling for HITL form data
        ctx_parts = []
        for key, value in working_memory.context_variables.items():
            if key.startswith("hitl_") and isinstance(value, dict):
                # Format HITL form data in a readable way
                form_title = key[5:]  # Remove "hitl_" prefix
                fields = value.get("fields", {})
                if fields:
                    field_strs = [f"{k}: {v}" for k, v in fields.items()]
                    ctx_parts.append(f"[表单:{form_title}] {', '.join(field_strs)}")
            else:
                ctx_parts.append(f"{key}={value}")
        if ctx_parts:
            parts.append(f"上下文: {'; '.join(ctx_parts)}")

    return "; ".join(parts) if parts else "无"


def format_relevant_memories(memories: List[memory_manager.RetrievalResult]) -> str:
    """Format relevant memories as a string for prompt injection.

    Args:
        memories: List of RetrievalResult

    Returns:
        Formatted string for prompt
    """
    if not memories:
        return "无"

    parts = []
    for i, result in enumerate(memories[:5], 1):
        m = result.memory
        parts.append(f"{i}. [{m.category}] {m.key}: {m.value}")

    return "\n".join(parts)


def build_system_prompt(context: ChatContext) -> str:
    """Build complete system prompt with context and strategy.

    Uses intent recognition to optimize prompt size:
    - If intent matched: use small intent-specific snippet (~200-400 chars)
    - If no intent: use full HITL_INSTRUCTION (~3K chars) for backward compatibility

    Args:
        context: ChatContext with all information

    Returns:
        Complete system prompt
    """
    working_memory_summary = format_working_memory_summary(context.working_memory)
    relevant_memory_str = format_relevant_memories(context.relevant_memories)
    strategy_prompt = build_strategy_prompt(context.strategy)

    # Determine HITL instruction based on intent recognition
    hitl_enabled = is_hitl_enabled()
    hitl_instruction_type = "none"  # 用于日志
    mcp_instruction = ""  # MCP instruction

    if is_intent_recognition_enabled() and context.intent_result:
        intent_snippet = get_intent_snippet(context.intent_result)

        # Check if this is an MCP intent
        if context.intent_result.is_mcp():
            # MCP intent: use MCP snippet, no HITL instruction
            mcp_instruction = intent_snippet
            hitl_instruction = ""
            hitl_instruction_type = "none (mcp)"
            logger.info(f"[Intent] Using MCP prompt snippet for: {context.intent_result.mcp_service_name or 'general'}")
        elif intent_snippet:
            # Use intent-specific snippet (much smaller)
            hitl_instruction = intent_snippet
            hitl_instruction_type = f"intent_snippet({context.intent_result.intent_type})"
            logger.info(f"[Intent] Using optimized prompt snippet for: {context.intent_result.intent_type}")
        elif context.intent_result.is_normal():
            # Normal conversation: minimal instructions
            hitl_instruction = ""
            hitl_instruction_type = "minimal"
            logger.info("[Intent] Using minimal prompt (normal conversation)")
        else:
            # Fallback to full instruction
            hitl_instruction = HITL_INSTRUCTION if hitl_enabled else HITL_INSTRUCTION_DISABLED
            hitl_instruction_type = "full" if hitl_enabled else "disabled"
    else:
        # No intent recognition: use full instruction for backward compatibility
        hitl_instruction = HITL_INSTRUCTION if hitl_enabled else HITL_INSTRUCTION_DISABLED
        hitl_instruction_type = "full" if hitl_enabled else "disabled"

    # 打印 HITL 状态日志
    hitl_instruction_len = len(hitl_instruction)
    mcp_instruction_len = len(mcp_instruction)
    logger.info(f"[HITL] Prompt contains HITL: enabled={hitl_enabled}, instruction_type={hitl_instruction_type}, instruction_length={hitl_instruction_len}")
    if mcp_instruction_len > 0:
        logger.info(f"[MCP] Prompt contains MCP instruction: length={mcp_instruction_len}")

    prompt = CHAT_PROMPT_TEMPLATE.format(
        user_message=context.user_message,
        working_memory_summary=working_memory_summary,
        relevant_long_term_memory=relevant_memory_str,
        strategy_prompt=strategy_prompt,
        mcp_instruction=mcp_instruction,
        hitl_instruction=hitl_instruction,
    )

    # 深度思考关闭时追加提示词
    if not is_deep_thinking_enabled():
        prompt += DISABLE_THINKING_PROMPT_SUFFIX

    return prompt


# ============ Response Processing ============

def process_llm_response(
    response_text: str,
    context: ChatContext,
) -> ChatResult:
    """Process LLM response, parsing emotion and updating memory.

    Args:
        response_text: Raw LLM response (should be JSON)
        context: Original chat context

    Returns:
        ChatResult with parsed data
    """
    # Parse LLM output
    parsed = parse_llm_output(response_text)

    # Apply confidence threshold
    emotion = apply_confidence_threshold(
        parsed.emotion,
        threshold=get_emotion_confidence_threshold(),
    )

    # Update working memory
    _update_working_memory_after_response(context, emotion)

    # Process memory updates
    memories_to_store = []
    if parsed.memory_update.should_store:
        memories_to_store = _store_suggested_memories(
            context.session_id,
            parsed.memory_update.entries,
        )

    # Update access tracking for used memories
    if context.relevant_memories:
        memory_ids = [r.memory.id for r in context.relevant_memories]
        memory_manager.update_memory_access(memory_ids)

    return ChatResult(
        response=parsed.response,
        emotion=emotion,
        strategy=context.strategy,
        memories_used=[r.memory.id for r in context.relevant_memories],
        memories_to_store=memories_to_store,
    )


def _update_working_memory_after_response(
    context: ChatContext,
    emotion: EmotionResult,
) -> None:
    """Update working memory after processing response.

    Args:
        context: Chat context
        emotion: Detected emotion
    """
    memory_manager.update_working_memory(
        context.session_id,
        last_emotion=emotion.primary,
        increment_turn=True,
    )


def _store_suggested_memories(
    session_id: str,
    entries: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Store LLM-suggested memories.

    Args:
        session_id: Session UUID
        entries: Memory entries to store

    Returns:
        List of stored memory info
    """
    import logging
    logger = logging.getLogger(__name__)

    stored = []

    for entry in entries:
        try:
            memory = memory_manager.create_memory_entry(
                category=entry.get("category", "fact"),
                key=entry["key"],
                value=entry["value"],
                session_id=session_id,
                confidence=0.8,  # LLM suggestions have medium-high confidence
                source="inferred",
            )
            stored.append({
                "id": memory.id,
                "category": memory.category,
                "key": memory.key,
            })
            logger.info(f"[Memory] 保存记忆: [{memory.category}] {memory.key}: {memory.value}")
        except Exception as e:
            logger.warning(f"Failed to store memory: {e}")

    if not entries:
        logger.info("[Memory] LLM 未建议保存任何记忆")

    return stored


# ============ Simple Mode (Fallback) ============

def build_simple_messages(
    system_prompt: str,
    history: List[Dict[str, str]],
    user_message: str,
) -> List[Dict[str, str]]:
    """Build simple message list for non-memory mode.

    Args:
        system_prompt: System prompt
        history: Message history
        user_message: Current user message

    Returns:
        List of message dicts for LLM API
    """
    messages = [{"role": "system", "content": system_prompt}]

    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": user_message})

    return messages


def build_memory_aware_messages(context: ChatContext) -> List[Dict[str, str]]:
    """Build message list with memory and emotion context.

    Args:
        context: Chat context

    Returns:
        List of message dicts for LLM API
    """
    system_prompt = build_system_prompt(context)

    # For memory-aware mode, we use a structured prompt that expects JSON output
    # The user message is already included in the system prompt
    # Use a minimal user message to trigger JSON output
    return [
        {"role": "system", "content": system_prompt},
    ]


# ============ Utility Functions ============

import re

# Pattern to match <thinking>...</thinking> blocks
_THINKING_TAG_PATTERN = re.compile(
    r'<thinking>.*?</thinking>',
    re.IGNORECASE | re.DOTALL
)


def filter_thinking_tags(text: str) -> str:
    """Filter out <thinking>...</thinking> tags from LLM response.

    This is a fallback strategy to remove thinking content when
    deep thinking mode is disabled but the model still outputs it.

    Args:
        text: LLM response text

    Returns:
        Text with thinking tags removed
    """
    if not text:
        return text

    # Only filter if deep thinking is disabled
    if is_deep_thinking_enabled():
        return text

    # Remove <thinking>...</thinking> blocks
    filtered = _THINKING_TAG_PATTERN.sub('', text)

    # Clean up extra whitespace
    filtered = filtered.strip()

    return filtered


def run_intent_recognition(message: str) -> Optional[IntentResult]:
    """Run Layer 1 intent recognition synchronously.

    This is a synchronous wrapper that only uses Layer 1 (rule-based matching).
    For Layer 2 (LLM-based), use the async recognize_intent_async function.

    Args:
        message: User message to analyze

    Returns:
        IntentResult if matched, None otherwise (will be normal conversation)
    """
    if not is_intent_recognition_enabled():
        logger.info("[Intent] Intent recognition disabled")
        return None

    from intent_recognizer import RuleBasedMatcher

    matcher = RuleBasedMatcher()
    result = matcher.match(message)

    if result:
        return result

    # Layer 1 didn't match, return normal intent
    # Layer 2 would require async, handled separately if needed
    logger.info("[Intent] Layer1: no match, returning normal intent")
    return IntentResult.normal()


async def recognize_intent_async(
    message: str,
    llm_client: Any = None,
    api_base: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    layer2_enabled: bool = True,
    layer2_threshold: float = 0.7,
) -> IntentResult:
    """Run full multi-layer intent recognition asynchronously.

    Args:
        message: User message to analyze
        llm_client: HTTP client for Layer 2 LLM calls
        api_base: LLM API base URL
        api_key: API key
        model: Model to use for Layer 2 (defaults to main chat model)
        layer2_enabled: Whether to use Layer 2
        layer2_threshold: Confidence threshold for Layer 2 (default 0.7)

    Returns:
        IntentResult with matched intent
    """
    logger.info(f"[Intent Async] Starting intent recognition: message_len={len(message)}")

    if not is_intent_recognition_enabled():
        logger.info("[Intent Async] Intent recognition disabled")
        return IntentResult.normal()

    from intent_recognizer import recognize_intent, build_mcp_keyword_rules_from_services
    import mcp_manager

    # Build dynamic MCP rules from running services
    pm = mcp_manager.get_process_manager()
    running_services = pm.get_running_servers()
    logger.info(f"[Intent Async] Building MCP rules from {len(running_services)} running services")
    mcp_keyword_rules = build_mcp_keyword_rules_from_services(running_services)
    logger.info(f"[Intent Async] Created {len(mcp_keyword_rules)} MCP keyword rules")

    result = await recognize_intent(
        message=message,
        llm_client=llm_client,
        api_base=api_base,
        api_key=api_key,
        model=model,
        layer2_enabled=layer2_enabled,
        layer2_threshold=layer2_threshold,
        mcp_keyword_rules=mcp_keyword_rules,
    )

    logger.info(f"[Intent Async] Recognition result: category={result.category}, type={result.intent_type}, source={result.source}")
    if result.is_mcp():
        logger.info(f"[Intent Async] MCP service matched: {result.mcp_service_name}")

    return result


def extract_response_text(llm_output: str) -> str:
    """Extract just the response text from LLM output.

    Handles both JSON and plain text outputs.

    Args:
        llm_output: Raw LLM output

    Returns:
        Response text only
    """
    try:
        data = json.loads(llm_output)
        return data.get("response", llm_output)
    except json.JSONDecodeError:
        return llm_output


@dataclass
class ToolCallRequest:
    """Parsed tool call request from LLM output."""
    name: str  # Service name
    method: str  # Method to call
    arguments: Dict[str, Any]  # Arguments to pass


def extract_tool_call(llm_output: str) -> Optional[ToolCallRequest]:
    """Extract tool_call from LLM output if present.

    Args:
        llm_output: Raw LLM output (JSON string)

    Returns:
        ToolCallRequest if tool_call found, None otherwise
    """
    try:
        # Handle potential markdown code blocks
        content = llm_output.strip()
        if content.startswith("```"):
            parts = content.split("```")
            if len(parts) >= 2:
                content = parts[1]
                if content.startswith("json"):
                    content = content[4:]
            content = content.strip()

        data = json.loads(content)
        tool_call = data.get("tool_call")

        if not tool_call:
            return None

        name = tool_call.get("name", "")
        method = tool_call.get("method", name)  # Default method to service name
        arguments = tool_call.get("arguments", {})

        if not name:
            logger.info("[MCP] tool_call found but missing name")
            return None

        logger.info(f"[MCP] Extracted tool_call: name={name}, method={method}")
        return ToolCallRequest(
            name=name,
            method=method,
            arguments=arguments,
        )

    except json.JSONDecodeError:
        return None
    except Exception as e:
        logger.info(f"[MCP] Failed to extract tool_call: {e}")
        return None


# ============ HITL Continuation ============

HITL_CONTINUATION_PROMPT_TEMPLATE = """你是一个友好的 AI 助手。用户刚刚通过表单提供了信息。

{hitl_context}

上下文: {working_memory_summary}
记忆: {relevant_long_term_memory}

{strategy_prompt}

以纯 JSON 格式回复:
{{"emotion":{{"primary":"neutral","category":"neutral","confidence":0.8}},"response":"你的回复","memory_update":{{"should_store":false,"entries":[]}}}}

emotion.primary: neutral|happy|excited|grateful|curious|sad|anxious|frustrated|confused|help_seeking|info_seeking
如需保存记忆: should_store=true, entries添加{{key,value,category(preference|fact|pattern)}}

{mcp_instruction}

{hitl_instruction}

直接输出 JSON:"""


def build_hitl_continuation_prompt(
    session_id: str,
    hitl_context: str,
) -> str:
    """Build prompt for HITL continuation.

    Args:
        session_id: Session UUID
        hitl_context: Context string from build_continuation_context()

    Returns:
        Complete prompt for LLM
    """
    # Get working memory
    working_memory = memory_manager.get_or_create_working_memory(session_id)

    # Get relevant memories (using hitl_context as query for relevance)
    relevant_memories = memory_manager.retrieve_relevant_memories(
        hitl_context,
        working_memory=working_memory,
    )

    # Format memory summaries
    working_memory_summary = format_working_memory_summary(working_memory)
    relevant_memory_str = format_relevant_memories(relevant_memories)

    # Get strategy based on previous emotion
    previous_emotion = working_memory.last_emotion
    if previous_emotion:
        from emotion_detector import EmotionResult
        prev_emotion_result = EmotionResult(primary=previous_emotion)
        strategy = select_strategy(prev_emotion_result)
    else:
        from emotion_detector import EmotionResult
        strategy = select_strategy(EmotionResult(primary="neutral"))

    strategy_prompt = build_strategy_prompt(strategy)

    # Use simplified HITL instruction for continuation (much shorter than full HITL_INSTRUCTION)
    hitl_enabled = is_hitl_enabled()
    hitl_instruction = HITL_CONTINUATION_INSTRUCTION if hitl_enabled else HITL_INSTRUCTION_DISABLED

    # Get MCP instruction - check if hitl_context suggests MCP tool usage
    # We include MCP tools if any are available, so LLM can call them based on form data
    import mcp_tool_executor
    import mcp_manager

    # Check running MCP services
    pm = mcp_manager.get_process_manager()
    running_services = pm.get_running_servers()
    logger.info(f"[HITL] Continuation: {len(running_services)} MCP services running")
    for svc in running_services:
        logger.info(f"[HITL]   - {svc.name}: {svc.description or 'no description'}")

    mcp_instruction = mcp_tool_executor.get_mcp_tools_prompt_snippet()
    if mcp_instruction:
        # Add the tool_call format instruction
        mcp_instruction = f"""
【可用的MCP工具】
{mcp_instruction}

如果用户提交的表单信息需要调用工具（如天气查询、搜索等），请在JSON响应中添加 tool_call 字段:
{{"response":"你的回复","tool_call":{{"name":"服务名称","method":"方法名","arguments":{{"参数名":"参数值"}}}}}}
"""
        logger.info(f"[HITL] Continuation prompt: mcp_instruction added, length={len(mcp_instruction)}")
    else:
        mcp_instruction = ""
        logger.info(f"[HITL] Continuation prompt: NO MCP services available, mcp_instruction is empty")

    # 打印 HITL 状态日志
    logger.info(f"[HITL] Continuation prompt: hitl_enabled={hitl_enabled}, instruction_length={len(hitl_instruction)}")

    return HITL_CONTINUATION_PROMPT_TEMPLATE.format(
        hitl_context=hitl_context,
        working_memory_summary=working_memory_summary,
        relevant_long_term_memory=relevant_memory_str,
        strategy_prompt=strategy_prompt,
        mcp_instruction=mcp_instruction,
        hitl_instruction=hitl_instruction,
    )
