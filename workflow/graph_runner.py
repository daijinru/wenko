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
        from hitl_handler import store_hitl_request

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

        # 3. Stream Execution
        yield self._format_sse("status", {"status": "starting", "session_id": session_id})

        final_response = ""
        try:
            async for output in app.astream(initial_state):
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

                    # Emit HITL request
                    if "hitl_request" in update and update["hitl_request"]:
                        hitl_req = update.get("hitl_full_request")
                        if hitl_req:
                            # Store HITL request
                            try:
                                store_hitl_request(hitl_req, session_id)
                            except Exception as e:
                                logger.error(f"Failed to store HITL request: {e}")

                            # Format HITL payload for frontend
                            hitl_payload = self._format_hitl_payload(hitl_req, session_id)
                            yield self._format_sse("hitl", {"type": "hitl", "payload": hitl_payload})

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
        from hitl_handler import store_hitl_request

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

        # 3. Stream Execution
        yield self._format_sse("status", {"status": "starting", "session_id": session_id})

        try:
            async for output in app.astream(initial_state):
                for node_name, update in output.items():
                    logger.info(f"[GraphRunner Image] Node {node_name} update keys: {list(update.keys()) if isinstance(update, dict) else type(update)}")

                    if not isinstance(update, dict):
                        continue

                    # Emit OCR result text
                    if "response" in update and update["response"]:
                        yield self._format_sse("text", {"type": "text", "payload": {"content": update["response"]}})

                    # Emit HITL request for memory confirmation
                    if "hitl_request" in update and update["hitl_request"]:
                        hitl_req = update.get("hitl_full_request")
                        if hitl_req:
                            # Store HITL request
                            try:
                                store_hitl_request(hitl_req, session_id)
                            except Exception as e:
                                logger.error(f"Failed to store HITL request: {e}")

                            # Format HITL payload
                            hitl_payload = self._format_hitl_payload(hitl_req, session_id)
                            yield self._format_sse("hitl", {"type": "hitl", "payload": hitl_payload})

            yield self._format_sse("done", {"type": "done"})

        except Exception as e:
            logger.error(f"Image graph execution failed: {e}", exc_info=True)
            yield self._format_sse("error", {"type": "error", "payload": {"message": f"图片分析失败: {str(e)}"}})

    async def resume(self, session_id: str, hitl_response: Dict[str, Any]) -> AsyncGenerator[str, None]:
        """
        Resume graph execution after HITL response.

        Args:
            session_id: Session ID to resume
            hitl_response: User's response to HITL form

        Yields:
            SSE formatted event strings
        """
        # Load checkpoint
        checkpoint = self._load_checkpoint(session_id)
        if not checkpoint:
            yield self._format_sse("error", {
                "type": "error",
                "payload": {"message": "Checkpoint not found for session"}
            })
            return

        # Inject HITL response into state
        checkpoint["last_human_input"] = hitl_response
        checkpoint["status"] = "processing"
        checkpoint["hitl_request"] = None

        # Rebuild state
        state = GraphState(**checkpoint)

        # Build graph and continue from reasoning
        orchestrator = GraphOrchestrator(
            api_base=self.config.api_base,
            api_key=self.config.api_key,
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            entry_point="text",
        )

        # For resume, we re-run from reasoning with the new context
        # This is a simplified approach - full implementation would use LangGraph checkpoints
        workflow = orchestrator.build()
        app = workflow.compile()

        yield self._format_sse("status", {"status": "resuming", "session_id": session_id})

        try:
            async for output in app.astream(state):
                for node_name, update in output.items():
                    if not isinstance(update, dict):
                        continue

                    if "response" in update and update["response"]:
                        yield self._format_sse("text", {"type": "text", "payload": {"content": update["response"]}})

            # Delete checkpoint after successful resume
            self._delete_checkpoint(session_id)

            yield self._format_sse("done", {"type": "done"})

        except Exception as e:
            logger.error(f"Resume failed: {e}", exc_info=True)
            yield self._format_sse("error", {"type": "error", "payload": {"message": str(e)}})

    def _format_sse(self, event: str, data: dict) -> str:
        """Format an SSE event string."""
        return f'event: {event}\ndata: {json.dumps(data)}\n\n'

    def _format_hitl_payload(self, hitl_req, session_id: str) -> Dict[str, Any]:
        """Format HITL request for frontend SSE payload."""
        # Handle both dict and object formats
        if isinstance(hitl_req, dict):
            payload = {
                "id": hitl_req.get("id"),
                "type": hitl_req.get("type"),
                "title": hitl_req.get("title"),
                "description": hitl_req.get("description"),
                "fields": hitl_req.get("fields", []),
                "actions": hitl_req.get("actions", {}),
                "session_id": session_id,
            }
        else:
            # Object with attributes
            fields = []
            if hasattr(hitl_req, 'fields'):
                for f in hitl_req.fields:
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
            if hasattr(hitl_req, 'actions'):
                actions = {
                    "approve": {
                        "label": hitl_req.actions.approve.label,
                        "style": hitl_req.actions.approve.style.value if hasattr(hitl_req.actions.approve.style, 'value') else str(hitl_req.actions.approve.style),
                    },
                    "edit": {
                        "label": hitl_req.actions.edit.label,
                        "style": hitl_req.actions.edit.style.value if hasattr(hitl_req.actions.edit.style, 'value') else str(hitl_req.actions.edit.style),
                    },
                    "reject": {
                        "label": hitl_req.actions.reject.label,
                        "style": hitl_req.actions.reject.style.value if hasattr(hitl_req.actions.reject.style, 'value') else str(hitl_req.actions.reject.style),
                    },
                }

            payload = {
                "id": hitl_req.id,
                "type": hitl_req.type,
                "title": hitl_req.title,
                "description": getattr(hitl_req, 'description', ''),
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
