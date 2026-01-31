"""Intent Recognition Rules

Defines regex and keyword rules for Layer 1 rule-based intent matching.
Rules are organized by intent type for easy maintenance and extension.
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional, Pattern


@dataclass
class IntentRule:
    """A single intent matching rule.

    Attributes:
        name: Rule identifier for logging
        pattern: Compiled regex pattern
        intent_type: The intent type this rule matches
        priority: Higher priority rules are checked first (default 0)
        mcp_service_name: For MCP rules, the associated service name
    """
    name: str
    pattern: Pattern
    intent_type: str
    priority: int = 0
    mcp_service_name: Optional[str] = None  # For MCP intent rules


def _compile_patterns(patterns: List[str]) -> Pattern:
    """Compile multiple patterns into a single regex with OR."""
    combined = "|".join(f"({p})" for p in patterns)
    return re.compile(combined, re.IGNORECASE)


# ============ Memory Intent Rules (4 types) ============

MEMORY_RULES: List[IntentRule] = [
    # Preference - 用户偏好
    IntentRule(
        name="preference_like",
        pattern=_compile_patterns([
            r"我喜欢",
            r"我偏好",
            r"我爱",
            r"我更喜欢",
            r"我比较喜欢",
            r"我最喜欢",
            r"我不喜欢",
            r"我讨厌",
            r"我不爱",
            r"我倾向于",
            r"我选择",
            r"我宁愿",
        ]),
        intent_type="preference",
        priority=10,
    ),

    # Fact - 用户事实
    IntentRule(
        name="fact_identity",
        pattern=_compile_patterns([
            r"我叫",
            r"我是",
            r"我的名字是",
            r"我在.+工作",
            r"我在.+上班",
            r"我住在",
            r"我来自",
            r"我今年.+岁",
            r"我的职业是",
            r"我做.+的",
            r"我会.+语言",
            r"我学过",
            r"我毕业于",
        ]),
        intent_type="fact",
        priority=10,
    ),

    # Pattern - 行为模式
    IntentRule(
        name="pattern_habit",
        pattern=_compile_patterns([
            r"我每天",
            r"我通常",
            r"我习惯",
            r"我一般",
            r"我经常",
            r"我总是",
            r"我每周",
            r"我每个月",
            r"我平时",
            r"我的习惯是",
        ]),
        intent_type="pattern",
        priority=10,
    ),

    # Opinion - 个人观点
    IntentRule(
        name="opinion_think",
        pattern=_compile_patterns([
            r"我认为",
            r"我觉得",
            r"我相信",
            r"我发现",
            r"在我看来",
            r"我的观点是",
            r"我认同",
            r"我不认同",
            r"我的看法是",
            r"依我之见",
            r"我个人认为",
            r"我的理解是",
        ]),
        intent_type="opinion",
        priority=10,
    ),
]


# ============ HITL Intent Rules (6 strategies) ============

HITL_RULES: List[IntentRule] = [
    # Plan Reminder - 计划提醒 (highest priority for time-related)
    IntentRule(
        name="plan_time_keyword",
        pattern=_compile_patterns([
            r"提醒我",
            r"别忘了",
            r"记得.+要",
            r"明天.+[要会]",
            r"后天.+[要会]",
            r"下周.+[要会]",
            r"下个?月.+[要会]",
            r"\d+点.+[要会开]",
            r"\d+[日号].+[要会]",
            r"周[一二三四五六日天].+[要会]",
            r"每天.+提醒",
            r"每周.+提醒",
            r"定时",
            r"预约",
            r"安排.+会议",
            r"开会.+[时间点]",
        ]),
        intent_type="plan_reminder",
        priority=20,  # High priority for time-sensitive intents
    ),

    # Proactive Inquiry - 主动询问 (greetings)
    IntentRule(
        name="greeting",
        pattern=_compile_patterns([
            r"^你好[啊呀]?$",
            r"^嗨[呀]?$",
            r"^hi[!]?$",
            r"^hello[!]?$",
            r"^hey[!]?$",
            r"^早[上]?好$",
            r"^晚上好$",
            r"^下午好$",
            r"^在吗[?？]?$",
            r"^有人吗[?？]?$",
        ]),
        intent_type="proactive_inquiry",
        priority=15,
    ),

    # Emotion Driven - 情感驱动
    IntentRule(
        name="emotion_positive",
        pattern=_compile_patterns([
            r"心情很好",
            r"很开心",
            r"很高兴",
            r"太棒了",
            r"好兴奋",
            r"真不错",
            r"感觉很好",
            r"超级开心",
        ]),
        intent_type="emotion_driven",
        priority=10,
    ),
    IntentRule(
        name="emotion_negative",
        pattern=_compile_patterns([
            r"很难过",
            r"心情不好",
            r"很沮丧",
            r"很烦",
            r"好累",
            r"压力很大",
            r"很焦虑",
            r"很担心",
            r"不开心",
            r"郁闷",
        ]),
        intent_type="emotion_driven",
        priority=10,
    ),

    # Memory Gap - 记忆补全 (recommendation requests)
    IntentRule(
        name="recommendation_request",
        pattern=_compile_patterns([
            r"推荐.+[书电影音乐餐厅]",
            r"建议.+[什么哪]",
            r"帮我推荐",
            r"有什么.+推荐",
            r"想找.+[书电影音乐]",
            r"求推荐",
        ]),
        intent_type="memory_gap",
        priority=10,
    ),

    # Topic Deepening - 话题深化
    IntentRule(
        name="topic_interest",
        pattern=_compile_patterns([
            r"我对.+感兴趣",
            r"我想了解.+更多",
            r"最近在[学看玩]",
            r"我正在[学研究]",
            r"我迷上了",
        ]),
        intent_type="topic_deepening",
        priority=5,
    ),

    # Question to Form - 问答转表单
    IntentRule(
        name="structured_question",
        pattern=_compile_patterns([
            r"想去.+旅[游行]",
            r"打算.+[买去做]",
            r"计划.+[买去做]",
            r"想[买换]",
            r"考虑.+[买换]",
        ]),
        intent_type="question_to_form",
        priority=5,
    ),

    # Visual Display - 图形化展示
    IntentRule(
        name="visual_compare",
        pattern=_compile_patterns([
            r"比较.+和",
            r"对比.+和",
            r"对比一下",
            r"比较一下",
            r".+和.+有什么区别",
            r".+和.+哪个好",
            r".+vs\.?.+",
            r".+versus.+",
            r".+跟.+比",
            r".+与.+对比",
        ]),
        intent_type="visual_display",
        priority=15,
    ),
    IntentRule(
        name="visual_list",
        pattern=_compile_patterns([
            r"列出.+",
            r"列一下",
            r"列举",
            r"汇总.+",
            r"整理.+清单",
            r"整理.+列表",
            r"给我一个.+列表",
            r"给我一个.+清单",
            r"常用的.+命令",
            r"常用的.+快捷键",
        ]),
        intent_type="visual_display",
        priority=15,
    ),
    IntentRule(
        name="visual_table",
        pattern=_compile_patterns([
            r"用表格",
            r"以表格",
            r"表格形式",
            r"做个表",
            r"画个表",
            r"整理成表",
        ]),
        intent_type="visual_display",
        priority=18,  # Higher priority when explicitly requesting table
    ),
    IntentRule(
        name="visual_diagram",
        pattern=_compile_patterns([
            r"流程图",
            r"架构图",
            r"示意图",
            r"画一个.+图",
            r"展示.+结构",
            r"画个.+流程",
            r"用图.+展示",
        ]),
        intent_type="visual_display",
        priority=18,
    ),
]


# ============ MCP Intent Rules ============

MCP_RULES: List[IntentRule] = [
    # Explicit tool call patterns
    IntentRule(
        name="mcp_explicit_tool",
        pattern=_compile_patterns([
            r"用.+工具",
            r"使用.+工具",
            r"调用.+工具",
            r"运行.+工具",
            r"执行.+工具",
        ]),
        intent_type="mcp_tool_call",
        priority=25,  # High priority for explicit tool calls
    ),
    IntentRule(
        name="mcp_explicit_service",
        pattern=_compile_patterns([
            r"用.+服务",
            r"使用.+服务",
            r"调用.+服务",
            r"让.+服务",
        ]),
        intent_type="mcp_tool_call",
        priority=25,
    ),
]


def create_mcp_keyword_rule(service_name: str, keywords: List[str]) -> Optional[IntentRule]:
    """Create an MCP rule from service trigger keywords.

    Args:
        service_name: Name of the MCP service
        keywords: List of trigger keywords

    Returns:
        IntentRule if keywords provided, None otherwise
    """
    if not keywords:
        return None

    # Escape special regex characters in keywords
    escaped_keywords = [re.escape(kw) for kw in keywords]

    return IntentRule(
        name=f"mcp_keyword_{service_name}",
        pattern=_compile_patterns(escaped_keywords),
        intent_type="mcp_tool_call",
        priority=20,  # Medium-high priority for keyword matches
        mcp_service_name=service_name,
    )


# ============ Combined Rules ============

def get_all_rules(include_mcp: bool = True) -> List[IntentRule]:
    """Get all intent rules sorted by priority (highest first).

    Args:
        include_mcp: Whether to include static MCP rules (default True)

    Returns:
        List of IntentRule sorted by priority
    """
    all_rules = MEMORY_RULES + HITL_RULES
    if include_mcp:
        all_rules = all_rules + MCP_RULES
    return sorted(all_rules, key=lambda r: r.priority, reverse=True)


def get_memory_rules() -> List[IntentRule]:
    """Get only memory-related rules."""
    return sorted(MEMORY_RULES, key=lambda r: r.priority, reverse=True)


def get_hitl_rules() -> List[IntentRule]:
    """Get only HITL-related rules."""
    return sorted(HITL_RULES, key=lambda r: r.priority, reverse=True)


def get_mcp_rules() -> List[IntentRule]:
    """Get only MCP-related rules (static rules only)."""
    return sorted(MCP_RULES, key=lambda r: r.priority, reverse=True)


def get_all_rules_with_dynamic_mcp(mcp_keyword_rules: List[IntentRule]) -> List[IntentRule]:
    """Get all rules including dynamic MCP keyword rules.

    Args:
        mcp_keyword_rules: Additional rules created from MCP service configurations

    Returns:
        List of IntentRule sorted by priority
    """
    all_rules = MEMORY_RULES + HITL_RULES + MCP_RULES + mcp_keyword_rules
    return sorted(all_rules, key=lambda r: r.priority, reverse=True)
