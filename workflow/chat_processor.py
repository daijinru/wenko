"""Chat Processor Module

Handles the complete chat flow with memory and emotion system integration.
Provides prompt templates and LLM output parsing.
"""

import json
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

# Confidence threshold for emotion degradation
EMOTION_CONFIDENCE_THRESHOLD = 0.5


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

重要：如果用户表达了偏好、个人信息或重要事实，必须在 memory_update 中保存。
- should_store 设为 true
- entries 中添加条目，key 和 value 必须使用中文
- category 可选: preference(偏好), fact(事实), pattern(习惯)

示例：用户说"我叫小明，喜欢用Python"，应保存:
{{"should_store":true,"entries":[{{"category":"fact","key":"用户姓名","value":"小明"}},{{"category":"preference","key":"编程语言偏好","value":"Python"}}]}}

{hitl_instruction}

现在请直接输出 JSON:"""


# ============ HITL Instruction Template ============

HITL_INSTRUCTION = """
人机交互表单 (HITL):
当你需要向用户收集结构化信息或确认操作时，可以在 JSON 响应中包含 hitl_request 字段。

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

示例：询问用户喜欢的运动
{{"response":"让我了解一下您的运动偏好","hitl_request":{{"type":"form","title":"运动偏好","fields":[{{"name":"sport","type":"select","label":"您最喜欢的运动","required":true,"options":[{{"value":"basketball","label":"篮球"}},{{"value":"football","label":"足球"}},{{"value":"swimming","label":"游泳"}}]}}],"context":{{"intent":"collect_preference","memory_category":"preference"}}}}}}

仅在以下情况使用 hitl_request:
1. 需要收集用户偏好或个人信息，且有明确的选项
2. 执行重要操作前需要用户确认
3. 存在多个选项需要用户选择
4. 用户明确要求选择或投票

不要在以下情况使用:
1. 简单的是/否问题（直接问即可）
2. 开放性问题
3. 用户已经给出了明确答案
"""

HITL_INSTRUCTION_DISABLED = ""


SIMPLE_SYSTEM_PROMPT = """你是一个友好的 AI 助手。"""


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
        ctx_str = ", ".join(f"{k}={v}" for k, v in working_memory.context_variables.items())
        parts.append(f"上下文: {ctx_str}")

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

    Args:
        context: ChatContext with all information

    Returns:
        Complete system prompt
    """
    working_memory_summary = format_working_memory_summary(context.working_memory)
    relevant_memory_str = format_relevant_memories(context.relevant_memories)
    strategy_prompt = build_strategy_prompt(context.strategy)

    # Include HITL instruction if enabled
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
