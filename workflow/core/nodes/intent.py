"""IntentNode - Multi-layer intent recognition for the cognitive graph.

Performs intent recognition on user input before other processing nodes,
enabling prompt optimization in downstream nodes (especially ReasoningNode).

Supports:
- Layer 1: Fast regex/keyword matching
- Layer 2: LLM-based classification (optional)
- MCP service keyword matching
"""

import logging
from typing import Dict, Any, List, Optional

from core.state import GraphState

logger = logging.getLogger(__name__)


class IntentNode:
    """
    Intent recognition node for the cognitive graph.

    Wraps the existing IntentRecognizer to provide multi-layer intent detection.
    Respects the system.intent_recognition_enabled setting.
    """

    def __init__(self, layer2_enabled: bool = True, api_base: str = "", api_key: str = "", model: str = ""):
        """
        Initialize the IntentNode.

        Args:
            layer2_enabled: Whether to enable Layer 2 LLM classification.
            api_base: LLM API base URL (avoids redundant config loading).
            api_key: API key for LLM calls.
            model: Model name for LLM calls.
        """
        self.layer2_enabled = layer2_enabled
        self._api_base = api_base
        self._api_key = api_key
        self._model = model
        self._matcher = None
        self._mcp_rules_initialized = False

    def _get_matcher(self):
        """Lazy load RuleBasedMatcher."""
        if self._matcher is None:
            from intent_recognizer import RuleBasedMatcher
            self._matcher = RuleBasedMatcher()
        return self._matcher

    def _update_mcp_rules(self):
        """Update matcher with MCP keyword rules from running services."""
        if self._mcp_rules_initialized:
            return

        try:
            from intent_recognizer import build_mcp_keyword_rules_from_services
            import mcp_manager

            pm = mcp_manager.get_process_manager()
            running_services = pm.get_running_servers()

            if running_services:
                mcp_rules = build_mcp_keyword_rules_from_services(running_services)
                if mcp_rules:
                    self._get_matcher().update_rules_with_mcp(mcp_rules)
                    logger.info(f"[IntentNode] Updated matcher with {len(mcp_rules)} MCP rules")

            self._mcp_rules_initialized = True
        except Exception as e:
            logger.warning(f"[IntentNode] Failed to load MCP rules: {e}")

    async def compute(self, state: GraphState) -> Dict[str, Any]:
        """
        Perform intent recognition on the input text.

        Args:
            state: Current graph state with semantic_input

        Returns:
            State updates with intent_result field, or empty dict if disabled
        """
        # Check if intent recognition is enabled
        from chat_processor import is_intent_recognition_enabled

        if not is_intent_recognition_enabled():
            logger.info("[IntentNode] Intent recognition disabled, skipping")
            return {}

        text = state.semantic_input.text
        if not text:
            logger.info("[IntentNode] No input text, returning normal intent")
            return self._make_normal_result()

        logger.info(f"[IntentNode] Processing: {text[:50]}...")

        # Update MCP rules if not done yet
        self._update_mcp_rules()

        # Layer 1: Rule-based matching
        matcher = self._get_matcher()
        result = matcher.match(text)

        if result:
            logger.info(f"[IntentNode] Layer1 matched: {result.intent_type} (rule={result.matched_rule})")
            return {"intent_result": self._result_to_dict(result)}

        # Layer 2: LLM classification (if enabled)
        if self.layer2_enabled:
            result = await self._run_layer2(text)
            if result:
                return {"intent_result": self._result_to_dict(result)}

        # Fallback: normal conversation
        logger.info("[IntentNode] No intent match, fallback to normal")
        return self._make_normal_result()

    async def _run_layer2(self, text: str):
        """Run Layer 2 LLM-based classification."""
        try:
            from intent_recognizer import LLMIntentClassifier
            import httpx

            api_base = self._api_base
            api_key = self._api_key
            model = self._model

            # Fallback to loading config if not provided at init
            if not api_base or not api_key or not model:
                from graph_runner import load_chat_config
                config = load_chat_config()
                api_base = api_base or config.api_base
                api_key = api_key or config.api_key
                model = model or config.model

            if not api_key:
                logger.warning("[IntentNode] Layer2 skipped: no API key configured")
                return None

            async with httpx.AsyncClient() as client:
                classifier = LLMIntentClassifier(
                    llm_client=client,
                    model=model,
                )
                result = await classifier.classify(
                    message=text,
                    api_base=api_base,
                    api_key=api_key,
                    model=model,
                )
                if result:
                    logger.info(f"[IntentNode] Layer2 matched: {result.intent_type}")
                    return result
        except Exception as e:
            logger.error(f"[IntentNode] Layer2 failed: {e}", exc_info=True)

        return None

    def _result_to_dict(self, result) -> Dict[str, Any]:
        """Convert IntentResult to dict for state storage."""
        return {
            "category": result.category.value if hasattr(result.category, 'value') else str(result.category),
            "intent_type": result.intent_type,
            "confidence": result.confidence,
            "source": result.source,
            "matched_rule": result.matched_rule,
            "mcp_service_name": result.mcp_service_name,
        }

    def _make_normal_result(self) -> Dict[str, Any]:
        """Create a normal conversation intent result."""
        return {
            "intent_result": {
                "category": "normal",
                "intent_type": "normal",
                "confidence": 0.0,
                "source": "fallback",
                "matched_rule": None,
                "mcp_service_name": None,
            }
        }
