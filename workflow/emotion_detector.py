"""Emotion Detection Module

Provides structured emotion recognition from LLM output.
Parses emotion JSON from LLM responses and validates against defined schema.
"""

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ============ Emotion Types ============

class EmotionCategory(str, Enum):
    """High-level emotion categories."""
    NEUTRAL = "neutral"
    POSITIVE = "positive"
    NEGATIVE = "negative"
    SEEKING = "seeking"


class EmotionType(str, Enum):
    """Specific emotion types."""
    # Neutral
    NEUTRAL = "neutral"

    # Positive emotions
    HAPPY = "happy"
    EXCITED = "excited"
    GRATEFUL = "grateful"
    CURIOUS = "curious"

    # Negative emotions
    SAD = "sad"
    ANXIOUS = "anxious"
    FRUSTRATED = "frustrated"
    CONFUSED = "confused"

    # Seeking emotions
    HELP_SEEKING = "help_seeking"
    INFO_SEEKING = "info_seeking"
    VALIDATION_SEEKING = "validation_seeking"


# Mapping from emotion type to category
EMOTION_CATEGORY_MAP: Dict[str, EmotionCategory] = {
    # Neutral
    "neutral": EmotionCategory.NEUTRAL,

    # Positive
    "happy": EmotionCategory.POSITIVE,
    "excited": EmotionCategory.POSITIVE,
    "grateful": EmotionCategory.POSITIVE,
    "curious": EmotionCategory.POSITIVE,

    # Negative
    "sad": EmotionCategory.NEGATIVE,
    "anxious": EmotionCategory.NEGATIVE,
    "frustrated": EmotionCategory.NEGATIVE,
    "confused": EmotionCategory.NEGATIVE,

    # Seeking
    "help_seeking": EmotionCategory.SEEKING,
    "info_seeking": EmotionCategory.SEEKING,
    "validation_seeking": EmotionCategory.SEEKING,
}


# ============ Data Classes ============

@dataclass
class EmotionResult:
    """Parsed emotion detection result."""
    primary: str = "neutral"
    category: str = "neutral"
    confidence: float = 0.5
    indicators: List[str] = field(default_factory=list)
    raw_data: Optional[Dict[str, Any]] = None

    def is_valid(self) -> bool:
        """Check if emotion result is valid."""
        return self.primary in EMOTION_CATEGORY_MAP

    def is_low_confidence(self, threshold: float = 0.5) -> bool:
        """Check if confidence is below threshold."""
        return self.confidence < threshold


@dataclass
class MemoryUpdateSuggestion:
    """LLM's suggestion for memory updates."""
    should_store: bool = False
    entries: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class LLMOutputResult:
    """Complete parsed result from LLM output."""
    emotion: EmotionResult
    response: str
    memory_update: MemoryUpdateSuggestion
    raw_output: Optional[str] = None
    parse_error: Optional[str] = None


# ============ Parsing Functions ============

def parse_emotion_from_dict(data: Dict[str, Any]) -> EmotionResult:
    """Parse emotion result from dictionary.

    Args:
        data: Emotion data dictionary

    Returns:
        EmotionResult instance
    """
    primary = data.get("primary", "neutral")
    category = data.get("category", "neutral")
    confidence = data.get("confidence", 0.5)
    indicators = data.get("indicators", [])

    # Validate and normalize primary emotion
    if primary not in EMOTION_CATEGORY_MAP:
        logger.warning(f"Unknown emotion type: {primary}, falling back to neutral")
        primary = "neutral"
        category = "neutral"
        confidence = 0.5

    # Ensure category matches primary if not provided correctly
    if category not in [e.value for e in EmotionCategory]:
        category = EMOTION_CATEGORY_MAP.get(primary, EmotionCategory.NEUTRAL).value

    # Clamp confidence to valid range
    confidence = max(0.0, min(1.0, float(confidence)))

    # Ensure indicators is a list
    if not isinstance(indicators, list):
        indicators = []

    return EmotionResult(
        primary=primary,
        category=category,
        confidence=confidence,
        indicators=indicators,
        raw_data=data,
    )


def parse_memory_update_from_dict(data: Dict[str, Any]) -> MemoryUpdateSuggestion:
    """Parse memory update suggestion from dictionary.

    Args:
        data: Memory update data dictionary

    Returns:
        MemoryUpdateSuggestion instance
    """
    should_store = data.get("should_store", False)
    entries = data.get("entries", [])

    # Validate entries
    valid_entries = []
    for entry in entries:
        if isinstance(entry, dict) and "key" in entry and "value" in entry:
            valid_entries.append({
                "category": entry.get("category", "fact"),
                "key": entry["key"],
                "value": entry["value"],
            })

    return MemoryUpdateSuggestion(
        should_store=bool(should_store),
        entries=valid_entries,
    )


def parse_llm_output(json_str: str) -> LLMOutputResult:
    """Parse complete LLM output JSON.

    Expected format:
    {
        "emotion": {
            "primary": "curious",
            "category": "positive",
            "confidence": 0.85,
            "indicators": ["question mark", "exploratory language"]
        },
        "response": "Your response text here",
        "memory_update": {
            "should_store": true,
            "entries": [
                {"category": "preference", "key": "language", "value": "Python"}
            ]
        }
    }

    Args:
        json_str: Raw JSON string from LLM

    Returns:
        LLMOutputResult instance
    """
    # Default result for fallback
    default_emotion = EmotionResult()
    default_memory_update = MemoryUpdateSuggestion()

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse LLM output as JSON: {e}")
        return LLMOutputResult(
            emotion=default_emotion,
            response=json_str,  # Use raw output as response
            memory_update=default_memory_update,
            raw_output=json_str,
            parse_error=f"JSON parse error: {str(e)}",
        )

    # Parse emotion
    emotion_data = data.get("emotion", {})
    if isinstance(emotion_data, dict):
        emotion = parse_emotion_from_dict(emotion_data)
    else:
        emotion = default_emotion

    # Parse response
    response = data.get("response", "")
    if not isinstance(response, str):
        response = str(response)

    # Parse memory update
    memory_data = data.get("memory_update", {})
    if isinstance(memory_data, dict):
        memory_update = parse_memory_update_from_dict(memory_data)
    else:
        memory_update = default_memory_update

    return LLMOutputResult(
        emotion=emotion,
        response=response,
        memory_update=memory_update,
        raw_output=json_str,
    )


def apply_confidence_threshold(
    emotion: EmotionResult,
    threshold: float = 0.5,
    fallback_emotion: str = "neutral",
) -> EmotionResult:
    """Apply confidence threshold, degrading to fallback if below threshold.

    Args:
        emotion: Original emotion result
        threshold: Confidence threshold (default 0.5)
        fallback_emotion: Emotion to use if below threshold

    Returns:
        EmotionResult, possibly degraded to fallback
    """
    if emotion.confidence < threshold:
        logger.info(
            f"Emotion confidence {emotion.confidence} below threshold {threshold}, "
            f"degrading from {emotion.primary} to {fallback_emotion}"
        )
        return EmotionResult(
            primary=fallback_emotion,
            category=EMOTION_CATEGORY_MAP.get(fallback_emotion, EmotionCategory.NEUTRAL).value,
            confidence=emotion.confidence,
            indicators=emotion.indicators + [f"degraded_from_{emotion.primary}"],
            raw_data=emotion.raw_data,
        )

    return emotion


def extract_emotion_from_text(text: str) -> EmotionResult:
    """Try to extract emotion from unstructured text.

    Simple heuristic-based extraction as fallback when JSON parsing fails.

    Args:
        text: Raw text to analyze

    Returns:
        EmotionResult based on keyword matching
    """
    text_lower = text.lower()

    # Simple keyword-based detection
    emotion_keywords = {
        "happy": ["happy", "glad", "joy", "excited", "great", "wonderful", "开心", "高兴", "快乐"],
        "sad": ["sad", "unhappy", "disappointed", "upset", "难过", "伤心", "失望"],
        "anxious": ["worried", "anxious", "nervous", "stressed", "担心", "焦虑", "紧张"],
        "confused": ["confused", "don't understand", "unclear", "困惑", "不明白", "搞不懂"],
        "curious": ["curious", "wondering", "interested", "好奇", "想知道", "感兴趣"],
        "frustrated": ["frustrated", "annoyed", "irritated", "沮丧", "烦躁"],
        "grateful": ["thank", "grateful", "appreciate", "谢谢", "感谢", "感激"],
        "help_seeking": ["help", "how do", "how to", "can you", "帮助", "怎么", "如何"],
        "info_seeking": ["what is", "what's", "tell me", "explain", "是什么", "告诉我", "解释"],
    }

    detected_emotions = []
    for emotion, keywords in emotion_keywords.items():
        if any(kw in text_lower for kw in keywords):
            detected_emotions.append(emotion)

    if detected_emotions:
        primary = detected_emotions[0]
        return EmotionResult(
            primary=primary,
            category=EMOTION_CATEGORY_MAP.get(primary, EmotionCategory.NEUTRAL).value,
            confidence=0.3,  # Low confidence for heuristic detection
            indicators=detected_emotions,
        )

    return EmotionResult(
        primary="neutral",
        category="neutral",
        confidence=0.5,
        indicators=["no_keywords_matched"],
    )
