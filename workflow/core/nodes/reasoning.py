"""ReasoningNode - The Brain of the Cognitive Graph

Generates responses using LLM with full context from emotion detection and memory retrieval.
Supports streaming token output, tool calls, ECS requests, and memory updates.
"""

import json
import logging
from typing import Dict, Any, Optional, AsyncGenerator, Callable

import httpx

from core.state import GraphState, ECSRequest, ExecutionContract, ExecutionStatus, ExecutionStep, ExecutionConsequenceView, compute_idempotency_key, can_create_contract

logger = logging.getLogger(f"workflow.{__name__}")

# Maximum consecutive identical tool calls before forcing termination
MAX_IDENTICAL_TOOL_CALLS = 3


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
            State updates including response, tool_calls, or ecs_request
        """
        # 1. Build prompt using chat_processor
        from chat_processor import (
            build_chat_context,
            build_system_prompt,
            process_llm_response,
            extract_tool_call,
            is_ecs_enabled,
        )
        from ecs_handler import extract_ecs_from_llm_response

        # Build context from state
        chat_context = build_chat_context(
            session_id=state.conversation_id,
            user_message=state.semantic_input.text,
        )

        # Inject emotional_context from EmotionNode
        if state.emotional_context:
            chat_context.emotional_context = state.emotional_context

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

        # Add tool execution result if available (critical for multi-step tool workflows)
        # Prefer structured consequence views over raw observation strings
        tool_result_text = self._build_tool_result_from_consequences(state)
        if tool_result_text:
            logger.info(f"[ReasoningNode] Using structured consequence views ({len(state.completed_executions)} contracts)")
            has_irreversible = any(
                c.irreversible and c.status == ExecutionStatus.COMPLETED
                for c in state.completed_executions
            )
            warning_suffix = "\n注意：标记 IRREVERSIBLE 的操作已在现实中生效，无法撤回。" if has_irreversible else ""
            tool_result_msg = f"【工具执行结果】\n{tool_result_text}{warning_suffix}\n\n请根据以上工具返回的结果继续处理用户的请求。如果需要调用其他工具（如使用返回的ID查询文档），请继续调用。如果结果已经足够回答用户问题，请直接给出回复。"
            messages.append({"role": "user", "content": tool_result_msg})
        elif state.observation:
            logger.info(f"[ReasoningNode] Using legacy observation string (length={len(state.observation)})")
            tool_result_msg = f"【工具执行结果】\n{state.observation}\n\n请根据以上工具返回的结果继续处理用户的请求。如果需要调用其他工具（如使用返回的ID查询文档），请继续调用。如果结果已经足够回答用户问题，请直接给出回复。"
            messages.append({"role": "user", "content": tool_result_msg})

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

            # Check for tool call loop
            current_call = {
                "service": tool_call.name,
                "method": tool_call.method,
                "args": tool_call.arguments,
            }

            # Count consecutive identical calls
            tool_history = list(state.tool_call_history)
            consecutive_count = 0
            for prev_call in reversed(tool_history):
                if (prev_call.get("service") == current_call["service"] and
                    prev_call.get("method") == current_call["method"]):
                    consecutive_count += 1
                else:
                    break

            if consecutive_count >= MAX_IDENTICAL_TOOL_CALLS:
                logger.warning(f"[ReasoningNode] Tool call loop detected: {tool_call.name}.{tool_call.method} called {consecutive_count + 1} times consecutively. Forcing termination.")
                # Force termination with error message
                error_msg = f"工具调用循环检测：{tool_call.name}.{tool_call.method} 已连续调用 {consecutive_count + 1} 次。请检查查询参数或换用其他方法。"
                updates["response"] = error_msg
                updates["pending_tool_calls"] = []
                updates["observation"] = None
                return updates

            # Record this tool call in history
            tool_history.append(current_call)
            updates["tool_call_history"] = tool_history

            # Create ExecutionContract for the tool call
            all_contracts = list(state.completed_executions) + list(state.pending_executions)
            irreversible = current_call.get("args", {}).get("irreversible", False)
            idempotency_key = compute_idempotency_key(current_call) if irreversible else None

            if irreversible and not can_create_contract(current_call, all_contracts):
                logger.warning(f"[ReasoningNode] Irreversible operation already completed: {tool_call.name}.{tool_call.method}")
                updates["response"] = f"操作已完成，无需重复执行：{tool_call.name}.{tool_call.method}"
                updates["pending_tool_calls"] = []
                return updates

            contract = ExecutionContract(
                action_type="tool_call",
                action_detail=current_call,
                irreversible=irreversible,
                idempotency_key=idempotency_key,
            )
            logger.info(
                f"[ReasoningNode] Created tool contract {contract.execution_id[:8]}: "
                f"{tool_call.name}.{tool_call.method} (irreversible={irreversible})"
            )

            updates["pending_tool_calls"] = [current_call]
            updates["pending_executions"] = [contract]
            updates["observation"] = None
            # Also store the response text for display
            try:
                parsed = json.loads(full_response)
                if "response" in parsed:
                    updates["response"] = parsed["response"]
            except json.JSONDecodeError:
                pass
            return updates

        # Try to extract ECS request
        if is_ecs_enabled():
            ecs_request = extract_ecs_from_llm_response(full_response)
            if ecs_request:
                logger.info(f"[ReasoningNode] ECS request detected: {ecs_request.type}")
                # Convert to state ECSRequest format
                updates["ecs_request"] = ECSRequest(
                    type=ecs_request.type,
                    message=ecs_request.title,
                    options=[],
                    context_data={"ecs_id": ecs_request.id},
                )
                updates["status"] = "suspended"
                # Store full ECS data for frontend (as dict for LangGraph serialization)
                updates["ecs_full_request"] = ecs_request.model_dump(mode='json') if hasattr(ecs_request, 'model_dump') else dict(ecs_request)

                # Create ExecutionContract for the ECS request
                ecs_contract = ExecutionContract(
                    action_type="ecs_request",
                    action_detail={
                        "type": ecs_request.type,
                        "id": ecs_request.id,
                        "title": ecs_request.title,
                    },
                )
                updates["pending_executions"] = [ecs_contract]
                logger.info(
                    f"[ReasoningNode] Created ECS contract {ecs_contract.execution_id[:8]}: "
                    f"type={ecs_request.type}, id={ecs_request.id}"
                )

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

    def _build_tool_result_from_consequences(self, state: GraphState) -> str:
        """
        Build tool result text from ExecutionConsequenceView projections.
        Uses the observation layer to perceive execution outcomes rather than
        reading ExecutionContract fields directly.

        Returns:
            Formatted result string, or empty string if no completed tool contracts.
        """
        from observation import ExecutionObserver

        if not state.completed_executions:
            return ""

        observer = ExecutionObserver()
        consequences = observer.consequence_views(list(state.completed_executions))

        results = []
        for cv in consequences:
            if cv.action_type != "tool_call":
                continue

            label = cv.consequence_label
            side_effect_tag = " IRREVERSIBLE" if cv.has_side_effects else ""
            suspended_tag = " (human-confirmed)" if cv.was_suspended else ""

            if label == "SUCCESS":
                results.append(f"[{label}{side_effect_tag}{suspended_tag}] {cv.action_summary}: {cv.result}")
            elif label in ("FAILED", "REJECTED", "CANCELLED"):
                results.append(f"[{label}] {cv.action_summary}: {cv.error_message}")

            logger.debug(f"[ReasoningNode] Consequence {cv.execution_id[:8]}: {label} ({cv.action_summary})")

        return "\n\n".join(results)

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
