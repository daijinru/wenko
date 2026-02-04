"""ReasoningNode - The Brain of the Cognitive Graph

Generates responses using LLM with full context from emotion detection and memory retrieval.
Supports streaming token output, tool calls, HITL requests, and memory updates.
"""

import json
import logging
from typing import Dict, Any, Optional, AsyncGenerator, Callable

import httpx

from core.state import GraphState, HITLRequest

logger = logging.getLogger(__name__)


class ReasoningNode:
    """
    The Brain. Decides next action based on state.
    Uses real LLM API via httpx for streaming responses.
    """

    def __init__(
        self,
        api_base: str,
        api_key: str,
        model: str,
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ):
        self.api_base = api_base
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature

    async def compute(
        self,
        state: GraphState,
        stream_callback: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """
        Generate plan/response using LLM.

        Args:
            state: Current graph state with all context
            stream_callback: Optional callback for streaming tokens

        Returns:
            State updates including response, tool_calls, or hitl_request
        """
        # 1. Build prompt using chat_processor
        from chat_processor import (
            build_chat_context,
            build_system_prompt,
            process_llm_response,
            extract_tool_call,
            is_hitl_enabled,
        )
        from hitl_handler import extract_hitl_from_llm_response

        # Build context from state
        chat_context = build_chat_context(
            session_id=state.conversation_id,
            user_message=state.semantic_input.text,
        )

        # Inject intent from IntentNode if available
        if state.intent_result:
            from intent_types import IntentResult, IntentCategory
            # Convert dict back to IntentResult for chat_context
            category_str = state.intent_result.get("category", "normal")
            try:
                category = IntentCategory(category_str)
            except ValueError:
                category = IntentCategory.NORMAL

            chat_context.intent_result = IntentResult(
                category=category,
                intent_type=state.intent_result.get("intent_type"),
                confidence=state.intent_result.get("confidence", 0.0),
                source=state.intent_result.get("source", "graph"),
                matched_rule=state.intent_result.get("matched_rule"),
                mcp_service_name=state.intent_result.get("mcp_service_name"),
            )
            logger.info(f"[ReasoningNode] Using intent from IntentNode: {category_str}/{state.intent_result.get('intent_type')}")
        elif state.semantic_input.intent:
            # Fallback: legacy intent from semantic_input
            from intent_types import IntentResult, IntentCategory
            chat_context.intent_result = IntentResult(
                category=IntentCategory.NORMAL,
                intent_type=state.semantic_input.intent,
                confidence=1.0,
                source="graph",
            )

        # Build the full system prompt
        system_prompt = build_system_prompt(chat_context)

        # 2. Prepare messages
        messages = [{"role": "system", "content": system_prompt}]

        # Add dialogue history if available
        for msg in state.dialogue_history:
            messages.append({"role": msg["role"], "content": msg["content"]})

        # Add current user message
        messages.append({"role": "user", "content": state.semantic_input.text})

        # 3. Call LLM with streaming
        full_response = ""
        try:
            async for token in self._stream_llm(messages):
                full_response += token
                if stream_callback:
                    stream_callback(token)
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return {"observation": f"LLM error: {str(e)}"}

        # 4. Parse the response
        updates = {}

        # Try to extract tool call
        tool_call = extract_tool_call(full_response)
        if tool_call:
            logger.info(f"[ReasoningNode] Tool call detected: {tool_call.name}.{tool_call.method}")
            updates["pending_tool_calls"] = [{
                "service": tool_call.name,
                "method": tool_call.method,
                "args": tool_call.arguments,
            }]
            updates["observation"] = None
            # Also store the response text for display
            try:
                parsed = json.loads(full_response)
                if "response" in parsed:
                    updates["response"] = parsed["response"]
            except json.JSONDecodeError:
                pass
            return updates

        # Try to extract HITL request
        if is_hitl_enabled():
            hitl_request = extract_hitl_from_llm_response(full_response)
            if hitl_request:
                logger.info(f"[ReasoningNode] HITL request detected: {hitl_request.type}")
                # Convert to state HITLRequest format
                updates["hitl_request"] = HITLRequest(
                    type=hitl_request.type,
                    message=hitl_request.title,
                    options=[],
                    context_data={"hitl_id": hitl_request.id},
                )
                updates["status"] = "suspended"
                # Store full HITL data for frontend (as dict for LangGraph serialization)
                updates["hitl_full_request"] = hitl_request.model_dump(mode='json') if hasattr(hitl_request, 'model_dump') else dict(hitl_request)
                # Also extract response text
                try:
                    parsed = json.loads(full_response)
                    if "response" in parsed:
                        updates["response"] = parsed["response"]
                except json.JSONDecodeError:
                    pass
                return updates

        # 5. Process normal response
        try:
            chat_result = process_llm_response(full_response, chat_context)
            response_text = chat_result.response

            # Update dialogue history
            current_history = list(state.dialogue_history)
            current_history.append({"role": "assistant", "content": response_text})
            updates["dialogue_history"] = current_history

            # Store response for SSE emission
            updates["response"] = response_text

            # Store emotion if detected
            if chat_result.emotion:
                updates["detected_emotion"] = {
                    "primary": chat_result.emotion.primary,
                    "category": chat_result.emotion.category,
                    "confidence": chat_result.emotion.confidence,
                }

            # Store memories to save
            if chat_result.memories_to_store:
                updates["memories_to_store"] = chat_result.memories_to_store

        except Exception as e:
            logger.warning(f"Failed to parse LLM response as JSON: {e}")
            # Fallback: treat raw response as text
            try:
                parsed = json.loads(full_response)
                response_text = parsed.get("response", full_response)
            except json.JSONDecodeError:
                response_text = full_response

            current_history = list(state.dialogue_history)
            current_history.append({"role": "assistant", "content": response_text})
            updates["dialogue_history"] = current_history
            updates["response"] = response_text

        return updates

    async def _stream_llm(self, messages: list) -> AsyncGenerator[str, None]:
        """
        Stream tokens from the LLM API.

        Args:
            messages: List of messages in OpenAI format

        Yields:
            Individual tokens as they arrive
        """
        api_url = f"{self.api_base.rstrip('/')}/chat/completions"

        request_body = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "stream": True,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                api_url,
                json=request_body,
                headers=headers,
            ) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    raise Exception(f"API error {response.status_code}: {error_text.decode()}")

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data.strip() == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue

    async def call_llm_non_streaming(self, messages: list) -> str:
        """
        Call LLM without streaming (for testing or simple cases).

        Args:
            messages: List of messages in OpenAI format

        Returns:
            Complete response text
        """
        api_url = f"{self.api_base.rstrip('/')}/chat/completions"

        request_body = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "stream": False,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(api_url, json=request_body, headers=headers)
            if response.status_code != 200:
                raise Exception(f"API error {response.status_code}: {response.text}")

            data = response.json()
            return data.get("choices", [{}])[0].get("message", {}).get("content", "")
