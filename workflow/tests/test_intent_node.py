"""Tests for IntentNode in the Cognitive Graph

Tests for:
- IntentNode Layer 1 matching
- Intent recognition disabled behavior
- Fallback to normal intent
- Integration with GraphState
"""

import pytest
import asyncio
import sys
import os
from unittest.mock import patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.state import GraphState, SemanticInput
from core.nodes.intent import IntentNode


class TestIntentNodeBasic:
    """Basic tests for IntentNode."""

    def setup_method(self):
        """Set up test fixtures."""
        self.node = IntentNode(layer2_enabled=False)

    @pytest.mark.asyncio
    async def test_intent_recognition_disabled(self):
        """Test that node returns empty dict when disabled."""
        state = GraphState(
            conversation_id="test-session",
            semantic_input=SemanticInput(text="提醒我明天开会"),
        )

        with patch('chat_processor.is_intent_recognition_enabled', return_value=False):
            result = await self.node.compute(state)

        assert result == {}

    @pytest.mark.asyncio
    async def test_empty_input_text(self):
        """Test that empty text returns normal intent."""
        state = GraphState(
            conversation_id="test-session",
            semantic_input=SemanticInput(text=""),
        )

        with patch('chat_processor.is_intent_recognition_enabled', return_value=True):
            result = await self.node.compute(state)

        assert "intent_result" in result
        assert result["intent_result"]["category"] == "normal"

    @pytest.mark.asyncio
    async def test_layer1_match_plan_reminder(self):
        """Test Layer 1 matching for plan reminder intent."""
        state = GraphState(
            conversation_id="test-session",
            semantic_input=SemanticInput(text="提醒我明天下午3点开会"),
        )

        with patch('chat_processor.is_intent_recognition_enabled', return_value=True):
            result = await self.node.compute(state)

        assert "intent_result" in result
        intent = result["intent_result"]
        assert intent["category"] == "ecs"
        assert intent["intent_type"] == "plan_reminder"
        assert intent["confidence"] == 1.0
        assert intent["source"] == "layer1"

    @pytest.mark.asyncio
    async def test_layer1_match_preference(self):
        """Test Layer 1 matching for preference intent."""
        state = GraphState(
            conversation_id="test-session",
            semantic_input=SemanticInput(text="我喜欢Python编程"),
        )

        with patch('chat_processor.is_intent_recognition_enabled', return_value=True):
            result = await self.node.compute(state)

        assert "intent_result" in result
        intent = result["intent_result"]
        assert intent["category"] == "memory"
        assert intent["intent_type"] == "preference"

    @pytest.mark.asyncio
    async def test_layer1_match_greeting(self):
        """Test Layer 1 matching for greeting (proactive inquiry)."""
        state = GraphState(
            conversation_id="test-session",
            semantic_input=SemanticInput(text="你好"),
        )

        with patch('chat_processor.is_intent_recognition_enabled', return_value=True):
            result = await self.node.compute(state)

        assert "intent_result" in result
        intent = result["intent_result"]
        assert intent["category"] == "ecs"
        assert intent["intent_type"] == "proactive_inquiry"

    @pytest.mark.asyncio
    async def test_no_match_fallback_to_normal(self):
        """Test fallback to normal when no pattern matches."""
        state = GraphState(
            conversation_id="test-session",
            semantic_input=SemanticInput(text="Python怎么安装？"),
        )

        with patch('chat_processor.is_intent_recognition_enabled', return_value=True):
            result = await self.node.compute(state)

        assert "intent_result" in result
        intent = result["intent_result"]
        assert intent["category"] == "normal"
        assert intent["source"] == "fallback"


class TestIntentNodeResultFormat:
    """Test intent result format consistency."""

    def setup_method(self):
        """Set up test fixtures."""
        self.node = IntentNode(layer2_enabled=False)

    @pytest.mark.asyncio
    async def test_result_has_all_fields(self):
        """Test that intent result contains all required fields."""
        state = GraphState(
            conversation_id="test-session",
            semantic_input=SemanticInput(text="我喜欢读书"),
        )

        with patch('chat_processor.is_intent_recognition_enabled', return_value=True):
            result = await self.node.compute(state)

        intent = result["intent_result"]
        required_fields = ["category", "intent_type", "confidence", "source", "matched_rule", "mcp_service_name"]
        for field in required_fields:
            assert field in intent, f"Missing field: {field}"

    @pytest.mark.asyncio
    async def test_normal_result_format(self):
        """Test normal intent result format."""
        state = GraphState(
            conversation_id="test-session",
            semantic_input=SemanticInput(text=""),
        )

        with patch('chat_processor.is_intent_recognition_enabled', return_value=True):
            result = await self.node.compute(state)

        intent = result["intent_result"]
        assert intent["category"] == "normal"
        assert intent["intent_type"] == "normal"
        assert intent["confidence"] == 0.0
        assert intent["source"] == "fallback"
        assert intent["matched_rule"] is None
        assert intent["mcp_service_name"] is None


class TestIntentNodeLayer2:
    """Test Layer 2 behavior (mocked)."""

    @pytest.mark.asyncio
    async def test_layer2_disabled_by_default(self):
        """Test that Layer 2 is disabled by default."""
        node = IntentNode()
        assert node.layer2_enabled is False

    @pytest.mark.asyncio
    async def test_layer2_enabled_constructor(self):
        """Test that Layer 2 can be enabled via constructor."""
        node = IntentNode(layer2_enabled=True)
        assert node.layer2_enabled is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
