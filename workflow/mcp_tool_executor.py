"""MCP Tool Executor Module

Provides functionality to execute tools on running MCP servers.
Handles communication via stdio using JSON-RPC protocol.
"""

import asyncio
import json
import logging
import os
import select
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import mcp_manager

logger = logging.getLogger(f"workflow.{__name__}")
from mcp_manager import MCPServerInfo, MCPServerStatus


@dataclass
class MCPToolInfo:
    """Information about a specific tool from an MCP service."""
    name: str  # Tool name (method name to call)
    service_name: str  # Service that provides this tool
    description: str  # Tool description
    input_schema: Optional[Dict[str, Any]] = None  # JSON schema for input


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
        # Cache for service tools: {service_name: [MCPToolInfo, ...]}
        self._tools_cache: Dict[str, List[MCPToolInfo]] = {}

    async def list_service_tools(self, service_name: str, force_refresh: bool = False) -> List[MCPToolInfo]:
        """Get list of tools from a specific MCP service using tools/list.

        Args:
            service_name: Name of the MCP service
            force_refresh: If True, refresh cache even if already populated

        Returns:
            List of MCPToolInfo for tools provided by this service
        """
        # Check cache first
        if not force_refresh and service_name in self._tools_cache:
            cached = self._tools_cache[service_name]
            logger.info(f"[MCP Executor] Returning cached tools for {service_name}: {len(cached)} tools")
            return cached

        logger.info(f"[MCP Executor] Fetching tools list for service: {service_name}")

        # Find the service
        service = self._find_service_by_name(service_name)
        if service is None:
            logger.info(f"[MCP Executor] Service not found: {service_name}")
            return []

        # Get the process
        pm = mcp_manager.get_process_manager()
        proc = pm.get_process(service.id)
        if proc is None:
            logger.info(f"[MCP Executor] Cannot get process for service: {service_name}")
            return []

        # Check if process is still alive
        if proc.poll() is not None:
            logger.info(f"[MCP Executor] Service process has terminated: {service_name}")
            return []

        # Build JSON-RPC request for tools/list
        request_id = str(uuid.uuid4())
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tools/list",
            "params": {},
        }
        logger.info(f"[MCP Executor] JSON-RPC request: id={request_id}, method=tools/list")

        try:
            # Send request via stdin
            request_json = json.dumps(request) + "\n"
            logger.info(f"[MCP Executor] Sending tools/list request: {len(request_json)} bytes")

            loop = asyncio.get_event_loop()
            await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: (proc.stdin.write(request_json.encode()), proc.stdin.flush())
                ),
                timeout=5.0
            )

            # Read response
            response_line = await self._read_line_with_timeout(proc.stdout, self.timeout)

            if response_line is None:
                logger.info(f"[MCP Executor] Timeout waiting for tools/list response")
                return []

            if not response_line.strip():
                logger.info(f"[MCP Executor] Empty response from tools/list")
                return []

            # Parse JSON-RPC response
            response = json.loads(response_line.decode())
            logger.info(f"[MCP Executor] tools/list response received: {len(response_line)} bytes")

            if "error" in response:
                error_msg = response["error"].get("message", "Unknown error")
                logger.info(f"[MCP Executor] tools/list error: {error_msg}")
                return []

            # Parse tools from result
            result = response.get("result", {})
            tools_data = result.get("tools", [])
            logger.info(f"[MCP Executor] Found {len(tools_data)} tools in service {service_name}")

            tools = []
            for tool_data in tools_data:
                tool_name = tool_data.get("name", "")
                if not tool_name:
                    continue
                tool = MCPToolInfo(
                    name=tool_name,
                    service_name=service_name,
                    description=tool_data.get("description", f"Tool: {tool_name}"),
                    input_schema=tool_data.get("inputSchema"),
                )
                tools.append(tool)
                logger.info(f"[MCP Executor]   - Tool: {tool_name}: {tool.description[:50]}...")

            # Cache the result
            self._tools_cache[service_name] = tools
            return tools

        except asyncio.TimeoutError:
            logger.info(f"[MCP Executor] Timeout calling tools/list on {service_name}")
            return []
        except json.JSONDecodeError as e:
            logger.info(f"[MCP Executor] Invalid JSON from tools/list: {e}")
            return []
        except Exception as e:
            logger.info(f"[MCP Executor] Error listing tools: {e}")
            return []

    def clear_tools_cache(self, service_name: Optional[str] = None) -> None:
        """Clear the tools cache.

        Args:
            service_name: If provided, only clear cache for this service
        """
        if service_name:
            self._tools_cache.pop(service_name, None)
            logger.info(f"[MCP Executor] Cleared tools cache for: {service_name}")
        else:
            self._tools_cache.clear()
            logger.info("[MCP Executor] Cleared all tools cache")

    def get_cached_tools(self, service_name: str) -> List[MCPToolInfo]:
        """Get cached tools for a service (synchronous).

        Args:
            service_name: Name of the MCP service

        Returns:
            List of cached MCPToolInfo, empty if not cached
        """
        return self._tools_cache.get(service_name, [])

    def get_cached_tools_description(self, service_name: str) -> str:
        """Get description of cached tools for a service (synchronous).

        This method uses cached tool information. Call list_service_tools()
        first to populate the cache.

        Args:
            service_name: Name of the MCP service

        Returns:
            Description string with tool methods, or empty if no cache
        """
        tools = self.get_cached_tools(service_name)
        if not tools:
            logger.info(f"[MCP Executor] No cached tools for service: {service_name}")
            return ""

        lines = [f"服务 [{service_name}] 提供以下工具:"]
        for tool in tools:
            lines.append(f"  - 方法名: {tool.name}")
            lines.append(f"    描述: {tool.description}")
            if tool.input_schema:
                required = tool.input_schema.get("required", [])
                properties = tool.input_schema.get("properties", {})
                if required:
                    params = []
                    for param_name in required:
                        param_info = properties.get(param_name, {})
                        param_type = param_info.get("type", "any")
                        params.append(f"{param_name}({param_type})")
                    lines.append(f"    必需参数: {', '.join(params)}")

        result = "\n".join(lines)
        logger.info(f"[MCP Executor] Cached tools description for {service_name}: {len(tools)} tools")
        return result

    def get_all_cached_tools_description(self) -> str:
        """Get description of all cached tools across all services.

        Returns:
            Combined description string
        """
        pm = mcp_manager.get_process_manager()
        running_servers = pm.get_running_servers()

        if not running_servers:
            return ""

        lines = ["【可用 MCP 工具】"]
        has_cached_tools = False

        for server in running_servers:
            tools = self.get_cached_tools(server.name)
            if tools:
                has_cached_tools = True
                lines.append(f"\n服务 [{server.name}]:")
                for tool in tools:
                    lines.append(f"  - 方法名: {tool.name}")
                    lines.append(f"    描述: {tool.description}")
                    if tool.input_schema:
                        required = tool.input_schema.get("required", [])
                        properties = tool.input_schema.get("properties", {})
                        if required:
                            params = []
                            for param_name in required:
                                param_info = properties.get(param_name, {})
                                param_type = param_info.get("type", "any")
                                params.append(f"{param_name}({param_type})")
                            lines.append(f"    必需参数: {', '.join(params)}")
            else:
                # Fallback to service-level description
                desc = server.description or f"MCP 服务"
                lines.append(f"\n服务 [{server.name}]: {desc}")
                lines.append(f"  - 方法名: (需要先获取工具列表)")

        if not has_cached_tools:
            return ""

        result = "\n".join(lines)
        logger.info(f"[MCP Executor] All cached tools description: {len(result)} chars")
        return result

    def get_available_tools(self) -> List[ToolDescription]:
        """Get list of tools from all running MCP servers.

        Returns:
            List of ToolDescription for available tools
        """
        pm = mcp_manager.get_process_manager()
        running_servers = pm.get_running_servers()

        logger.info(f"[MCP Executor] Getting available tools from {len(running_servers)} running servers")

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
            logger.info(f"[MCP Executor] Found tool: name={server.name}, description={desc[:50]}...")

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
            logger.info(f"[MCP Executor] Service not found for description: name={service_name}")
            return None

        desc = info.description or f"MCP service: {service_name}"
        result = f"[工具] {service_name}: {desc}"
        logger.info(f"[MCP Executor] Tool description level1: {result}")
        return result

    def get_all_tools_description_level1(self) -> str:
        """Get Level 1 descriptions for all available tools (from cache).

        Returns:
            Combined description string for all tools
        """
        tools = self.get_available_tools()
        if not tools:
            logger.info("[MCP Executor] No available tools for description")
            return ""

        lines = ["【可用 MCP 工具】"]
        for tool in tools:
            lines.append(f"- {tool.name}: {tool.description}")
        result = "\n".join(lines)
        logger.info(f"[MCP Executor] All tools description: {len(tools)} tools, {len(result)} chars")
        return result

    async def get_all_tools_with_methods(self) -> str:
        """Get detailed description of all tools including method names.

        This async method fetches actual tool lists from each service
        using tools/list, providing correct method names for LLM.

        Returns:
            Detailed description string for prompt injection
        """
        pm = mcp_manager.get_process_manager()
        running_servers = pm.get_running_servers()

        if not running_servers:
            logger.info("[MCP Executor] No running servers for tools description")
            return ""

        logger.info(f"[MCP Executor] Fetching tools from {len(running_servers)} running servers")

        lines = ["【可用 MCP 工具】"]

        for server in running_servers:
            # Get tools from this service
            tools = await self.list_service_tools(server.name)

            if tools:
                lines.append(f"\n服务 [{server.name}]:")
                for tool in tools:
                    # Include tool name (method) and description
                    lines.append(f"  - 方法: {tool.name}")
                    lines.append(f"    描述: {tool.description}")
                    # If input_schema has required params, show them
                    if tool.input_schema:
                        required = tool.input_schema.get("required", [])
                        properties = tool.input_schema.get("properties", {})
                        if required:
                            params = []
                            for param_name in required:
                                param_info = properties.get(param_name, {})
                                param_type = param_info.get("type", "any")
                                param_desc = param_info.get("description", "")
                                params.append(f"{param_name}({param_type})")
                            lines.append(f"    参数: {', '.join(params)}")
            else:
                # Fallback to service description if tools/list failed
                desc = server.description or f"MCP 服务"
                lines.append(f"\n服务 [{server.name}]: {desc}")
                lines.append(f"  - 方法: {server.name} (使用服务名作为默认方法)")

        result = "\n".join(lines)
        logger.info(f"[MCP Executor] Detailed tools description: {len(result)} chars")
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
                logger.info(f"[MCP Executor] Found service: name={name}, id={server.id}, pid={server.pid}")
                return server
        logger.info(f"[MCP Executor] Service not found: name={name}")
        return None

    def is_service_available(self, service_name: str) -> bool:
        """Check if a service is available (running).

        Args:
            service_name: Name of the service to check

        Returns:
            True if service is running, False otherwise
        """
        available = self._find_service_by_name(service_name) is not None
        logger.info(f"[MCP Executor] Service availability check: name={service_name}, available={available}")
        return available

    async def _read_line_with_timeout(
        self,
        stdout,
        timeout: float,
    ) -> Optional[bytes]:
        """Read a line from stdout with proper timeout support.

        Uses select() for non-blocking I/O to allow true timeout interruption.
        Falls back to polling-based approach on Windows.

        Args:
            stdout: The stdout pipe to read from
            timeout: Timeout in seconds

        Returns:
            The line read, or None if timeout/error
        """
        if os.name == 'nt':
            # Windows: use polling-based approach
            return await self._read_line_polling(stdout, timeout)
        else:
            # Unix: use select for efficient non-blocking I/O
            return await self._read_line_select(stdout, timeout)

    async def _read_line_select(
        self,
        stdout,
        timeout: float,
    ) -> Optional[bytes]:
        """Read line using select() for Unix systems."""
        loop = asyncio.get_event_loop()
        fd = stdout.fileno()
        buffer = b""
        deadline = loop.time() + timeout

        while True:
            remaining = deadline - loop.time()
            if remaining <= 0:
                logger.info(f"[MCP Executor] Select timeout, no complete line received")
                return None

            # Use select with a small timeout to check for data
            try:
                readable = await loop.run_in_executor(
                    None,
                    lambda: select.select([fd], [], [], min(remaining, 0.5))[0]
                )
            except Exception as e:
                logger.info(f"[MCP Executor] Select error: {e}")
                return None

            if readable:
                try:
                    chunk = os.read(fd, 4096)
                    if not chunk:
                        # EOF
                        logger.info(f"[MCP Executor] EOF received from stdout")
                        return buffer if buffer else None
                    buffer += chunk
                    if b"\n" in buffer:
                        line, _ = buffer.split(b"\n", 1)
                        return line + b"\n"
                except BlockingIOError:
                    continue
                except Exception as e:
                    logger.info(f"[MCP Executor] Read error: {e}")
                    return None

            # Allow cancellation
            await asyncio.sleep(0)

    async def _read_line_polling(
        self,
        stdout,
        timeout: float,
    ) -> Optional[bytes]:
        """Read line using polling for Windows systems."""
        loop = asyncio.get_event_loop()
        buffer = b""
        deadline = loop.time() + timeout
        poll_interval = 0.1

        while True:
            remaining = deadline - loop.time()
            if remaining <= 0:
                logger.info(f"[MCP Executor] Polling timeout, no complete line received")
                return None

            # Check if process has data available (non-blocking check)
            try:
                # Try to read available data
                chunk = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        lambda: stdout.read(1) if stdout.peek(1) else b""
                    ),
                    timeout=min(poll_interval, remaining)
                )
                if chunk:
                    buffer += chunk
                    # Continue reading until newline
                    while True:
                        more = stdout.read(1)
                        if not more:
                            break
                        buffer += more
                        if more == b"\n":
                            return buffer
            except asyncio.TimeoutError:
                pass
            except Exception as e:
                logger.info(f"[MCP Executor] Polling read error: {e}")
                return None

            # Allow cancellation
            await asyncio.sleep(0.01)

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
        logger.info(f"[MCP] Executing tool: service={service_name}, method={method}")

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

        # Check if process is still alive
        if proc.poll() is not None:
            return ToolCallResult(
                success=False,
                tool_name=method,
                service_name=service_name,
                error=f"MCP service '{service_name}' process has terminated",
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
        logger.info(f"[MCP Executor] JSON-RPC request: id={request_id}, method=tools/call, tool={method}, args={arguments}")

        try:
            # Send request via stdin with timeout protection
            request_json = json.dumps(request) + "\n"
            logger.info(f"[MCP Executor] Sending request to stdin: {len(request_json)} bytes")

            try:
                # Use executor to allow timeout on write
                loop = asyncio.get_event_loop()
                await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        lambda: (proc.stdin.write(request_json.encode()), proc.stdin.flush())
                    ),
                    timeout=5.0  # 5 second timeout for write
                )
            except asyncio.TimeoutError:
                logger.info(f"[MCP Executor] Timeout writing to stdin")
                return ToolCallResult(
                    success=False,
                    tool_name=method,
                    service_name=service_name,
                    error="Timeout writing to MCP service stdin",
                )

            logger.info(f"[MCP Executor] Request sent, waiting for response (timeout={self.timeout}s)")

            # Read responses until we find the one matching our request ID
            # MCP servers may send notifications or responses from previous requests
            import time
            start_time = time.time()
            response = None

            while True:
                elapsed = time.time() - start_time
                remaining_timeout = self.timeout - elapsed

                if remaining_timeout <= 0:
                    logger.info(f"[MCP Executor] Timeout after {self.timeout}s waiting for matching response")
                    return ToolCallResult(
                        success=False,
                        tool_name=method,
                        service_name=service_name,
                        error=f"Tool call timed out after {self.timeout}s",
                    )

                # Read next line with remaining timeout
                response_line = await self._read_line_with_timeout(proc.stdout, remaining_timeout)

                if response_line is None:
                    logger.info(f"[MCP Executor] Timeout after {elapsed:.1f}s waiting for response")
                    return ToolCallResult(
                        success=False,
                        tool_name=method,
                        service_name=service_name,
                        error=f"Tool call timed out after {self.timeout}s",
                    )

                if not response_line.strip():
                    logger.info(f"[MCP Executor] Empty response line, continuing to read...")
                    continue

                # Parse JSON-RPC response
                logger.info(f"[MCP Executor] Received response: {len(response_line)} bytes")
                try:
                    response = json.loads(response_line.decode())
                except json.JSONDecodeError as e:
                    logger.info(f"[MCP Executor] Non-JSON response, skipping: {response_line[:100]}")
                    continue

                # Check if this is a notification (no id field) - skip it
                if "id" not in response:
                    logger.info(f"[MCP Executor] Received notification (no id), skipping: method={response.get('method', 'unknown')}")
                    continue

                # Verify response ID matches request
                resp_id = response.get("id")
                if resp_id != request_id:
                    logger.info(f"[MCP Executor] Response ID mismatch: expected={request_id}, got={resp_id}, reading next response...")
                    continue

                # Found matching response
                logger.info(f"[MCP Executor] Found matching response for request {request_id}")
                break

            if "error" in response:
                error_msg = response["error"].get("message", "Unknown error")
                logger.info(f"[MCP Executor] JSON-RPC error: {error_msg}")
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

            logger.info(f"[MCP] Tool execution successful: {method}")
            return ToolCallResult(
                success=True,
                tool_name=method,
                service_name=service_name,
                result=result,
            )

        except json.JSONDecodeError as e:
            logger.info(f"[MCP Executor] JSON decode error: {e}")
            return ToolCallResult(
                success=False,
                tool_name=method,
                service_name=service_name,
                error=f"Invalid JSON response: {e}",
            )
        except BrokenPipeError:
            logger.info(f"[MCP Executor] Broken pipe - MCP service may have crashed")
            return ToolCallResult(
                success=False,
                tool_name=method,
                service_name=service_name,
                error="MCP service connection lost (broken pipe)",
            )
        except Exception as e:
            logger.info(f"[MCP Executor] Execution exception: {e}")
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
        logger.info(f"[MCP Executor] Creating global executor with timeout={timeout}s")
        _executor = MCPToolExecutor(timeout=timeout)
    return _executor


def get_available_mcp_tools() -> List[ToolDescription]:
    """Convenience function to get available tools.

    Returns:
        List of ToolDescription for available tools
    """
    logger.info("[MCP] get_available_mcp_tools() called")
    return get_executor().get_available_tools()


def get_mcp_tools_prompt_snippet() -> str:
    """Get prompt snippet describing available MCP tools.

    Returns:
        Prompt snippet string, empty if no tools available
    """
    logger.info("[MCP] get_mcp_tools_prompt_snippet() called")
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
    logger.info(f"[MCP] execute_mcp_tool() called: service={service_name}, method={method}, args={arguments}")
    executor = get_executor(timeout)
    return await executor.execute_tool(service_name, method, arguments)


async def get_mcp_tools_prompt_snippet_async() -> str:
    """Async convenience function to get detailed MCP tools prompt snippet.

    This version fetches actual tool lists from services using tools/list,
    providing correct method names for LLM to use.

    Returns:
        Detailed prompt snippet string with method names
    """
    logger.info("[MCP] get_mcp_tools_prompt_snippet_async() called")
    return await get_executor().get_all_tools_with_methods()


async def list_service_tools(service_name: str) -> List[MCPToolInfo]:
    """Async convenience function to list tools from a specific service.

    Args:
        service_name: Name of the MCP service

    Returns:
        List of MCPToolInfo for tools in this service
    """
    logger.info(f"[MCP] list_service_tools() called: service={service_name}")
    return await get_executor().list_service_tools(service_name)
