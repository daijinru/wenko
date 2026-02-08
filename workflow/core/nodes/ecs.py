import logging
from typing import Dict, Any
from core.state import GraphState, ExecutionStatus, ExecutionStep

logger = logging.getLogger(f"workflow.{__name__}")

class ECSNode:
    """
    Node representing an Externalized Cognitive Step interaction point.
    Execution reaches here when the system needs external input.
    Advances ExecutionContract through PENDING → RUNNING → WAITING.
    """

    async def execute(self, state: GraphState) -> Dict[str, Any]:
        """
        Prepare for suspension by advancing contract state.
        """
        if not state.ecs_request:
            logger.debug("[ECSNode] No ecs_request in state, skipping")
            return {"status": "processing"}

        logger.info(f"[ECSNode] Processing ECS request: type={state.ecs_request.type}, pending_contracts={len(state.pending_executions)}")

        # Advance any pending ECS contracts to WAITING
        completed = list(state.completed_executions)
        remaining = []
        for contract in state.pending_executions:
            if contract.action_type == "ecs_request" and contract.status == ExecutionStatus.PENDING:
                logger.info(f"[ECSNode] Suspending contract {contract.execution_id[:8]}: PENDING → RUNNING → WAITING")
                contract.transition("start", actor="ecs_node")
                contract.transition("suspend", actor="ecs_node")
                self._record_trace(state, contract)
                completed.append(contract)
            else:
                remaining.append(contract)

        logger.info(f"[ECSNode] Suspended: {len(completed) - len(state.completed_executions)} contracts, remaining: {len(remaining)}")

        return {
            "status": "suspended",
            "pending_executions": remaining,
            "completed_executions": completed,
        }

    def _record_trace(self, state: GraphState, contract) -> None:
        """Record contract transitions into execution_trace."""
        for t in contract.transitions:
            state.execution_trace.append(ExecutionStep(
                node_id="ecs_node",
                action=f"transition:{contract.execution_id}:{t['from']}→{t['to']}",
                result=None,
                metadata={
                    "trigger": t["trigger"],
                    "actor": t["actor"],
                    "contract_id": contract.execution_id,
                    "irreversible": contract.irreversible,
                },
            ))
