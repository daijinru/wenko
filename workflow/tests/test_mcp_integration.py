"""Tests for MCP Conversation Integration

Tests for:
- MCP intent types and recognition
- MCP service configuration extensions
- MCP tool executor
- Tool call extraction from LLM output
"""

import pytest
import sys
import os
import json

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from intent_types import (
    IntentCategory,
    IntentResult,
    MCPIntent,
    parse_intent_type,
)
from intent_rules import (
    get_all_rules,
    get_mcp_rules,
    create_mcp_keyword_rule,
)
from intent_recognizer import (
    RuleBasedMatcher,
    build_mcp_keyword_rules_from_services,
)
import chat_processor


class TestMCPIntentTypes:
    """Tests for MCP intent type definitions."""

    def test_mcp_intent_values(self):
        """Test MCPIntent enum values."""
        assert MCPIntent.TOOL_CALL.value == "mcp_tool_call"

    def test_intent_category_includes_mcp(self):
        """Test that IntentCategory includes MCP."""
        assert IntentCategory.MCP.value == "mcp"

    def test_intent_result_mcp(self):
        """Test IntentResult.mcp() factory method."""
        result = IntentResult.mcp(service_name="weather", confidence=1.0)
        assert result.category == IntentCategory.MCP
        assert result.intent_type == "mcp_tool_call"
        assert result.confidence == 1.0
        assert result.mcp_service_name == "weather"
        assert result.is_mcp()
        assert not result.is_memory()
        assert not result.is_hitl()
        assert not result.is_normal()

    def test_intent_result_mcp_no_service(self):
        """Test IntentResult.mcp() without service name."""
        result = IntentResult.mcp()
        assert result.category == IntentCategory.MCP
        assert result.mcp_service_name is None
        assert result.is_mcp()

    def test_parse_intent_type_mcp(self):
        """Test parsing MCP intent types."""
        category, intent_type = parse_intent_type("mcp_tool_call")
        assert category == IntentCategory.MCP
        assert intent_type == "mcp_tool_call"


class TestMCPIntentRules:
    """Tests for MCP intent rule definitions."""

    def test_get_mcp_rules(self):
        """Test getting MCP-specific rules."""
        rules = get_mcp_rules()
        assert len(rules) > 0
        for rule in rules:
            assert rule.intent_type == "mcp_tool_call"

    def test_get_all_rules_includes_mcp(self):
        """Test that get_all_rules includes MCP rules."""
        rules = get_all_rules(include_mcp=True)
        mcp_rules = [r for r in rules if r.intent_type == "mcp_tool_call"]
        assert len(mcp_rules) > 0

    def test_create_mcp_keyword_rule(self):
        """Test creating MCP keyword rule from service config."""
        rule = create_mcp_keyword_rule("weather", ["天气", "气温", "下雨"])
        assert rule is not None
        assert rule.name == "mcp_keyword_weather"
        assert rule.intent_type == "mcp_tool_call"
        assert rule.mcp_service_name == "weather"
        assert rule.priority == 20

    def test_create_mcp_keyword_rule_empty(self):
        """Test creating MCP keyword rule with no keywords."""
        rule = create_mcp_keyword_rule("empty_service", [])
        assert rule is None


class TestMCPRuleBasedMatcher:
    """Tests for MCP rule-based matching."""

    def setup_method(self):
        """Set up test fixtures."""
        self.matcher = RuleBasedMatcher()

    def test_match_explicit_tool_call(self):
        """Test matching explicit tool call patterns."""
        test_cases = [
            "用天气工具查一下",
            "使用翻译工具帮我翻译",
            "调用计算工具",
            "运行搜索工具找一下",
        ]
        for message in test_cases:
            result = self.matcher.match(message)
            assert result is not None, f"Should match: {message}"
            assert result.intent_type == "mcp_tool_call"
            assert result.source == "layer1"

    def test_match_explicit_service_call(self):
        """Test matching explicit service call patterns."""
        test_cases = [
            "用翻译服务",
            "使用天气服务查询",
            "调用文件服务",
        ]
        for message in test_cases:
            result = self.matcher.match(message)
            assert result is not None, f"Should match: {message}"
            assert result.intent_type == "mcp_tool_call"

    def test_match_with_dynamic_keywords(self):
        """Test matching with dynamic MCP keyword rules."""
        # Create dynamic rules
        weather_rule = create_mcp_keyword_rule("weather", ["天气", "气温"])
        translate_rule = create_mcp_keyword_rule("translate", ["翻译", "英文"])

        # Update matcher with dynamic rules
        self.matcher.update_rules_with_mcp([weather_rule, translate_rule])

        # Test matching
        result = self.matcher.match("今天天气怎么样")
        assert result is not None
        assert result.intent_type == "mcp_tool_call"
        assert result.mcp_service_name == "weather"

        result = self.matcher.match("帮我翻译一下")
        assert result is not None
        assert result.intent_type == "mcp_tool_call"
        assert result.mcp_service_name == "translate"


class TestToolCallExtraction:
    """Tests for extracting tool_call from LLM output."""

    def test_extract_tool_call_basic(self):
        """Test extracting basic tool_call."""
        llm_output = json.dumps({
            "response": "让我帮你查询天气",
            "emotion": {"primary": "neutral", "category": "neutral", "confidence": 0.8},
            "memory_update": {"should_store": False, "entries": []},
            "tool_call": {
                "name": "weather",
                "method": "get_weather",
                "arguments": {"city": "北京"}
            }
        })

        result = chat_processor.extract_tool_call(llm_output)
        assert result is not None
        assert result.name == "weather"
        assert result.method == "get_weather"
        assert result.arguments == {"city": "北京"}

    def test_extract_tool_call_default_method(self):
        """Test that method defaults to name if not specified."""
        llm_output = json.dumps({
            "response": "查询中",
            "tool_call": {
                "name": "weather",
                "arguments": {"city": "上海"}
            }
        })

        result = chat_processor.extract_tool_call(llm_output)
        assert result is not None
        assert result.name == "weather"
        assert result.method == "weather"  # Defaults to name

    def test_extract_tool_call_no_tool_call(self):
        """Test extraction when no tool_call present."""
        llm_output = json.dumps({
            "response": "普通回复",
            "emotion": {"primary": "neutral", "category": "neutral", "confidence": 0.8},
            "memory_update": {"should_store": False, "entries": []}
        })

        result = chat_processor.extract_tool_call(llm_output)
        assert result is None

    def test_extract_tool_call_invalid_json(self):
        """Test extraction with invalid JSON."""
        result = chat_processor.extract_tool_call("not valid json")
        assert result is None

    def test_extract_tool_call_missing_name(self):
        """Test extraction when tool_call has no name."""
        llm_output = json.dumps({
            "response": "查询中",
            "tool_call": {
                "arguments": {"city": "北京"}
            }
        })

        result = chat_processor.extract_tool_call(llm_output)
        assert result is None

    def test_extract_tool_call_with_markdown(self):
        """Test extraction with markdown code blocks."""
        llm_output = '''```json
{
    "response": "查询天气",
    "tool_call": {
        "name": "weather",
        "method": "query",
        "arguments": {"city": "深圳"}
    }
}
```'''

        result = chat_processor.extract_tool_call(llm_output)
        assert result is not None
        assert result.name == "weather"


class TestMCPIntentSnippet:
    """Tests for MCP intent snippet generation."""

    def test_get_mcp_intent_snippet_no_service(self):
        """Test getting MCP snippet without specific service."""
        snippet = chat_processor.get_mcp_intent_snippet()
        assert "MCP工具调用指令" in snippet
        assert "tool_call" in snippet

    def test_get_mcp_intent_snippet_with_service(self):
        """Test getting MCP snippet with specific service name."""
        snippet = chat_processor.get_mcp_intent_snippet("weather")
        assert "MCP工具调用指令" in snippet
        # Service name should be in the snippet
        assert "weather" in snippet


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
