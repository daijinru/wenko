import logging
from typing import Dict, Any, List
from workflow.core.state import GraphState, MemoryRef
import workflow.memory_manager as mm

logger = logging.getLogger(__name__)

class MemoryNode:
    """
    Node responsible for Long-term Memory interactions (Recall & Consolidate).
    """

    async def recall(self, state: GraphState) -> Dict[str, Any]:
        """
        Retrieve relevant long-term memories based on current input and context.
        Updates state.working_memory.retrieved_memories.
        """
        user_text = state.semantic_input.text
        if not user_text:
            return {}

        # Use existing memory manager retrieval
        # We need to map WorkingMemory from state to memory_manager.WorkingMemory if needed
        # But retrieve_relevant_memories mainly needs user_message and optional working_memory object

        # Convert state.working_memory (Pydantic) to dict or expected object if necessary
        # memory_manager expects an object with current_topic.
        # Let's create a simple object or mock if needed, or just pass None for now as we might not have full context synchronization yet.

        # We can extract session_id from state
        session_id = state.conversation_id

        # Retrieve memories
        results = mm.retrieve_relevant_memories(
            user_message=user_text,
            working_memory=None, # We'll improve context passing later
            limit=5
        )

        # Convert results to MemoryRef
        memory_refs = []
        for res in results:
            mem = res.memory
            memory_refs.append(MemoryRef(
                id=mem.id,
                content=str(mem.value),
                type=mem.category,
                confidence=mem.confidence
            ))

        # Update working memory in state
        # Note: In LangGraph, we typically return the diff/update.
        # Here we return the updated working_memory object.
        state.working_memory.retrieved_memories = memory_refs

        # Also update access stats asynchronously (or synchronously here for simplicity)
        mm.update_memory_access([m.id for m in memory_refs])

        return {"working_memory": state.working_memory}

    async def consolidate(self, state: GraphState) -> Dict[str, Any]:
        """
        Save new memories extracted during the turn.
        Expected to be called with specific instructions or automatically based on intent.
        """
        # This logic depends on how we extract information to save.
        # If the SemanticInput has 'intent' of type 'memory' (preference, fact, etc.), we can save it.
        # Or if ReasoningNode produced a tool call to 'save_memory'.

        # For now, let's support saving based on SemanticInput intent if it matches memory categories
        # logic similar to chat_processor.py's handling of intents

        input_data = state.semantic_input
        if input_data.intent:
            category = None
            if input_data.intent in ["preference", "fact", "pattern"]:
                category = input_data.intent

            if category:
                # We need to extract key/value. This usually requires LLM extraction.
                # If InputNormalization or Reasoning didn't extract structured data, we can't save effectively here.
                # So Consolidate might be better as a Tool or invoked after Reasoning.
                pass

        return {}
