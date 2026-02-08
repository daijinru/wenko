import logging
import json
from typing import Dict, Any, List
from core.state import GraphState
from mcp_tool_executor import execute_mcp_tool, ToolCallResult

logger = logging.getLogger(f"workflow.{__name__}")

class ToolNode:
    """
    Node responsible for executing MCP tool calls.
    """

    async def execute(self, state: GraphState) -> Dict[str, Any]:
        """
        Execute pending tool calls and return observations.
        """
        tool_calls = state.pending_tool_calls
        if not tool_calls:
            return {"observation": None}

        observations = []

        for call in tool_calls:
            service_name = call.get("service")
            method = call.get("method")
            args = call.get("args", {})

            # If service name is not explicit, we might need to resolve it.
            # Assuming ReasoningNode provides service name for now.
            if not service_name:
                observations.append(f"Error: Service name missing for tool {method}")
                continue

            try:
                result: ToolCallResult = await execute_mcp_tool(
                    service_name=service_name,
                    method=method,
                    arguments=args
                )

                if result.success:
                    observations.append(f"Tool {method} output: {result.result}")
                else:
                    observations.append(f"Tool {method} failed: {result.error}")

            except Exception as e:
                logger.error(f"Tool execution exception: {e}")
                observations.append(f"Tool {method} system error: {str(e)}")

        # Combine observations
        combined_observation = "\n\n".join(observations)

        # Clear pending calls and set observation
        return {
            "pending_tool_calls": [],
            "observation": combined_observation
        }
