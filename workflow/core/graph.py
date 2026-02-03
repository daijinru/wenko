from typing import Any
from langgraph.graph import StateGraph, END
from workflow.core.state import GraphState
from workflow.core.nodes.emotion import EmotionNode
from workflow.core.nodes.memory import MemoryNode
from workflow.core.nodes.reasoning import ReasoningNode
from workflow.core.nodes.tool_node import ToolNode
from workflow.core.nodes.hitl import HITLNode

class GraphOrchestrator:
    def __init__(self, llm_client: Any, model: str):
        self.emotion_node = EmotionNode()
        self.memory_node = MemoryNode()
        self.reasoning_node = ReasoningNode(llm_client, model)
        self.tool_node = ToolNode()
        self.hitl_node = HITLNode()

    def build(self) -> StateGraph:
        workflow = StateGraph(GraphState)

        # Add Nodes
        workflow.add_node("emotion", self.emotion_node.compute)
        workflow.add_node("memory", self.memory_node.recall) # Recall at start
        workflow.add_node("reasoning", self.reasoning_node.compute)
        workflow.add_node("tools", self.tool_node.execute)
        workflow.add_node("hitl", self.hitl_node.execute)

        # Define Edges
        # Start -> Emotion -> Memory -> Reasoning
        workflow.set_entry_point("emotion")
        workflow.add_edge("emotion", "memory")
        workflow.add_edge("memory", "reasoning")

        # Conditional Edges from Reasoning
        def route_reasoning(state: GraphState):
            if state.pending_tool_calls:
                return "tools"
            if state.hitl_request:
                return "hitl"
            return END

        workflow.add_conditional_edges(
            "reasoning",
            route_reasoning,
            {
                "tools": "tools",
                "hitl": "hitl",
                END: END
            }
        )

        # From Tools -> Reasoning (Re-evaluate with observation)
        workflow.add_edge("tools", "reasoning")

        # From HITL -> END (Wait for resume)
        # When resumed, we probably want to go back to Reasoning or a specific Resume node.
        # If we just END here with status=suspended, the runner handles the pause.
        # Upon resume, we need to decide where to go.
        # For now, let's say HITL ends the turn, and next input (human response) restarts the graph?
        # Or we use LangGraph's interrupt feature.
        # If we use interrupt, the node execution halts.

        # Let's map HITL to END for now, assuming the runner stops when it sees "suspended" status or we use explicit interrupt in the future.
        workflow.add_edge("hitl", END)

        return workflow
