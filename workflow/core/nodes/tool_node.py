import logging
import json
from typing import Dict, Any, List
from core.state import GraphState, ExecutionStatus, ExecutionStep
from mcp_tool_executor import execute_mcp_tool, ToolCallResult

logger = logging.getLogger(f"workflow.{__name__}")

class ToolNode:
    """
    Node responsible for executing MCP tool calls.
    Advances ExecutionContract state and maintains backward-compatible observation output.
    """

    async def execute(self, state: GraphState) -> Dict[str, Any]:
        """
        Execute pending tool calls, advance contract states, and return observations.
        """
        tool_calls = state.pending_tool_calls
        contracts = list(state.pending_executions)
        if not tool_calls and not contracts:
            return {"observation": None}

        logger.info(f"[ToolNode] Executing: {len(tool_calls)} tool calls, {len(contracts)} contracts")

        observations = []
        completed = list(state.completed_executions)

        # Build a lookup from tool_calls to contracts for matching
        contract_map = {}
        for c in contracts:
            if c.action_type == "tool_call" and c.status == ExecutionStatus.PENDING:
                key = (c.action_detail.get("service"), c.action_detail.get("method"))
                contract_map.setdefault(key, []).append(c)

        for call in tool_calls:
            service_name = call.get("service")
            method = call.get("method")
            args = call.get("args", {})

            # Find matching contract
            matching = contract_map.get((service_name, method), [])
            contract = matching.pop(0) if matching else None

            if contract:
                logger.info(f"[ToolNode] Matched contract {contract.execution_id[:8]} for {service_name}.{method}")
            else:
                logger.debug(f"[ToolNode] No contract for {service_name}.{method} (legacy mode)")

            if not service_name:
                obs = f"Error: Service name missing for tool {method}"
                observations.append(obs)
                if contract:
                    contract.transition("start", actor="tool_node")
                    contract.transition("fail", actor="tool_node")
                    contract.error_message = obs
                    self._record_trace(state, contract)
                    completed.append(contract)
                continue

            try:
                # Advance contract: PENDING → RUNNING
                if contract:
                    contract.transition("start", actor="tool_node")

                logger.info(f"[ToolNode] Calling MCP: {service_name}.{method}")
                result: ToolCallResult = await execute_mcp_tool(
                    service_name=service_name,
                    method=method,
                    arguments=args
                )

                if result.success:
                    obs = f"Tool {method} output: {result.result}"
                    observations.append(obs)
                    if contract:
                        contract.transition("succeed", actor="tool_node")
                        contract.result = result.result
                        logger.info(f"[ToolNode] Contract {contract.execution_id[:8]} COMPLETED: {service_name}.{method}")
                else:
                    obs = f"Tool {method} failed: {result.error}"
                    observations.append(obs)
                    if contract:
                        contract.transition("fail", actor="tool_node")
                        contract.error_message = result.error
                        logger.warning(f"[ToolNode] Contract {contract.execution_id[:8]} FAILED: {service_name}.{method} - {result.error}")

            except Exception as e:
                logger.error(f"[ToolNode] Exception during {service_name}.{method}: {e}")
                obs = f"Tool {method} system error: {str(e)}"
                observations.append(obs)
                if contract:
                    if contract.status == ExecutionStatus.PENDING:
                        contract.transition("start", actor="tool_node")
                    contract.transition("fail", actor="tool_node")
                    contract.error_message = str(e)

            if contract:
                self._record_trace(state, contract)
                completed.append(contract)

        # Combine observations (backward compatible)
        combined_observation = "\n\n".join(observations)
        logger.info(f"[ToolNode] Done: {len(completed) - len(state.completed_executions)} contracts completed")

        return {
            "pending_tool_calls": [],
            "observation": combined_observation,
            "pending_executions": [],
            "completed_executions": completed,
        }

    def _record_trace(self, state: GraphState, contract) -> None:
        """Record contract transitions into execution_trace."""
        for t in contract.transitions:
            state.execution_trace.append(ExecutionStep(
                node_id="tool_node",
                action=f"transition:{contract.execution_id}:{t['from']}→{t['to']}",
                result=contract.result,
                metadata={
                    "trigger": t["trigger"],
                    "actor": t["actor"],
                    "contract_id": contract.execution_id,
                    "irreversible": contract.irreversible,
                },
            ))
