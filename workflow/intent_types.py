"""Intent Type Definitions

Defines intent types and result structures for multi-layer intent recognition.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class MemoryIntent(Enum):
    """Memory-related intent types mapping to 4 memory save rules."""
    PREFERENCE = "preference"      # 用户偏好 - 喜欢/不喜欢的事物
    FACT = "fact"                  # 用户事实 - 个人信息、技能、状态
    PATTERN = "pattern"            # 行为模式 - 习惯、重复需求
    OPINION = "opinion"            # 个人观点 - 看法、认为、觉得


class HITLIntent(Enum):
    """HITL form trigger intent types mapping to 7 HITL strategies."""
    PROACTIVE_INQUIRY = "proactive_inquiry"   # 主动询问 - 问候、初次对话
    TOPIC_DEEPENING = "topic_deepening"       # 话题深化 - 模糊喜好、领域提及
    EMOTION_DRIVEN = "emotion_driven"         # 情感驱动 - 情绪表达
    MEMORY_GAP = "memory_gap"                 # 记忆补全 - 推荐、建议请求
    QUESTION_TO_FORM = "question_to_form"     # 问答转表单 - 可结构化问题
    PLAN_REMINDER = "plan_reminder"           # 计划提醒 - 时间相关计划
    VISUAL_DISPLAY = "visual_display"         # 图形化展示 - 比较、对比、列表、流程图


class MCPIntent(Enum):
    """MCP tool call intent types."""
    TOOL_CALL = "mcp_tool_call"  # 工具调用 - 用户请求使用某个工具


class IntentCategory(Enum):
    """Top-level intent categories."""
    MEMORY = "memory"      # Triggers memory save rules
    HITL = "hitl"          # Triggers HITL form strategies
    MCP = "mcp"            # Triggers MCP tool calls
    NORMAL = "normal"      # Normal conversation, no special handling


@dataclass
class IntentResult:
    """Result from intent recognition.

    Attributes:
        category: Top-level category (memory, hitl, mcp, or normal)
        intent_type: Specific intent (MemoryIntent, HITLIntent, or MCPIntent value)
        confidence: Confidence score (0.0-1.0)
        matched_rule: Name of the rule that matched (for Layer 1)
        source: Which layer produced this result ("layer1", "layer2", "fallback")
        mcp_service_name: Name of the MCP service for MCP intents
    """
    category: IntentCategory
    intent_type: Optional[str] = None
    confidence: float = 0.0
    matched_rule: Optional[str] = None
    source: str = "fallback"
    mcp_service_name: Optional[str] = None  # For MCP intents: which service to call

    @classmethod
    def memory(cls, intent: MemoryIntent, confidence: float = 1.0,
               matched_rule: Optional[str] = None, source: str = "layer1") -> "IntentResult":
        """Create a memory intent result."""
        return cls(
            category=IntentCategory.MEMORY,
            intent_type=intent.value,
            confidence=confidence,
            matched_rule=matched_rule,
            source=source,
        )

    @classmethod
    def hitl(cls, intent: HITLIntent, confidence: float = 1.0,
             matched_rule: Optional[str] = None, source: str = "layer1") -> "IntentResult":
        """Create a HITL intent result."""
        return cls(
            category=IntentCategory.HITL,
            intent_type=intent.value,
            confidence=confidence,
            matched_rule=matched_rule,
            source=source,
        )

    @classmethod
    def mcp(cls, service_name: Optional[str] = None, confidence: float = 1.0,
            matched_rule: Optional[str] = None, source: str = "layer1") -> "IntentResult":
        """Create an MCP tool call intent result."""
        return cls(
            category=IntentCategory.MCP,
            intent_type=MCPIntent.TOOL_CALL.value,
            confidence=confidence,
            matched_rule=matched_rule,
            source=source,
            mcp_service_name=service_name,
        )

    @classmethod
    def normal(cls) -> "IntentResult":
        """Create a normal conversation result (no special intent)."""
        return cls(
            category=IntentCategory.NORMAL,
            intent_type=None,
            confidence=1.0,
            matched_rule=None,
            source="fallback",
        )

    def is_memory(self) -> bool:
        """Check if this is a memory intent."""
        return self.category == IntentCategory.MEMORY

    def is_hitl(self) -> bool:
        """Check if this is a HITL intent."""
        return self.category == IntentCategory.HITL

    def is_mcp(self) -> bool:
        """Check if this is an MCP tool call intent."""
        return self.category == IntentCategory.MCP

    def is_normal(self) -> bool:
        """Check if this is normal conversation."""
        return self.category == IntentCategory.NORMAL


# Intent type string to enum mapping for parsing
MEMORY_INTENT_MAP = {intent.value: intent for intent in MemoryIntent}
HITL_INTENT_MAP = {intent.value: intent for intent in HITLIntent}
MCP_INTENT_MAP = {intent.value: intent for intent in MCPIntent}


def parse_intent_type(intent_str: str) -> tuple[Optional[IntentCategory], Optional[str]]:
    """Parse an intent string to category and type.

    Args:
        intent_str: Intent type string (e.g., "preference", "plan_reminder", "mcp_tool_call")

    Returns:
        Tuple of (category, intent_type) or (None, None) if not found
    """
    if intent_str in MEMORY_INTENT_MAP:
        return IntentCategory.MEMORY, intent_str
    if intent_str in HITL_INTENT_MAP:
        return IntentCategory.HITL, intent_str
    if intent_str in MCP_INTENT_MAP:
        return IntentCategory.MCP, intent_str
    return None, None
