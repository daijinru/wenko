"""GraphOrchestrator - Builds and configures the cognitive graph workflow.

Supports two entry points:
- Text chat: IntentNode → EmotionNode → MemoryNode → ReasoningNode → (Tools/ECS/END)
- Image chat: ImageNode → MemoryExtractionNode → (ECS/END)
"""

from typing import Any, Optional, Literal
from langgraph.graph import StateGraph, END
from core.state import GraphState
from core.nodes.emotion import EmotionNode
from core.nodes.memory import MemoryNode
from core.nodes.reasoning import ReasoningNode
from core.nodes.tool_node import ToolNode
from core.nodes.ecs import ECSNode
from core.nodes.intent import IntentNode


class GraphOrchestrator:
    """
    Orchestrates the cognitive graph workflow.

    Supports configurable entry points for different input types.
    """

    def __init__(
        self,
        api_base: str,
        api_key: str,
        model: str,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        entry_point: Literal["text", "image"] = "text",
    ):
        """
        Initialize the orchestrator with LLM configuration.

        Args:
            api_base: LLM API base URL
            api_key: API key for authentication
            model: Model name to use
            max_tokens: Maximum tokens for response
            temperature: Sampling temperature
            entry_point: Which flow to use ("text" or "image")
        """
        self.entry_point = entry_point

        # Initialize nodes
        self.intent_node = IntentNode(
            layer2_enabled=True,
            api_base=api_base,
            api_key=api_key,
            model=model,
        )
        self.emotion_node = EmotionNode()
        self.memory_node = MemoryNode()
        self.reasoning_node = ReasoningNode(
            api_base=api_base,
            api_key=api_key,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        self.tool_node = ToolNode()
        self.ecs_node = ECSNode()

        # Image nodes (lazy import to avoid circular deps)
        self._image_node = None
        self._memory_extraction_node = None

    def _get_image_node(self):
        """Lazy load ImageNode."""
        if self._image_node is None:
            from core.nodes.image import ImageNode
            self._image_node = ImageNode()
        return self._image_node

    def _get_memory_extraction_node(self):
        """Lazy load MemoryExtractionNode."""
        if self._memory_extraction_node is None:
            from core.nodes.image import MemoryExtractionNode
            self._memory_extraction_node = MemoryExtractionNode()
        return self._memory_extraction_node

    def build(self) -> StateGraph:
        """
        Build the state graph based on entry point.

        Returns:
            Configured StateGraph ready for compilation
        """
        if self.entry_point == "image":
            return self._build_image_graph()
        return self._build_text_graph()

    def _build_text_graph(self) -> StateGraph:
        """Build the text chat workflow graph."""
        workflow = StateGraph(GraphState)

        # Add Nodes
        workflow.add_node("intent", self._intent_wrapper)
        workflow.add_node("emotion", self.emotion_node.compute)
        workflow.add_node("memory", self.memory_node.recall)
        workflow.add_node("reasoning", self._reasoning_wrapper)
        workflow.add_node("tools", self.tool_node.execute)
        workflow.add_node("ecs", self.ecs_node.execute)

        # Define Edges: Intent -> Emotion -> Memory -> Reasoning
        workflow.set_entry_point("intent")
        workflow.add_edge("intent", "emotion")
        workflow.add_edge("emotion", "memory")
        workflow.add_edge("memory", "reasoning")

        # Conditional Edges from Reasoning
        def route_reasoning(state: GraphState):
            if state.pending_tool_calls:
                return "tools"
            if state.ecs_request:
                return "ecs"
            return END

        workflow.add_conditional_edges(
            "reasoning",
            route_reasoning,
            {
                "tools": "tools",
                "ecs": "ecs",
                END: END
            }
        )

        # From Tools -> Reasoning (Re-evaluate with observation)
        workflow.add_edge("tools", "reasoning")

        # From ECS -> END (suspend and wait for resume)
        workflow.add_edge("ecs", END)

        return workflow

    def _build_image_graph(self) -> StateGraph:
        """Build the image analysis workflow graph."""
        workflow = StateGraph(GraphState)

        # Get image-specific nodes
        image_node = self._get_image_node()
        memory_extraction_node = self._get_memory_extraction_node()

        # Add Nodes
        workflow.add_node("image", image_node.compute)
        workflow.add_node("memory_extraction", memory_extraction_node.compute)
        workflow.add_node("ecs", self.ecs_node.execute)

        # Define Edges: Image -> MemoryExtraction -> (ECS or END)
        workflow.set_entry_point("image")
        workflow.add_edge("image", "memory_extraction")

        # Conditional edge from memory extraction
        def route_memory_extraction(state: GraphState):
            if state.ecs_request:
                return "ecs"
            return END

        workflow.add_conditional_edges(
            "memory_extraction",
            route_memory_extraction,
            {
                "ecs": "ecs",
                END: END
            }
        )

        # ECS -> END
        workflow.add_edge("ecs", END)

        return workflow

    async def _intent_wrapper(self, state: GraphState):
        """
        Wrapper for IntentNode.compute that works with LangGraph.
        """
        return await self.intent_node.compute(state)

    async def _reasoning_wrapper(self, state: GraphState):
        """
        Wrapper for ReasoningNode.compute that works with LangGraph.

        LangGraph expects sync or async functions, but our compute method
        has optional parameters. This wrapper provides the interface.
        """
        return await self.reasoning_node.compute(state)
