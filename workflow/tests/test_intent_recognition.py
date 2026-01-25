"""Tests for Intent Recognition Module

Tests for:
- Layer 1: Rule-based intent matching
- Layer 2: LLM-based classification (mocked)
- Full intent recognition flow
- Integration with chat_processor
"""

import pytest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from intent_types import (
    IntentCategory,
    IntentResult,
    MemoryIntent,
    HITLIntent,
    parse_intent_type,
)
from intent_rules import (
    IntentRule,
    get_all_rules,
    get_memory_rules,
    get_hitl_rules,
)
from intent_recognizer import RuleBasedMatcher


class TestIntentTypes:
    """Tests for intent type definitions."""

    def test_memory_intent_values(self):
        """Test MemoryIntent enum values."""
        assert MemoryIntent.PREFERENCE.value == "preference"
        assert MemoryIntent.FACT.value == "fact"
        assert MemoryIntent.PATTERN.value == "pattern"
        assert MemoryIntent.OPINION.value == "opinion"

    def test_hitl_intent_values(self):
        """Test HITLIntent enum values."""
        assert HITLIntent.PROACTIVE_INQUIRY.value == "proactive_inquiry"
        assert HITLIntent.TOPIC_DEEPENING.value == "topic_deepening"
        assert HITLIntent.EMOTION_DRIVEN.value == "emotion_driven"
        assert HITLIntent.MEMORY_GAP.value == "memory_gap"
        assert HITLIntent.QUESTION_TO_FORM.value == "question_to_form"
        assert HITLIntent.PLAN_REMINDER.value == "plan_reminder"

    def test_intent_result_memory(self):
        """Test IntentResult.memory() factory method."""
        result = IntentResult.memory(MemoryIntent.PREFERENCE, confidence=0.9)
        assert result.category == IntentCategory.MEMORY
        assert result.intent_type == "preference"
        assert result.confidence == 0.9
        assert result.is_memory()
        assert not result.is_hitl()
        assert not result.is_normal()

    def test_intent_result_hitl(self):
        """Test IntentResult.hitl() factory method."""
        result = IntentResult.hitl(HITLIntent.PLAN_REMINDER, confidence=1.0)
        assert result.category == IntentCategory.HITL
        assert result.intent_type == "plan_reminder"
        assert result.confidence == 1.0
        assert result.is_hitl()
        assert not result.is_memory()
        assert not result.is_normal()

    def test_intent_result_normal(self):
        """Test IntentResult.normal() factory method."""
        result = IntentResult.normal()
        assert result.category == IntentCategory.NORMAL
        assert result.intent_type is None
        assert result.confidence == 1.0
        assert result.is_normal()
        assert not result.is_memory()
        assert not result.is_hitl()

    def test_parse_intent_type_memory(self):
        """Test parsing memory intent types."""
        category, intent_type = parse_intent_type("preference")
        assert category == IntentCategory.MEMORY
        assert intent_type == "preference"

        category, intent_type = parse_intent_type("fact")
        assert category == IntentCategory.MEMORY

    def test_parse_intent_type_hitl(self):
        """Test parsing HITL intent types."""
        category, intent_type = parse_intent_type("plan_reminder")
        assert category == IntentCategory.HITL
        assert intent_type == "plan_reminder"

    def test_parse_intent_type_unknown(self):
        """Test parsing unknown intent type."""
        category, intent_type = parse_intent_type("unknown_intent")
        assert category is None
        assert intent_type is None


class TestIntentRules:
    """Tests for intent rule definitions."""

    def test_get_all_rules(self):
        """Test getting all rules."""
        rules = get_all_rules()
        assert len(rules) > 0
        # Should be sorted by priority (highest first)
        assert rules[0].priority >= rules[-1].priority

    def test_get_memory_rules(self):
        """Test getting memory-specific rules."""
        rules = get_memory_rules()
        assert len(rules) > 0
        for rule in rules:
            assert rule.intent_type in ["preference", "fact", "pattern", "opinion"]

    def test_get_hitl_rules(self):
        """Test getting HITL-specific rules."""
        rules = get_hitl_rules()
        assert len(rules) > 0
        hitl_intents = ["proactive_inquiry", "topic_deepening", "emotion_driven",
                        "memory_gap", "question_to_form", "plan_reminder"]
        for rule in rules:
            assert rule.intent_type in hitl_intents


class TestRuleBasedMatcher:
    """Tests for Layer 1 rule-based matching."""

    def setup_method(self):
        """Set up test fixtures."""
        self.matcher = RuleBasedMatcher()

    # ============ Memory Intent Tests ============

    def test_match_preference_like(self):
        """Test matching preference patterns."""
        test_cases = [
            "我喜欢Python",
            "我偏好使用Mac",
            "我不喜欢Java",
            "我最喜欢吃火锅",
        ]
        for message in test_cases:
            result = self.matcher.match(message)
            assert result is not None, f"Should match: {message}"
            assert result.intent_type == "preference"
            assert result.confidence == 1.0
            assert result.source == "layer1"

    def test_match_fact_identity(self):
        """Test matching fact patterns."""
        test_cases = [
            "我叫小明",
            "我是前端开发",
            "我在北京工作",
            "我今年25岁",
        ]
        for message in test_cases:
            result = self.matcher.match(message)
            assert result is not None, f"Should match: {message}"
            assert result.intent_type == "fact"

    def test_match_pattern_habit(self):
        """Test matching pattern/habit patterns."""
        test_cases = [
            "我每天早上6点起床",
            "我通常用Chrome浏览器",
            "我习惯晚上写代码",
        ]
        for message in test_cases:
            result = self.matcher.match(message)
            assert result is not None, f"Should match: {message}"
            assert result.intent_type == "pattern"

    def test_match_opinion(self):
        """Test matching opinion patterns."""
        test_cases = [
            "我认为AI很重要",
            "我觉得这个方案不错",
            "我相信未来会更好",
            "在我看来这是最佳选择",
        ]
        for message in test_cases:
            result = self.matcher.match(message)
            assert result is not None, f"Should match: {message}"
            assert result.intent_type == "opinion"

    # ============ HITL Intent Tests ============

    def test_match_plan_reminder(self):
        """Test matching plan/reminder patterns."""
        test_cases = [
            "提醒我明天开会",
            "别忘了下周交报告",
            "明天3点要去面试",
            "每天8点提醒我吃药",
        ]
        for message in test_cases:
            result = self.matcher.match(message)
            assert result is not None, f"Should match: {message}"
            assert result.intent_type == "plan_reminder"

    def test_match_greeting(self):
        """Test matching greeting patterns."""
        test_cases = [
            "你好",
            "嗨",
            "hello",
            "早上好",
        ]
        for message in test_cases:
            result = self.matcher.match(message)
            assert result is not None, f"Should match: {message}"
            assert result.intent_type == "proactive_inquiry"

    def test_match_emotion_positive(self):
        """Test matching positive emotion patterns."""
        test_cases = [
            "心情很好",
            "很开心今天完成了项目",
            "太棒了!",
        ]
        for message in test_cases:
            result = self.matcher.match(message)
            assert result is not None, f"Should match: {message}"
            assert result.intent_type == "emotion_driven"

    def test_match_emotion_negative(self):
        """Test matching negative emotion patterns."""
        test_cases = [
            "心情不好",
            "很难过",
            "好累啊",
        ]
        for message in test_cases:
            result = self.matcher.match(message)
            assert result is not None, f"Should match: {message}"
            assert result.intent_type == "emotion_driven"

    def test_match_recommendation_request(self):
        """Test matching recommendation request patterns."""
        test_cases = [
            "推荐一本书",
            "有什么电影推荐",
            "帮我推荐个餐厅",
        ]
        for message in test_cases:
            result = self.matcher.match(message)
            assert result is not None, f"Should match: {message}"
            assert result.intent_type == "memory_gap"

    # ============ No Match Tests ============

    def test_no_match_simple_question(self):
        """Test that simple questions don't match."""
        test_cases = [
            "Python怎么安装？",
            "什么是机器学习？",
            "帮我解释一下这段代码",
        ]
        for message in test_cases:
            result = self.matcher.match(message)
            assert result is None, f"Should not match: {message}"

    def test_no_match_confirmation(self):
        """Test that simple confirmations don't match."""
        test_cases = [
            "好的",
            "谢谢",
            "明白了",
            "收到",
        ]
        for message in test_cases:
            result = self.matcher.match(message)
            assert result is None, f"Should not match: {message}"


class TestIntentPriority:
    """Test that intent priority works correctly."""

    def setup_method(self):
        """Set up test fixtures."""
        self.matcher = RuleBasedMatcher()

    def test_plan_reminder_higher_priority(self):
        """Test that plan_reminder has higher priority than other patterns."""
        # This message could match both "preference" and "plan_reminder"
        # but plan_reminder should win due to higher priority
        message = "提醒我明天要买Python的书"
        result = self.matcher.match(message)
        assert result is not None
        # plan_reminder has priority 20, preference has priority 10
        assert result.intent_type == "plan_reminder"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
