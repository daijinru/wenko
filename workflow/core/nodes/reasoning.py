import logging
import json
from typing import Dict, Any, Optional
from workflow.core.state import GraphState, HITLRequest
from workflow.core.prompts import CHAT_PROMPT_TEMPLATE
from workflow.mcp_tool_executor import get_mcp_tools_prompt_snippet_async

logger = logging.getLogger(__name__)

class ReasoningNode:
    """
    The Brain. Decides next action based on state.
    """
    def __init__(self, llm_client: Any, model: str):
        self.llm_client = llm_client
        self.model = model

    async def compute(self, state: GraphState) -> Dict[str, Any]:
        """
        Generate plan/response using LLM.
        """
        # 1. Prepare Prompt Context
        working_mem_summary = self._format_working_memory(state.working_memory)
        long_term_mem_summary = self._format_long_term_memory(state.working_memory.retrieved_memories)
        emotion_modulation = f"Modulation Instruction: {state.emotional_context.modulation_instruction}"

        # Tools
        mcp_instruction = await self._get_mcp_instruction()

        # HITL (Simplified for now, assume always enabled or check config)
        hitl_instruction = "..." # We need to inject HITL instructions if we want the LLM to generate HITL requests.
        # For this refactor, let's assume standard HITL prompt injection similar to chat_processor.

        prompt = CHAT_PROMPT_TEMPLATE.format(
            user_message=state.semantic_input.text,
            working_memory_summary=working_mem_summary,
            relevant_long_term_memory=long_term_mem_summary,
            strategy_prompt="", # Can be added if we have StrategyNode
            emotion_modulation=emotion_modulation,
            mcp_instruction=mcp_instruction,
            hitl_instruction="" # Add HITL template if needed
        )

        # 2. Call LLM
        response_text = await self._call_llm(prompt)

        # 3. Parse Output
        parsed = self._parse_output(response_text)

        updates = {}

        # 4. Determine Action
        if parsed.get("tool_call"):
            # Tool Call
            updates["pending_tool_calls"] = [parsed["tool_call"]]
            # We don't return response to user yet if tool is called, or maybe we do?
            # Usually we wait for tool result.
            updates["observation"] = None # Clear previous observation
        elif parsed.get("hitl_request"):
            # HITL Request
            updates["hitl_request"] = HITLRequest(**parsed["hitl_request"])
            updates["status"] = "suspended"
        else:
            # Direct Response
            # If parsed has 'response' field, use it. Otherwise use the raw text if it's not JSON.
            response_content = parsed.get("response")

            # If we failed to parse as JSON, but got some text, maybe treat as response?
            # But _parse_output returns {} on error.
            # Let's rely on parsed keys.

            if response_content:
                # Update dialogue history
                current_history = list(state.dialogue_history)
                current_history.append({"role": "assistant", "content": response_content})
                updates["dialogue_history"] = current_history

                # Also expose it for runners that might look for a 'response' key in the update
                # even if it's not in GraphState (LangGraph allows extra keys in update dict usually,
                # but Pydantic validation might strip it if strict).
                updates["response"] = response_content

        # Always return the raw response for debugging or if it contains the user response
        # But GraphState doesn't have a 'response' field for the final output yet,
        # usually it flows to an OutputNode or is part of the state.
        # Let's assume we update dialogue_history here or return it.

        # For now, let's return the parsed response structure as part of the state update
        # (maybe we need a field for 'current_response' in State)

        return updates

    def _format_working_memory(self, wm):
        return f"Topic: {wm.current_goals}"

    def _format_long_term_memory(self, memories):
        return "\n".join([f"- {m.content}" for m in memories])

    async def _get_mcp_instruction(self):
         snippet = await get_mcp_tools_prompt_snippet_async()
         if snippet:
             return f"Available Tools:\n{snippet}\nTo call a tool, include 'tool_call' in JSON."
         return ""

    async def _call_llm(self, prompt: str) -> str:
        if hasattr(self.llm_client, "chat"):
            response = await self.llm_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
        return "{}"

    def _parse_output(self, text: str) -> Dict[str, Any]:
        try:
            return json.loads(text)
        except:
            return {}
