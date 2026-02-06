"""Response Strategy Engine

Provides deterministic emotion-to-strategy mapping.
Strategies control response tone, length, and behavior parameters.
No LLM involvement in strategy selection - purely rule-based.
"""

from dataclasses import dataclass
from typing import Dict, Optional

from emotion_detector import EmotionResult, EmotionCategory


# ============ Strategy Data Class ============

@dataclass
class ResponseStrategy:
    """Response generation strategy parameters."""
    tone: str  # Tone instruction for prompt
    max_length: int  # Target response length in characters
    use_memory: bool  # Whether to reference long-term memory
    proactive_question: bool  # Whether to ask follow-up questions
    formality: str = "casual"  # casual | formal
    emoji_allowed: bool = False  # Whether emojis are allowed

    def to_prompt_params(self) -> Dict[str, str]:
        """Convert strategy to prompt template parameters.

        Returns:
            Dictionary of prompt parameters
        """
        return {
            "tone": self.tone,
            "max_length": str(self.max_length),
            "use_memory": "是" if self.use_memory else "否",
            "proactive_question": "是" if self.proactive_question else "否",
            "formality": "正式" if self.formality == "formal" else "轻松随意",
            "emoji_allowed": "可以" if self.emoji_allowed else "不要",
        }


# ============ Emotion-Strategy Mapping ============

# Default strategy for unknown emotions
DEFAULT_STRATEGY = ResponseStrategy(
    tone="professional",
    max_length=300,
    use_memory=True,
    proactive_question=False,
    formality="casual",
    emoji_allowed=False,
)

# Complete emotion-strategy mapping table
EMOTION_STRATEGY_MAP: Dict[str, ResponseStrategy] = {
    # Neutral - Professional and balanced
    "neutral": ResponseStrategy(
        tone="professional",
        max_length=300,
        use_memory=True,
        proactive_question=False,
        formality="casual",
        emoji_allowed=False,
    ),

    # Positive emotions
    "happy": ResponseStrategy(
        tone="warm",
        max_length=250,
        use_memory=True,
        proactive_question=True,
        formality="casual",
        emoji_allowed=True,
    ),
    "excited": ResponseStrategy(
        tone="enthusiastic",
        max_length=300,
        use_memory=True,
        proactive_question=True,
        formality="casual",
        emoji_allowed=True,
    ),
    "grateful": ResponseStrategy(
        tone="warm_appreciative",
        max_length=200,
        use_memory=True,
        proactive_question=False,
        formality="casual",
        emoji_allowed=True,
    ),
    "curious": ResponseStrategy(
        tone="informative_engaging",
        max_length=400,
        use_memory=True,
        proactive_question=True,
        formality="casual",
        emoji_allowed=True,
    ),

    # Negative emotions
    "sad": ResponseStrategy(
        tone="empathetic",
        max_length=400,
        use_memory=True,
        proactive_question=False,  # Don't pester with questions
        formality="casual",
        emoji_allowed=False,
    ),
    "anxious": ResponseStrategy(
        tone="calm_reassuring",
        max_length=350,
        use_memory=True,
        proactive_question=False,  # Reduce pressure
        formality="casual",
        emoji_allowed=False,
    ),
    "frustrated": ResponseStrategy(
        tone="patient_understanding",
        max_length=400,
        use_memory=True,
        proactive_question=False,  # Don't add to frustration
        formality="casual",
        emoji_allowed=False,
    ),
    "confused": ResponseStrategy(
        tone="clear_explanatory",
        max_length=500,
        use_memory=True,
        proactive_question=True,  # Offer clarification
        formality="casual",
        emoji_allowed=False,
    ),

    # Seeking emotions
    "help_seeking": ResponseStrategy(
        tone="helpful",
        max_length=600,
        use_memory=True,
        proactive_question=True,  # Gather more info to help
        formality="casual",
        emoji_allowed=True,
    ),
    "info_seeking": ResponseStrategy(
        tone="informative",
        max_length=500,
        use_memory=True,
        proactive_question=True,  # Offer related info
        formality="casual",
        emoji_allowed=True,
    ),
    "validation_seeking": ResponseStrategy(
        tone="supportive_affirming",
        max_length=300,
        use_memory=True,
        proactive_question=False,  # Focus on validation
        formality="casual",
        emoji_allowed=True,
    ),
}

# Tone description map for prompt injection
TONE_DESCRIPTIONS: Dict[str, str] = {
    "professional": "专业、客观、简洁",
    "warm": "温暖、友好、亲切",
    "enthusiastic": "热情、积极、充满活力",
    "warm_appreciative": "温暖、感激、真诚",
    "informative_engaging": "信息丰富、引人入胜、有见地",
    "empathetic": "共情、理解、支持性的",
    "calm_reassuring": "平静、安抚、令人放心的",
    "patient_understanding": "耐心、理解、不评判的",
    "clear_explanatory": "清晰、解释性强、条理分明",
    "helpful": "乐于助人、积极主动、解决问题导向",
    "informative": "信息丰富、准确、全面",
    "supportive_affirming": "支持性的、肯定的、鼓励的",
}


# ============ Strategy Selection ============

def select_strategy(emotion: EmotionResult) -> ResponseStrategy:
    """Select response strategy based on detected emotion.

    This is a purely deterministic function - same emotion always
    produces the same strategy.

    Args:
        emotion: Detected emotion result

    Returns:
        ResponseStrategy for the emotion
    """
    strategy = EMOTION_STRATEGY_MAP.get(emotion.primary)

    if strategy is None:
        # Unknown emotion, use default
        return DEFAULT_STRATEGY

    return strategy


def get_strategy_for_emotion(emotion_type: str) -> ResponseStrategy:
    """Get strategy for a specific emotion type string.

    Args:
        emotion_type: Emotion type string (e.g., "happy", "sad")

    Returns:
        ResponseStrategy for the emotion
    """
    return EMOTION_STRATEGY_MAP.get(emotion_type, DEFAULT_STRATEGY)


def get_tone_description(tone: str) -> str:
    """Get Chinese description for a tone.

    Args:
        tone: Tone key (e.g., "professional", "warm")

    Returns:
        Chinese description of the tone
    """
    return TONE_DESCRIPTIONS.get(tone, "专业、友好")


def build_strategy_prompt(strategy: ResponseStrategy) -> str:
    """Build prompt segment describing response strategy.

    Args:
        strategy: ResponseStrategy to convert

    Returns:
        Prompt text describing strategy constraints
    """
    tone_desc = get_tone_description(strategy.tone)

    parts = [
        f"- 语气: {tone_desc}",
        f"- 目标长度: 约 {strategy.max_length} 字符",
        f"- 是否可以引用之前的记忆: {'是' if strategy.use_memory else '否'}",
        f"- 是否主动追问: {'是' if strategy.proactive_question else '否'}",
        f"- 风格: {'正式' if strategy.formality == 'formal' else '轻松随意'}",
    ]

    if strategy.emoji_allowed:
        parts.append("- 可以适当使用表情符号")
    else:
        parts.append("- 不要使用表情符号")

    return "\n".join(parts)


def get_all_strategies() -> Dict[str, ResponseStrategy]:
    """Get all available emotion-strategy mappings.

    Returns:
        Complete mapping dictionary
    """
    return EMOTION_STRATEGY_MAP.copy()


def validate_strategy_completeness() -> bool:
    """Validate that all defined emotion types have strategies.

    Returns:
        True if all emotion types have corresponding strategies
    """
    from emotion_detector import EmotionType

    missing = []
    for emotion_type in EmotionType:
        if emotion_type.value not in EMOTION_STRATEGY_MAP:
            missing.append(emotion_type.value)

    if missing:
        import logging
        logging.warning(f"Missing strategies for emotions: {missing}")
        return False

    return True
