"""GraphRunner - Adapter to run the cognitive graph and stream results to frontend.

Provides two main methods:
- run(): For text chat requests
- run_image(): For image analysis requests

Both methods yield SSE events compatible with the frontend.
"""

import json
import logging
import uuid
from typing import AsyncGenerator, Dict, Any, Optional

import httpx

from core.graph import GraphOrchestrator
from core.state import GraphState, SemanticInput, WorkingMemory, EmotionalContext

logger = logging.getLogger(__name__)


def load_chat_config():
    """Load chat configuration from database."""
    from chat_db import get_all_settings

    settings = get_all_settings()

    class ChatConfig:
        def __init__(self, settings):
            self.api_base = settings.get("llm.api_base", "https://api.openai.com/v1")
            self.api_key = settings.get("llm.api_key", "")
            self.model = settings.get("llm.model", "gpt-4o-mini")
            self.system_prompt = settings.get("llm.system_prompt", "你是一个友好的 AI 助手。")
            self.max_tokens = int(settings.get("llm.max_tokens", 1024))
            self.temperature = float(settings.get("llm.temperature", 0.7))

    return ChatConfig(settings)


class GraphRunner:
    """
    Adapter to run the cognitive graph and stream results to the frontend.
    Handles both text chat and image analysis workflows.
    """

    def __init__(self):
        self.config = load_chat_config()

    async def run(self, request) -> AsyncGenerator[str, None]:
        """
        Run the graph for a text chat request and yield SSE events.

        Args:
            request: ChatRequest with message and session_id

        Yields:
            SSE formatted event strings
        """
        from chat_db import add_message
        from ecs_handler import store_ecs_request

        session_id = request.session_id or str(uuid.uuid4())

        # Save user message to database
        if request.session_id:
            try:
                add_message(request.session_id, "user", request.message)
            except Exception as e:
                logger.error(f"Failed to save user message: {e}")

        # 1. Initialize State
        initial_state = GraphState(
            conversation_id=session_id,
            semantic_input=SemanticInput(
                text=request.message,
                raw_event=request.model_dump() if hasattr(request, 'model_dump') else {},
            ),
            working_memory=WorkingMemory(),
            emotional_context=EmotionalContext(),
        )

        # 2. Build and compile graph
        orchestrator = GraphOrchestrator(
            api_base=self.config.api_base,
            api_key=self.config.api_key,
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            entry_point="text",
        )
        workflow = orchestrator.build()
        app = workflow.compile()

        # 3. Stream Execution with increased recursion limit
        yield self._format_sse("status", {"status": "starting", "session_id": session_id})

        final_response = ""
        try:
            async for output in app.astream(initial_state, config={"recursion_limit": 50}):
                # output is a dict of {node_name: state_update}
                for node_name, update in output.items():
                    logger.info(f"[GraphRunner] Node {node_name} update keys: {list(update.keys()) if isinstance(update, dict) else type(update)}")

                    if not isinstance(update, dict):
                        continue

                    # Emit response text
                    if "response" in update and update["response"]:
                        final_response = update["response"]
                        yield self._format_sse("text", {"type": "text", "payload": {"content": update["response"]}})

                    # Emit emotion from EmotionNode
                    if "emotional_context" in update and node_name == "emotion":
                        em = update["emotional_context"]
                        if hasattr(em, 'current_emotion'):
                            yield self._format_sse("emotion", {
                                "type": "emotion",
                                "payload": {
                                    "primary": em.current_emotion,
                                    "category": getattr(em, 'category', 'neutral'),
                                    "confidence": em.arousal,
                                }
                            })

                    # Emit detected emotion from ReasoningNode
                    if "detected_emotion" in update:
                        em = update["detected_emotion"]
                        yield self._format_sse("emotion", {
                            "type": "emotion",
                            "payload": em,
                        })

                    # Emit ECS request
                    if "ecs_request" in update and update["ecs_request"]:
                        ecs_req = update.get("ecs_full_request")
                        if ecs_req:
                            # Store ECS request
                            try:
                                store_ecs_request(ecs_req, session_id)
                            except Exception as e:
                                logger.error(f"Failed to store ECS request: {e}")

                            # Format ECS payload for frontend
                            ecs_payload = self._format_ecs_payload(ecs_req, session_id)
                            yield self._format_sse("ecs", {"type": "ecs", "payload": ecs_payload})

                    # Emit tool result
                    if "observation" in update and update["observation"] and node_name == "tools":
                        yield self._format_sse("tool_result", {
                            "type": "tool_result",
                            "payload": {"result": update["observation"]},
                        })

                    # Emit memory saved event
                    if "memories_to_store" in update and update["memories_to_store"]:
                        memory_payload = {
                            "count": len(update["memories_to_store"]),
                            "entries": update["memories_to_store"],
                        }
                        yield self._format_sse("memory_saved", {"type": "memory_saved", "payload": memory_payload})

            # Save assistant response to database
            if request.session_id and final_response:
                try:
                    add_message(request.session_id, "assistant", final_response)
                except Exception as e:
                    logger.error(f"Failed to save assistant message: {e}")

            yield self._format_sse("done", {"type": "done"})

        except Exception as e:
            logger.error(f"Graph execution failed: {e}", exc_info=True)
            yield self._format_sse("error", {"type": "error", "payload": {"message": str(e)}})

    async def run_image(self, request) -> AsyncGenerator[str, None]:
        """
        Run the graph for an image analysis request and yield SSE events.

        Args:
            request: ImageChatRequest with image data and action

        Yields:
            SSE formatted event strings
        """
        from ecs_handler import store_ecs_request

        session_id = request.session_id or str(uuid.uuid4())

        # 1. Initialize State with image data
        initial_state = GraphState(
            conversation_id=session_id,
            semantic_input=SemanticInput(
                images=[request.image],
                image_action=request.action,
                raw_event=request.model_dump() if hasattr(request, 'model_dump') else {},
            ),
            working_memory=WorkingMemory(),
            emotional_context=EmotionalContext(),
        )

        # 2. Build and compile image graph
        orchestrator = GraphOrchestrator(
            api_base=self.config.api_base,
            api_key=self.config.api_key,
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            entry_point="image",
        )
        workflow = orchestrator.build()
        app = workflow.compile()

        # 3. Stream Execution with increased recursion limit
        yield self._format_sse("status", {"status": "starting", "session_id": session_id})

        try:
            async for output in app.astream(initial_state, config={"recursion_limit": 50}):
                for node_name, update in output.items():
                    logger.info(f"[GraphRunner Image] Node {node_name} update keys: {list(update.keys()) if isinstance(update, dict) else type(update)}")

                    if not isinstance(update, dict):
                        continue

                    # Emit OCR result text
                    if "response" in update and update["response"]:
                        yield self._format_sse("text", {"type": "text", "payload": {"content": update["response"]}})

                    # Emit ECS request for memory confirmation
                    if "ecs_request" in update and update["ecs_request"]:
                        ecs_req = update.get("ecs_full_request")
                        if ecs_req:
                            # Store ECS request
                            try:
                                store_ecs_request(ecs_req, session_id)
                            except Exception as e:
                                logger.error(f"Failed to store ECS request: {e}")

                            # Format ECS payload
                            ecs_payload = self._format_ecs_payload(ecs_req, session_id)
                            yield self._format_sse("ecs", {"type": "ecs", "payload": ecs_payload})

            yield self._format_sse("done", {"type": "done"})

        except Exception as e:
            logger.error(f"Image graph execution failed: {e}", exc_info=True)
            yield self._format_sse("error", {"type": "error", "payload": {"message": f"图片分析失败: {str(e)}"}})

    async def resume(self, request) -> AsyncGenerator[str, None]:
        """
        Resume graph execution after ECS form submission.

        Args:
            request: ECSContinueRequest with session_id and continuation_data

        Yields:
            SSE formatted event strings
        """
        from chat_db import add_message
        from ecs_handler import store_ecs_request, build_continuation_context
        from ecs_schema import ECSContinuationData, ECSDisplayRequest

        session_id = request.session_id

        # Build continuation context from the ECS response data
        continuation_data = ECSContinuationData(
            request_title=request.continuation_data.request_title,
            action=request.continuation_data.action,
            form_data=request.continuation_data.form_data,
            field_labels=request.continuation_data.field_labels,
        )

        ecs_context = build_continuation_context(continuation_data)
        logger.info(f"[GraphRunner Resume] ECS context built: length={len(ecs_context)}")

        # 1. Initialize State with ECS continuation as input
        initial_state = GraphState(
            conversation_id=session_id,
            semantic_input=SemanticInput(
                text=f"请根据我刚才提交的表单信息给出回复。\n\n{ecs_context}",
                raw_event=request.model_dump() if hasattr(request, 'model_dump') else {},
            ),
            working_memory=WorkingMemory(),
            emotional_context=EmotionalContext(),
            last_human_input={
                "action": continuation_data.action,
                "form_data": continuation_data.form_data,
                "field_labels": continuation_data.field_labels,
            },
        )

        # 2. Build and compile graph (skip intent node for continuation)
        orchestrator = GraphOrchestrator(
            api_base=self.config.api_base,
            api_key=self.config.api_key,
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            entry_point="text",
        )
        workflow = orchestrator.build()
        app = workflow.compile()

        # 3. Stream Execution with increased recursion limit
        yield self._format_sse("status", {"status": "resuming", "session_id": session_id})

        final_response = ""
        try:
            async for output in app.astream(initial_state, config={"recursion_limit": 50}):
                for node_name, update in output.items():
                    logger.info(f"[GraphRunner Resume] Node {node_name} update keys: {list(update.keys()) if isinstance(update, dict) else type(update)}")

                    if not isinstance(update, dict):
                        continue

                    # Emit response text
                    if "response" in update and update["response"]:
                        final_response = update["response"]
                        yield self._format_sse("text", {"type": "text", "payload": {"content": update["response"]}})

                    # Emit emotion
                    if "detected_emotion" in update:
                        em = update["detected_emotion"]
                        yield self._format_sse("emotion", {
                            "type": "emotion",
                            "payload": em,
                        })

                    # Emit chained ECS request
                    if "ecs_request" in update and update["ecs_request"]:
                        ecs_req = update.get("ecs_full_request")
                        if ecs_req:
                            # Store ECS request
                            try:
                                store_ecs_request(ecs_req, session_id)
                            except Exception as e:
                                logger.error(f"Failed to store ECS request: {e}")

                            # Format ECS payload for frontend
                            ecs_payload = self._format_ecs_payload(ecs_req, session_id)
                            yield self._format_sse("ecs", {"type": "ecs", "payload": ecs_payload})

                    # Emit tool result
                    if "observation" in update and update["observation"] and node_name == "tools":
                        yield self._format_sse("tool_result", {
                            "type": "tool_result",
                            "payload": {"result": update["observation"]},
                        })

                    # Emit memory saved event
                    if "memories_to_store" in update and update["memories_to_store"]:
                        memory_payload = {
                            "count": len(update["memories_to_store"]),
                            "entries": update["memories_to_store"],
                        }
                        yield self._format_sse("memory_saved", {"type": "memory_saved", "payload": memory_payload})

            # Save assistant response to database
            if final_response:
                try:
                    add_message(session_id, "assistant", final_response)
                except Exception as e:
                    logger.error(f"Failed to save assistant message: {e}")

            yield self._format_sse("done", {"type": "done"})

        except Exception as e:
            logger.error(f"Resume failed: {e}", exc_info=True)
            yield self._format_sse("error", {"type": "error", "payload": {"message": str(e)}})

    def _format_sse(self, event: str, data: dict) -> str:
        """Format an SSE event string."""
        return f'event: {event}\ndata: {json.dumps(data)}\n\n'

    def _format_ecs_payload(self, ecs_req, session_id: str) -> Dict[str, Any]:
        """Format ECS request for frontend SSE payload."""
        # Handle both dict and object formats
        if isinstance(ecs_req, dict):
            ecs_type = ecs_req.get("type", "form")
            if ecs_type == "visual_display":
                # Visual display type
                payload = {
                    "id": ecs_req.get("id"),
                    "type": "visual_display",
                    "title": ecs_req.get("title"),
                    "description": ecs_req.get("description"),
                    "displays": ecs_req.get("displays", []),
                    "dismiss_label": ecs_req.get("dismiss_label", "关闭"),
                    "session_id": session_id,
                }
            else:
                # Form type
                payload = {
                    "id": ecs_req.get("id"),
                    "type": ecs_req.get("type"),
                    "title": ecs_req.get("title"),
                    "description": ecs_req.get("description"),
                    "fields": ecs_req.get("fields", []),
                    "actions": ecs_req.get("actions", {}),
                    "session_id": session_id,
                }
        else:
            # Object with attributes
            ecs_type = getattr(ecs_req, 'type', 'form')

            if ecs_type == "visual_display":
                # Visual display type - format displays
                displays = []
                if hasattr(ecs_req, 'displays'):
                    for d in ecs_req.displays:
                        displays.append({
                            "type": d.type.value if hasattr(d.type, 'value') else str(d.type),
                            "data": d.data,
                        })

                payload = {
                    "id": ecs_req.id,
                    "type": "visual_display",
                    "title": ecs_req.title,
                    "description": getattr(ecs_req, 'description', ''),
                    "displays": displays,
                    "dismiss_label": getattr(ecs_req, 'dismiss_label', '关闭'),
                    "session_id": session_id,
                }
            else:
                # Form type - format fields and actions
                fields = []
                if hasattr(ecs_req, 'fields'):
                    for f in ecs_req.fields:
                        field_dict = {
                            "name": f.name,
                            "type": f.type.value if hasattr(f.type, 'value') else str(f.type),
                            "label": f.label,
                            "required": f.required,
                            "placeholder": getattr(f, 'placeholder', None),
                            "default": getattr(f, 'default', None),
                        }
                        if hasattr(f, 'options') and f.options:
                            field_dict["options"] = [{"value": o.value, "label": o.label} for o in f.options]
                        fields.append(field_dict)

                actions = {}
                if hasattr(ecs_req, 'actions'):
                    actions = {
                        "approve": {
                            "label": ecs_req.actions.approve.label,
                            "style": ecs_req.actions.approve.style.value if hasattr(ecs_req.actions.approve.style, 'value') else str(ecs_req.actions.approve.style),
                        },
                        "edit": {
                            "label": ecs_req.actions.edit.label,
                            "style": ecs_req.actions.edit.style.value if hasattr(ecs_req.actions.edit.style, 'value') else str(ecs_req.actions.edit.style),
                        },
                        "reject": {
                            "label": ecs_req.actions.reject.label,
                            "style": ecs_req.actions.reject.style.value if hasattr(ecs_req.actions.reject.style, 'value') else str(ecs_req.actions.reject.style),
                        },
                    }

                payload = {
                    "id": ecs_req.id,
                    "type": ecs_req.type,
                    "title": ecs_req.title,
                    "description": getattr(ecs_req, 'description', ''),
                    "fields": fields,
                    "actions": actions,
                    "session_id": session_id,
                }

        return payload

    def _load_checkpoint(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load checkpoint from database."""
        from chat_db import get_connection

        try:
            with get_connection() as conn:
                cursor = conn.execute(
                    "SELECT state_json FROM graph_checkpoints WHERE session_id = ?",
                    (session_id,)
                )
                row = cursor.fetchone()
                if row:
                    return json.loads(row[0])
        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}")
        return None

    def _save_checkpoint(self, session_id: str, state: GraphState) -> None:
        """Save checkpoint to database."""
        from chat_db import get_connection

        try:
            state_json = state.model_dump_json()
            with get_connection() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO graph_checkpoints (session_id, state_json, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                """, (session_id, state_json))
                conn.commit()
                logger.info(f"[GraphRunner] Saved checkpoint for session {session_id}")
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")

    def _delete_checkpoint(self, session_id: str) -> None:
        """Delete checkpoint from database."""
        from chat_db import get_connection

        try:
            with get_connection() as conn:
                conn.execute(
                    "DELETE FROM graph_checkpoints WHERE session_id = ?",
                    (session_id,)
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to delete checkpoint: {e}")
