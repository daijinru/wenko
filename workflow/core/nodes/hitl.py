from typing import Dict, Any
from workflow.core.state import GraphState

class HITLNode:
    """
    Node representing a Human-in-the-Loop interaction point.
    Execution reaches here when the system needs human input.
    """

    async def execute(self, state: GraphState) -> Dict[str, Any]:
        """
        Prepare for suspension.
        """
        if not state.hitl_request:
             # If we ended up here without a request, it's an error or we should just resume/skip
             return {"status": "processing"}

        # We ensure status is suspended.
        # The Graph Runner/Orchestrator should detect this state and pause execution,
        # persisting the state/checkpoint.
        return {"status": "suspended"}
