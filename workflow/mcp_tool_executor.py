"""MCP Tool Executor Module

Provides functionality to execute tools on running MCP servers.
Handles communication via stdio using JSON-RPC protocol.
"""

import asyncio
import json
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import mcp_manager
from mcp_manager import MCPServerInfo, MCPServerStatus


@dataclass
class ToolDescription:
    """Description of an MCP tool at different detail levels."""
    name: str
    service_name: str
    description: str  # Level 1: brief description
    # Level 2/3 can be extended when MCP provides tool schema


@dataclass
class ToolCallResult:
    """Result from executing an MCP tool."""
    success: bool
    tool_name: str
    service_name: str
    result: Optional[str] = None  # Tool output
    error: Optional[str] = None  # Error message if failed


class MCPToolExecutor:
    """Executor for MCP tool calls.

    Handles communication with running MCP servers and executes
    tool calls using the JSON-RPC protocol over stdio.
    """

    # Default timeout for tool calls (seconds)
    DEFAULT_TIMEOUT = 30.0

    def __init__(self, timeout: float = DEFAULT_TIMEOUT):
        """Initialize the executor.

        Args:
            timeout: Timeout for tool calls in seconds
        """
        self.timeout = timeout

    def get_available_tools(self) -> List[ToolDescription]:
        """Get list of tools from all running MCP servers.

        Returns:
            List of ToolDescription for available tools
        """
        pm = mcp_manager.get_process_manager()
        running_servers = pm.get_running_servers()

        tools = []
        for server in running_servers:
            # Create a tool description for each running server
            # The server itself is treated as a tool for now
            desc = server.description or f"MCP service: {server.name}"
            tools.append(ToolDescription(
                name=server.name,
                service_name=server.name,
                description=desc,
            ))

        return tools

    def get_tool_description_level1(self, service_name: str) -> Optional[str]:
        """Get Level 1 (brief) description for a tool/service.

        Args:
            service_name: Name of the MCP service

        Returns:
            Brief description string, or None if service not found
        """
        pm = mcp_manager.get_process_manager()
        info = self._find_service_by_name(service_name)
        if info is None:
            return None

        desc = info.description or f"MCP service: {service_name}"
        return f"[工具] {service_name}: {desc}"

    def get_all_tools_description_level1(self) -> str:
        """Get Level 1 descriptions for all available tools.

        Returns:
            Combined description string for all tools
        """
        tools = self.get_available_tools()
        if not tools:
            return ""

        lines = ["【可用 MCP 工具】"]
        for tool in tools:
            lines.append(f"- {tool.name}: {tool.description}")
        return "\n".join(lines)

    def _find_service_by_name(self, name: str) -> Optional[MCPServerInfo]:
        """Find a running service by name.

        Args:
            name: Service name to find

        Returns:
            MCPServerInfo if found and running, None otherwise
        """
        pm = mcp_manager.get_process_manager()
        for server in pm.get_running_servers():
            if server.name == name:
                return server
        return None

    def is_service_available(self, service_name: str) -> bool:
        """Check if a service is available (running).

        Args:
            service_name: Name of the service to check

        Returns:
            True if service is running, False otherwise
        """
        return self._find_service_by_name(service_name) is not None

    async def execute_tool(
        self,
        service_name: str,
        method: str,
        arguments: Optional[Dict[str, Any]] = None,
    ) -> ToolCallResult:
        """Execute a tool call on an MCP server.

        Args:
            service_name: Name of the MCP service
            method: Method/tool name to call
            arguments: Arguments to pass to the tool

        Returns:
            ToolCallResult with success status and result/error
        """
        print(f"[MCP] Executing tool: service={service_name}, method={method}")

        # Find the service
        service = self._find_service_by_name(service_name)
        if service is None:
            return ToolCallResult(
                success=False,
                tool_name=method,
                service_name=service_name,
                error=f"MCP service '{service_name}' is not running",
            )

        # Get the process
        pm = mcp_manager.get_process_manager()
        proc = pm.get_process(service.id)
        if proc is None:
            return ToolCallResult(
                success=False,
                tool_name=method,
                service_name=service_name,
                error=f"Cannot communicate with MCP service '{service_name}'",
            )

        # Build JSON-RPC request
        request_id = str(uuid.uuid4())
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": arguments or {},
        }

        try:
            # Send request via stdin
            request_json = json.dumps(request) + "\n"
            proc.stdin.write(request_json.encode())
            proc.stdin.flush()

            # Read response with timeout
            try:
                response_line = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        None, proc.stdout.readline
                    ),
                    timeout=self.timeout,
                )
            except asyncio.TimeoutError:
                return ToolCallResult(
                    success=False,
                    tool_name=method,
                    service_name=service_name,
                    error=f"Tool call timed out after {self.timeout}s",
                )

            if not response_line:
                return ToolCallResult(
                    success=False,
                    tool_name=method,
                    service_name=service_name,
                    error="No response from MCP service",
                )

            # Parse JSON-RPC response
            response = json.loads(response_line.decode())

            if "error" in response:
                error_msg = response["error"].get("message", "Unknown error")
                return ToolCallResult(
                    success=False,
                    tool_name=method,
                    service_name=service_name,
                    error=error_msg,
                )

            result = response.get("result", "")
            if isinstance(result, dict):
                result = json.dumps(result, ensure_ascii=False)
            elif not isinstance(result, str):
                result = str(result)

            print(f"[MCP] Tool execution successful: {method}")
            return ToolCallResult(
                success=True,
                tool_name=method,
                service_name=service_name,
                result=result,
            )

        except json.JSONDecodeError as e:
            return ToolCallResult(
                success=False,
                tool_name=method,
                service_name=service_name,
                error=f"Invalid JSON response: {e}",
            )
        except Exception as e:
            return ToolCallResult(
                success=False,
                tool_name=method,
                service_name=service_name,
                error=f"Tool execution failed: {str(e)}",
            )


# Global executor instance
_executor: Optional[MCPToolExecutor] = None


def get_executor(timeout: float = MCPToolExecutor.DEFAULT_TIMEOUT) -> MCPToolExecutor:
    """Get the global executor instance.

    Args:
        timeout: Timeout for tool calls

    Returns:
        MCPToolExecutor instance
    """
    global _executor
    if _executor is None:
        _executor = MCPToolExecutor(timeout=timeout)
    return _executor


def get_available_mcp_tools() -> List[ToolDescription]:
    """Convenience function to get available tools.

    Returns:
        List of ToolDescription for available tools
    """
    return get_executor().get_available_tools()


def get_mcp_tools_prompt_snippet() -> str:
    """Get prompt snippet describing available MCP tools.

    Returns:
        Prompt snippet string, empty if no tools available
    """
    return get_executor().get_all_tools_description_level1()


async def execute_mcp_tool(
    service_name: str,
    method: str,
    arguments: Optional[Dict[str, Any]] = None,
    timeout: float = MCPToolExecutor.DEFAULT_TIMEOUT,
) -> ToolCallResult:
    """Convenience function to execute an MCP tool.

    Args:
        service_name: Name of the MCP service
        method: Method/tool name to call
        arguments: Arguments to pass to the tool
        timeout: Timeout in seconds

    Returns:
        ToolCallResult with result or error
    """
    executor = get_executor(timeout)
    return await executor.execute_tool(service_name, method, arguments)
