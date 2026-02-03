import json
import logging
import uuid
from typing import AsyncGenerator, Dict, Any, Optional
import httpx

from workflow.core.graph import GraphOrchestrator
from workflow.core.state import GraphState, SemanticInput, WorkingMemory, EmotionalContext
from workflow.main import ChatRequest, load_chat_config, ChatConfig

logger = logging.getLogger(__name__)

class GraphRunner:
    """
    Adapter to run the cognitive graph and stream results to the frontend.
    """

    def __init__(self):
        self.config = load_chat_config()

    async def run(self, request: ChatRequest) -> AsyncGenerator[str, None]:
        """
        Run the graph for a chat request and yield SSE events.
        """
        session_id = request.session_id or str(uuid.uuid4())

        # 1. Initialize State
        # In a real app, we would load existing state from a checkpoint/DB
        initial_state = GraphState(
            conversation_id=session_id,
            semantic_input=SemanticInput(
                text=request.message,
                raw_event=request.model_dump()
            ),
            # We should load working memory from DB here
            working_memory=WorkingMemory(),
            emotional_context=EmotionalContext()
        )

        # 2. Setup Dependencies
        # We pass a simple client wrapper or just configuration
        # For this PoC, ReasoningNode handles the call internally or we pass the client.
        # Let's pass the config and let ReasoningNode create ephemeral client or use a shared one.
        # But ReasoningNode expects llm_client.

        # We can pass an object that has .chat.completions.create compatible interface
        # or just pass the config and let ReasoningNode handle it.
        # Let's update ReasoningNode to accept config or a provider.
        # For now, I'll pass None and assume ReasoningNode mocks it or I update ReasoningNode to use httpx directly if I modified it.
        # I wrote ReasoningNode to use self.llm_client but implemented a mock _call_llm.

        orchestrator = GraphOrchestrator(llm_client=None, model=self.config.model)
        workflow = orchestrator.build()
        app = workflow.compile()

        # 3. Stream Execution
        yield f'event: status\ndata: {json.dumps({"status": "starting", "session_id": session_id})}\n\n'

        try:
            async for output in app.astream(initial_state):
                # output is a dict of {node_name: state_update}
                for node_name, update in output.items():
                    logger.info(f"Node {node_name} update: {update.keys()}")

                    # Map graph updates to frontend events
                    if "response" in update:
                        # If ReasoningNode outputted a response (I need to ensure it does)
                        yield f'event: text\ndata: {json.dumps({"type": "text", "payload": {"content": update["response"]}})}\n\n'

                    if "emotional_context" in update and node_name == "emotion":
                        em = update["emotional_context"]
                        yield f'event: emotion\ndata: {json.dumps({"type": "emotion", "payload": {"primary": em.current_emotion, "confidence": em.arousal}})}\n\n'

                    if "hitl_request" in update and update["hitl_request"]:
                        # Serialize HITL request
                        req = update["hitl_request"]
                        yield f'event: hitl\ndata: {json.dumps({"type": "hitl", "payload": req.model_dump()})}\n\n'

            yield f'event: done\ndata: {json.dumps({"type": "done"})}\n\n'

        except Exception as e:
            logger.error(f"Graph execution failed: {e}")
            yield f'event: error\ndata: {json.dumps({"type": "error", "payload": {"message": str(e)}})}\n\n'
