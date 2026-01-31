"""Multi-Layer Intent Recognition Module

Provides a two-layer intent recognition system:
- Layer 1: Fast regex/keyword-based matching
- Layer 2: LLM-based classification for ambiguous cases
- Fallback: Normal conversation when no intent matches

Logging format:
- [Intent] Layer1: MATCHED {intent} (confidence={score}, rule={rule_name})
- [Intent] Layer2: MATCHED {intent} (confidence={score})
- [Intent] Fallback: using normal conversation
"""

import json
from typing import Any, List, Optional

from intent_rules import (
    IntentRule,
    get_all_rules,
    get_all_rules_with_dynamic_mcp,
    create_mcp_keyword_rule,
)
from intent_types import (
    IntentCategory,
    IntentResult,
    parse_intent_type,
)


# ============ Layer 1: Rule-Based Matcher ============

class RuleBasedMatcher:
    """Layer 1: Fast regex/keyword-based intent matching.

    Matches user messages against predefined patterns for
    memory intents, HITL triggers, and MCP tool calls.
    """

    def __init__(self, rules: Optional[List[IntentRule]] = None):
        """Initialize with optional custom rules.

        Args:
            rules: List of IntentRule to use. Defaults to all rules.
        """
        self.rules = rules if rules is not None else get_all_rules()

    def update_rules_with_mcp(self, mcp_keyword_rules: List[IntentRule]) -> None:
        """Update rules to include dynamic MCP keyword rules.

        Args:
            mcp_keyword_rules: Additional rules from MCP service configurations
        """
        print(f"[Intent] Updating rules with {len(mcp_keyword_rules)} MCP keyword rules")
        self.rules = get_all_rules_with_dynamic_mcp(mcp_keyword_rules)
        print(f"[Intent] Total rules after update: {len(self.rules)}")

    def match(self, message: str) -> Optional[IntentResult]:
        """Match a message against all rules.

        Args:
            message: User message to match

        Returns:
            IntentResult if matched, None otherwise
        """
        print("[Intent] Layer1: checking user message...")

        for rule in self.rules:
            if rule.pattern.search(message):
                # Determine category based on intent type
                category, _ = parse_intent_type(rule.intent_type)
                if category is None:
                    continue

                result = IntentResult(
                    category=category,
                    intent_type=rule.intent_type,
                    confidence=1.0,
                    matched_rule=rule.name,
                    source="layer1",
                    mcp_service_name=rule.mcp_service_name,  # Pass through MCP service name
                )

                print(
                    f"[Intent] Layer1: MATCHED {rule.intent_type} "
                    f"(confidence=1.0, rule={rule.name})"
                )
                return result

        print("[Intent] Layer1: no match")
        return None


# ============ Layer 2: LLM-Based Classifier ============

# Minimal prompt for intent classification (< 500 tokens)
INTENT_CLASSIFICATION_PROMPT = """分析用户消息的意图类型。

用户消息: {message}

可能的意图类型:
Memory类（用户分享信息）:
- preference: 用户偏好（喜欢/不喜欢）
- fact: 用户事实（个人信息、职业、技能）
- pattern: 行为模式（习惯、日常）
- opinion: 个人观点（认为、觉得、相信）

HITL类（需要表单交互）:
- proactive_inquiry: 问候或初次对话
- topic_deepening: 提到兴趣领域但未详细说明
- emotion_driven: 表达情绪状态
- memory_gap: 请求推荐或建议
- question_to_form: 可结构化的问题或计划
- plan_reminder: 时间相关的提醒或计划

返回JSON格式:
{{"intent_type": "类型名称或null", "confidence": 0.0-1.0}}

只返回JSON，不要其他文字:"""


class LLMIntentClassifier:
    """Layer 2: LLM-based intent classification.

    Uses a lightweight LLM call with minimal prompt to classify
    ambiguous user messages that Layer 1 couldn't match.
    """

    # Default confidence threshold - 0.7 provides good balance between
    # precision (avoiding false positives) and recall (catching valid intents)
    DEFAULT_CONFIDENCE_THRESHOLD = 0.7

    def __init__(
        self,
        llm_client: Any,
        model: Optional[str] = None,
        confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
    ):
        """Initialize the classifier.

        Args:
            llm_client: LLM client for API calls (httpx async client)
            model: Model to use. Defaults to main chat model from config.
            confidence_threshold: Minimum confidence to accept match (default 0.7).
        """
        self.llm_client = llm_client
        self.model = model
        self.confidence_threshold = confidence_threshold

    async def classify(
        self,
        message: str,
        api_base: str,
        api_key: str,
        model: Optional[str] = None,
    ) -> Optional[IntentResult]:
        """Classify a message using LLM.

        Args:
            message: User message to classify
            api_base: LLM API base URL
            api_key: API key
            model: Model to use (overrides instance default)

        Returns:
            IntentResult if classified, None otherwise
        """
        print("[Intent] Layer2: calling LLM classifier...")

        use_model = model or self.model
        if not use_model:
            print("[Intent] Layer2: no model configured, skipping")
            return None

        prompt = INTENT_CLASSIFICATION_PROMPT.format(message=message)

        try:
            response = await self.llm_client.post(
                f"{api_base}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": use_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 100,
                    "temperature": 0.1,
                },
                timeout=10.0,
            )

            if response.status_code != 200:
                print(f"[Intent] Layer2: API error {response.status_code}")
                return None

            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()

            return self._parse_response(content)

        except Exception as e:
            print(f"[Intent] Layer2: classification failed: {e}")
            return None

    def _parse_response(self, content: str) -> Optional[IntentResult]:
        """Parse LLM response to extract intent.

        Args:
            content: Raw LLM response content

        Returns:
            IntentResult if parsed successfully, None otherwise
        """
        try:
            # Handle potential markdown code blocks
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            content = content.strip()

            data = json.loads(content)
            intent_type = data.get("intent_type")
            confidence = float(data.get("confidence", 0.0))

            if not intent_type or intent_type == "null":
                print(f"[Intent] Layer2: no match (confidence={confidence:.2f})")
                return None

            if confidence < self.confidence_threshold:
                print(
                    f"[Intent] Layer2: no match "
                    f"(confidence={confidence:.2f} < threshold={self.confidence_threshold})"
                )
                return None

            # Parse intent type to category
            category, _ = parse_intent_type(intent_type)
            if category is None:
                print(f"[Intent] Layer2: unknown intent type '{intent_type}'")
                return None

            result = IntentResult(
                category=category,
                intent_type=intent_type,
                confidence=confidence,
                matched_rule=None,
                source="layer2",
            )

            print(
                f"[Intent] Layer2: MATCHED {intent_type} "
                f"(confidence={confidence:.2f})"
            )
            return result

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"[Intent] Layer2: parse error: {e}")
            return None


# ============ Main Intent Recognizer ============

class IntentRecognizer:
    """Multi-layer intent recognition combining Layer 1 and Layer 2.

    Flow:
    1. Layer 1 (rules) -> if match, return immediately
    2. Layer 2 (LLM) -> if match with high confidence, return
    3. Fallback -> return normal conversation intent
    """

    def __init__(
        self,
        llm_client: Any = None,
        layer2_model: Optional[str] = None,
        layer2_threshold: float = LLMIntentClassifier.DEFAULT_CONFIDENCE_THRESHOLD,
        layer2_enabled: bool = True,
        mcp_keyword_rules: Optional[List[IntentRule]] = None,
    ):
        """Initialize the recognizer.

        Args:
            llm_client: HTTP client for Layer 2 LLM calls
            layer2_model: Model to use for Layer 2 (defaults to main chat model)
            layer2_threshold: Confidence threshold for Layer 2 (default 0.7)
            layer2_enabled: Whether to use Layer 2 (disable to save API calls)
            mcp_keyword_rules: Additional MCP rules from service configurations
        """
        self.layer1 = RuleBasedMatcher()
        if mcp_keyword_rules:
            self.layer1.update_rules_with_mcp(mcp_keyword_rules)
        self.layer2 = LLMIntentClassifier(
            llm_client=llm_client,
            model=layer2_model,
            confidence_threshold=layer2_threshold,
        ) if llm_client and layer2_enabled else None
        self.layer2_enabled = layer2_enabled

    async def recognize(
        self,
        message: str,
        api_base: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ) -> IntentResult:
        """Recognize intent from user message.

        Args:
            message: User message
            api_base: LLM API base URL (for Layer 2)
            api_key: API key (for Layer 2)
            model: Model to use (for Layer 2)

        Returns:
            IntentResult with matched intent or normal fallback
        """
        # Layer 1: Rule-based matching
        result = self.layer1.match(message)
        if result:
            print(f"[Intent] Using prompt snippet: {result.intent_type}")
            return result

        # Layer 2: LLM-based classification
        if self.layer2 and api_base and api_key:
            result = await self.layer2.classify(
                message=message,
                api_base=api_base,
                api_key=api_key,
                model=model,
            )
            if result:
                print(f"[Intent] Using prompt snippet: {result.intent_type}")
                return result

        # Fallback: Normal conversation
        print("[Intent] Fallback: using normal conversation")
        return IntentResult.normal()


# ============ Convenience Function ============

async def recognize_intent(
    message: str,
    llm_client: Any = None,
    api_base: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    layer2_enabled: bool = True,
    layer2_threshold: float = LLMIntentClassifier.DEFAULT_CONFIDENCE_THRESHOLD,
    mcp_keyword_rules: Optional[List[IntentRule]] = None,
) -> IntentResult:
    """Convenience function for one-shot intent recognition.

    Args:
        message: User message to analyze
        llm_client: HTTP client for Layer 2
        api_base: LLM API base URL
        api_key: API key
        model: Model to use (defaults to main chat model)
        layer2_enabled: Whether to use Layer 2
        layer2_threshold: Confidence threshold for Layer 2 (default 0.7)
        mcp_keyword_rules: Additional MCP rules from service configurations

    Returns:
        IntentResult with matched intent
    """
    recognizer = IntentRecognizer(
        llm_client=llm_client,
        layer2_model=model,
        layer2_threshold=layer2_threshold,
        layer2_enabled=layer2_enabled,
        mcp_keyword_rules=mcp_keyword_rules,
    )
    return await recognizer.recognize(
        message=message,
        api_base=api_base,
        api_key=api_key,
        model=model,
    )


def build_mcp_keyword_rules_from_services(running_services: List[Any]) -> List[IntentRule]:
    """Build MCP keyword rules from running MCP services.

    Args:
        running_services: List of MCPServerInfo for running services

    Returns:
        List of IntentRule for MCP keyword matching
    """
    print(f"[Intent] Building MCP keyword rules from {len(running_services)} services")
    rules = []
    for service in running_services:
        if hasattr(service, 'trigger_keywords') and service.trigger_keywords:
            rule = create_mcp_keyword_rule(service.name, service.trigger_keywords)
            if rule:
                rules.append(rule)
                print(f"[Intent] Created MCP rule: service='{service.name}', keywords={service.trigger_keywords}")
        else:
            print(f"[Intent] Service '{service.name}' has no trigger_keywords")
    print(f"[Intent] Built {len(rules)} MCP keyword rules total")
    return rules
