import asyncio
import logging
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.graph import GraphOrchestrator
from core.state import GraphState, SemanticInput, WorkingMemory, EmotionalContext

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(f"workflow.{__name__}")

async def test_graph():
    logger.info("Starting Graph Verification...")

    # Mock LLM Client
    class MockResponse:
        def __init__(self, content):
            self.choices = [type('Choice', (), {'message': type('Message', (), {'content': content})})()]

    class MockCompletions:
        async def create(self, model, messages):
            # Return a JSON response as expected by ReasoningNode
            return MockResponse('{"response": "That is great to hear! I am glad you are feeling happy."}')

    class MockChat:
        def __init__(self):
            self.completions = MockCompletions()

    class MockLLM:
        def __init__(self):
            self.chat = MockChat()

    orchestrator = GraphOrchestrator(llm_client=MockLLM(), model="test-model")
    workflow = orchestrator.build()
    app = workflow.compile()

    # Initial State
    state = GraphState(
        conversation_id="test-session",
        semantic_input=SemanticInput(text="I am happy today"),
        working_memory=WorkingMemory(),
        emotional_context=EmotionalContext()
    )

    logger.info(f"Initial State: {state}")

    # Run
    async for output in app.astream(state):
        for node, update in output.items():
            if update is None:
                logger.error(f"Node '{node}' returned None!")
            else:
                logger.info(f"Node '{node}' executed. Update keys: {list(update.keys())}")
                if "emotional_context" in update:
                    logger.info(f"Emotion detected: {update['emotional_context'].current_emotion}")

    logger.info("Graph finished.")

if __name__ == "__main__":
    asyncio.run(test_graph())
