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
USE_MEMORY_EMOTION_SYSTEM = os.environ.get("USE_MEMORY_EMOTION_SYSTEM", "true").lower() == "true"

# Confidence threshold for emotion degradation
EMOTION_CONFIDENCE_THRESHOLD = 0.5


# ============ Prompt Templates ============

CHAT_PROMPT_TEMPLATE = """你是一个 AI 助手。请严格按照以下格式输出 JSON 响应。

## 输入信息
- 用户消息: {user_message}
- 工作记忆: {working_memory_summary}
- 相关长期记忆: {relevant_long_term_memory}

## 任务 1: 情绪识别
分析用户消息的情绪状态。可选的情绪类型包括:
- neutral (无明显情绪)
- happy, excited, grateful, curious (积极情绪)
- sad, anxious, frustrated, confused (消极情绪)
- help_seeking, info_seeking, validation_seeking (寻求型)

## 任务 2: 生成回复
按照以下策略参数生成回复：
{strategy_prompt}

## 任务 3: 记忆更新 (可选)
如果用户明确表达了偏好、重要事实或习惯模式，建议存储到长期记忆。

## 输出格式 (严格 JSON)
```json
{{
  "emotion": {{
    "primary": "<emotion_type>",
    "category": "<positive|negative|neutral|seeking>",
    "confidence": <0.0-1.0>,
    "indicators": ["<indicator1>", "<indicator2>"]
  }},
  "response": "<your response text>",
  "memory_update": {{
    "should_store": <true|false>,
    "entries": [
      {{
        "category": "<preference|fact|pattern>",
        "key": "<memory_key>",
        "value": "<memory_value>"
      }}
    ]
  }}
}}
```

重要: 只输出 JSON，不要有其他内容。response 字段中直接写回复文本。"""


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
    # Get or create working memory
    working_memory = memory_manager.get_or_create_working_memory(session_id)

    # Retrieve relevant long-term memories
    relevant_memories = memory_manager.retrieve_relevant_memories(
        user_message,
        working_memory=working_memory,
    )

    # Get previous emotion for strategy selection
    previous_emotion = working_memory.last_emotion

    # Select strategy based on previous emotion (two-phase strategy)
    if previous_emotion:
        from emotion_detector import EmotionResult
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

    return CHAT_PROMPT_TEMPLATE.format(
        user_message=context.user_message,
        working_memory_summary=working_memory_summary,
        relevant_long_term_memory=relevant_memory_str,
        strategy_prompt=strategy_prompt,
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
        except Exception as e:
            # Log but don't fail on memory storage errors
            import logging
            logging.warning(f"Failed to store memory: {e}")

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
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "请根据上述信息生成 JSON 格式的响应。"},
    ]


# ============ Utility Functions ============

def is_memory_emotion_enabled() -> bool:
    """Check if memory/emotion system is enabled.

    Returns:
        True if enabled
    """
    return USE_MEMORY_EMOTION_SYSTEM


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
