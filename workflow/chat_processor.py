"""Chat Processor Module

Handles the complete chat flow with memory and emotion system integration.
Provides prompt templates and LLM output parsing.
Integrates multi-layer intent recognition for token optimization.
"""

import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

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

# Environment variable to toggle memory/emotion system
# Default to True - set USE_MEMORY_EMOTION_SYSTEM=false to disable
USE_MEMORY_EMOTION_SYSTEM = os.environ.get("USE_MEMORY_EMOTION_SYSTEM", "true").lower() == "true"

# Environment variable to toggle HITL system
# Default to True - set USE_HITL_SYSTEM=false to disable
USE_HITL_SYSTEM = os.environ.get("USE_HITL_SYSTEM", "true").lower() == "true"

# Environment variable to toggle intent recognition system
# Default to True - set USE_INTENT_RECOGNITION=false to disable
USE_INTENT_RECOGNITION = os.environ.get("USE_INTENT_RECOGNITION", "true").lower() == "true"

# Confidence threshold for emotion degradation
EMOTION_CONFIDENCE_THRESHOLD = 0.5

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

【不要使用表单的情况】
- 用户正在寻求帮助解决紧急问题（如"帮我快速解决..."）
- 用户已在消息中给出明确答案（如"我要Python"、"选A"）
- 简单的是/否确认问题
"""

HITL_INSTRUCTION_DISABLED = ""


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
}


def get_intent_snippet(intent_result: Optional[IntentResult]) -> str:
    """Get the appropriate prompt snippet for an intent.

    Args:
        intent_result: Result from intent recognition

    Returns:
        Intent-specific prompt snippet, or empty string if no match
    """
    if not intent_result or intent_result.is_normal():
        return ""

    intent_type = intent_result.intent_type

    if intent_result.is_memory():
        return MEMORY_INTENT_SNIPPETS.get(intent_type, "")
    elif intent_result.is_hitl():
        return HITL_INTENT_SNIPPETS.get(intent_type, "")

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
    if USE_INTENT_RECOGNITION and context.intent_result:
        intent_snippet = get_intent_snippet(context.intent_result)
        if intent_snippet:
            # Use intent-specific snippet (much smaller)
            hitl_instruction = intent_snippet
            print(f"[Intent] Using optimized prompt snippet for: {context.intent_result.intent_type}")
        elif context.intent_result.is_normal():
            # Normal conversation: minimal instructions
            hitl_instruction = ""
            print("[Intent] Using minimal prompt (normal conversation)")
        else:
            # Fallback to full instruction
            hitl_instruction = HITL_INSTRUCTION if USE_HITL_SYSTEM else HITL_INSTRUCTION_DISABLED
    else:
        # No intent recognition: use full instruction for backward compatibility
        hitl_instruction = HITL_INSTRUCTION if USE_HITL_SYSTEM else HITL_INSTRUCTION_DISABLED

    return CHAT_PROMPT_TEMPLATE.format(
        user_message=context.user_message,
        working_memory_summary=working_memory_summary,
        relevant_long_term_memory=relevant_memory_str,
        strategy_prompt=strategy_prompt,
        hitl_instruction=hitl_instruction,
    )


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
        threshold=EMOTION_CONFIDENCE_THRESHOLD,
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

def is_memory_emotion_enabled() -> bool:
    """Check if memory/emotion system is enabled.

    Returns:
        True if enabled
    """
    return USE_MEMORY_EMOTION_SYSTEM


def is_hitl_enabled() -> bool:
    """Check if HITL system is enabled.

    Returns:
        True if enabled
    """
    return USE_HITL_SYSTEM


def is_intent_recognition_enabled() -> bool:
    """Check if intent recognition system is enabled.

    Returns:
        True if enabled
    """
    return USE_INTENT_RECOGNITION


def run_intent_recognition(message: str) -> Optional[IntentResult]:
    """Run Layer 1 intent recognition synchronously.

    This is a synchronous wrapper that only uses Layer 1 (rule-based matching).
    For Layer 2 (LLM-based), use the async recognize_intent_async function.

    Args:
        message: User message to analyze

    Returns:
        IntentResult if matched, None otherwise (will be normal conversation)
    """
    if not USE_INTENT_RECOGNITION:
        print("[Intent] Intent recognition disabled")
        return None

    from intent_recognizer import RuleBasedMatcher

    matcher = RuleBasedMatcher()
    result = matcher.match(message)

    if result:
        return result

    # Layer 1 didn't match, return normal intent
    # Layer 2 would require async, handled separately if needed
    print("[Intent] Layer1: no match, returning normal intent")
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
    if not USE_INTENT_RECOGNITION:
        print("[Intent] Intent recognition disabled")
        return IntentResult.normal()

    from intent_recognizer import recognize_intent

    return await recognize_intent(
        message=message,
        llm_client=llm_client,
        api_base=api_base,
        api_key=api_key,
        model=model,
        layer2_enabled=layer2_enabled,
        layer2_threshold=layer2_threshold,
    )


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


# ============ HITL Continuation ============

HITL_CONTINUATION_PROMPT_TEMPLATE = """你是一个友好的 AI 助手。

{hitl_context}

上下文信息:
- 工作记忆: {working_memory_summary}
- 相关记忆: {relevant_long_term_memory}

回复要求:
{strategy_prompt}

你必须以纯 JSON 格式回复，不要包含任何其他文字或 markdown 标记。JSON 格式如下:
{{"emotion":{{"primary":"neutral","category":"neutral","confidence":0.8,"indicators":[]}},"response":"你的回复内容","memory_update":{{"should_store":false,"entries":[]}}}}

emotion.primary 可选值: neutral, happy, excited, grateful, curious, sad, anxious, frustrated, confused, help_seeking, info_seeking, validation_seeking
emotion.category 可选值: neutral, positive, negative, seeking

重要：如果用户表达了偏好、个人信息或重要事实，必须在 memory_update 中保存。
- should_store 设为 true
- entries 中添加条目，key 和 value 必须使用中文
- category 可选: preference(偏好), fact(事实), pattern(习惯)

{hitl_instruction}

【特别提醒】这是表单提交后的后续对话。如果你想继续向用户提问或了解更多信息，请继续使用 hitl_request 表单！不要用纯文本提问。

现在请直接输出 JSON:"""


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

    # Include HITL instruction if enabled
    hitl_instruction = HITL_INSTRUCTION if USE_HITL_SYSTEM else HITL_INSTRUCTION_DISABLED

    return HITL_CONTINUATION_PROMPT_TEMPLATE.format(
        hitl_context=hitl_context,
        working_memory_summary=working_memory_summary,
        relevant_long_term_memory=relevant_memory_str,
        strategy_prompt=strategy_prompt,
        hitl_instruction=hitl_instruction,
    )
