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

        print(f"[MCP Executor] Getting available tools from {len(running_servers)} running servers")

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
            print(f"[MCP Executor] Found tool: name={server.name}, description={desc[:50]}...")

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
            print(f"[MCP Executor] Service not found for description: name={service_name}")
            return None

        desc = info.description or f"MCP service: {service_name}"
        result = f"[工具] {service_name}: {desc}"
        print(f"[MCP Executor] Tool description level1: {result}")
        return result

    def get_all_tools_description_level1(self) -> str:
        """Get Level 1 descriptions for all available tools.

        Returns:
            Combined description string for all tools
        """
        tools = self.get_available_tools()
        if not tools:
            print("[MCP Executor] No available tools for description")
            return ""

        lines = ["【可用 MCP 工具】"]
        for tool in tools:
            lines.append(f"- {tool.name}: {tool.description}")
        result = "\n".join(lines)
        print(f"[MCP Executor] All tools description: {len(tools)} tools, {len(result)} chars")
        return result

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
                print(f"[MCP Executor] Found service: name={name}, id={server.id}, pid={server.pid}")
                return server
        print(f"[MCP Executor] Service not found: name={name}")
        return None

    def is_service_available(self, service_name: str) -> bool:
        """Check if a service is available (running).

        Args:
            service_name: Name of the service to check

        Returns:
            True if service is running, False otherwise
        """
        available = self._find_service_by_name(service_name) is not None
        print(f"[MCP Executor] Service availability check: name={service_name}, available={available}")
        return available

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

        # Build JSON-RPC request using MCP protocol tools/call method
        request_id = str(uuid.uuid4())
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tools/call",
            "params": {
                "name": method,
                "arguments": arguments or {},
            },
        }
        print(f"[MCP Executor] JSON-RPC request: id={request_id}, method=tools/call, tool={method}, args={arguments}")

        try:
            # Send request via stdin
            request_json = json.dumps(request) + "\n"
            print(f"[MCP Executor] Sending request to stdin: {len(request_json)} bytes")
            proc.stdin.write(request_json.encode())
            proc.stdin.flush()
            print(f"[MCP Executor] Request sent, waiting for response (timeout={self.timeout}s)")

            # Read response with timeout
            try:
                response_line = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        None, proc.stdout.readline
                    ),
                    timeout=self.timeout,
                )
            except asyncio.TimeoutError:
                print(f"[MCP Executor] Timeout after {self.timeout}s waiting for response")
                return ToolCallResult(
                    success=False,
                    tool_name=method,
                    service_name=service_name,
                    error=f"Tool call timed out after {self.timeout}s",
                )

            if not response_line:
                print(f"[MCP Executor] Empty response from service")
                return ToolCallResult(
                    success=False,
                    tool_name=method,
                    service_name=service_name,
                    error="No response from MCP service",
                )

            # Parse JSON-RPC response
            print(f"[MCP Executor] Received response: {len(response_line)} bytes")
            response = json.loads(response_line.decode())

            if "error" in response:
                error_msg = response["error"].get("message", "Unknown error")
                print(f"[MCP Executor] JSON-RPC error: {error_msg}")
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
            print(f"[MCP Executor] JSON decode error: {e}")
            return ToolCallResult(
                success=False,
                tool_name=method,
                service_name=service_name,
                error=f"Invalid JSON response: {e}",
            )
        except Exception as e:
            print(f"[MCP Executor] Execution exception: {e}")
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
        print(f"[MCP Executor] Creating global executor with timeout={timeout}s")
        _executor = MCPToolExecutor(timeout=timeout)
    return _executor


def get_available_mcp_tools() -> List[ToolDescription]:
    """Convenience function to get available tools.

    Returns:
        List of ToolDescription for available tools
    """
    print("[MCP] get_available_mcp_tools() called")
    return get_executor().get_available_tools()


def get_mcp_tools_prompt_snippet() -> str:
    """Get prompt snippet describing available MCP tools.

    Returns:
        Prompt snippet string, empty if no tools available
    """
    print("[MCP] get_mcp_tools_prompt_snippet() called")
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
    print(f"[MCP] execute_mcp_tool() called: service={service_name}, method={method}, args={arguments}")
    executor = get_executor(timeout)
    return await executor.execute_tool(service_name, method, arguments)
