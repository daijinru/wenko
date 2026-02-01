"""MCP Service Manager Module

Provides management functionality for MCP (Model Context Protocol) servers.
Supports service registration, lifecycle management (start/stop), and status monitoring.
"""

import json
import os
import signal
import subprocess
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum

from pydantic import BaseModel, Field

import chat_db


class MCPServerStatus(str, Enum):
    """MCP server status."""
    STOPPED = "stopped"
    RUNNING = "running"
    ERROR = "error"


class MCPServerConfig(BaseModel):
    """MCP server configuration."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    command: str
    args: List[str] = Field(default_factory=list)
    env: Dict[str, str] = Field(default_factory=dict)
    enabled: bool = True
    auto_start: bool = False  # Whether to auto-start on application startup
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    # New fields for conversation integration
    description: Optional[str] = None  # Tool description for prompt injection
    trigger_keywords: List[str] = Field(default_factory=list)  # Keywords for intent recognition

    class Config:
        use_enum_values = True


class MCPServerInfo(BaseModel):
    """MCP server info with runtime status."""
    id: str
    name: str
    command: str
    args: List[str]
    env: Dict[str, str]
    enabled: bool
    auto_start: bool = False
    created_at: str
    status: MCPServerStatus = MCPServerStatus.STOPPED
    error_message: Optional[str] = None
    pid: Optional[int] = None
    # New fields for conversation integration
    description: Optional[str] = None
    trigger_keywords: List[str] = Field(default_factory=list)


class MCPServerRegistry:
    """Registry for MCP server configurations.

    Stores and retrieves server configurations from the database.
    """

    SETTINGS_KEY = "mcp.servers"

    def __init__(self):
        print("[MCP Registry] Initializing MCP server registry")
        self._ensure_setting_exists()

    def _ensure_setting_exists(self) -> None:
        """Ensure the mcp.servers setting exists in database."""
        value = chat_db.get_setting(self.SETTINGS_KEY)
        if value is None:
            chat_db.set_setting(self.SETTINGS_KEY, [], "json")

    def _load_servers(self) -> List[Dict[str, Any]]:
        """Load server configs from database."""
        value = chat_db.get_setting(self.SETTINGS_KEY)
        if value is None:
            return []
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return []
        return value if isinstance(value, list) else []

    def _save_servers(self, servers: List[Dict[str, Any]]) -> None:
        """Save server configs to database."""
        chat_db.set_setting(self.SETTINGS_KEY, servers, "json")

    def list_servers(self) -> List[MCPServerConfig]:
        """Get all registered server configs."""
        servers_data = self._load_servers()
        print(f"[MCP Registry] Listing servers: count={len(servers_data)}")
        return [MCPServerConfig(**s) for s in servers_data]

    def get_server(self, server_id: str) -> Optional[MCPServerConfig]:
        """Get a specific server config by ID."""
        for server_data in self._load_servers():
            if server_data.get("id") == server_id:
                print(f"[MCP Registry] Found server: id={server_id}, name={server_data.get('name')}")
                return MCPServerConfig(**server_data)
        print(f"[MCP Registry] Server not found: id={server_id}")
        return None

    def add_server(self, config: MCPServerConfig) -> MCPServerConfig:
        """Add a new server config."""
        servers = self._load_servers()

        # Check for duplicate name
        for s in servers:
            if s.get("name") == config.name:
                print(f"[MCP Registry] Add server failed: duplicate name '{config.name}'")
                raise ValueError(f"Server with name '{config.name}' already exists")

        servers.append(config.model_dump())
        self._save_servers(servers)
        print(f"[MCP Registry] Server added: id={config.id}, name={config.name}, command={config.command}")
        return config

    def update_server(self, server_id: str, **updates) -> Optional[MCPServerConfig]:
        """Update an existing server config."""
        servers = self._load_servers()
        print(f"[MCP Registry] Updating server: id={server_id}, updates={list(updates.keys())}")

        for i, s in enumerate(servers):
            if s.get("id") == server_id:
                # Check for duplicate name if name is being updated
                new_name = updates.get("name")
                if new_name and new_name != s.get("name"):
                    for other in servers:
                        if other.get("id") != server_id and other.get("name") == new_name:
                            print(f"[MCP Registry] Update failed: duplicate name '{new_name}'")
                            raise ValueError(f"Server with name '{new_name}' already exists")

                # Apply updates
                for key, value in updates.items():
                    if value is not None:
                        s[key] = value

                servers[i] = s
                self._save_servers(servers)
                print(f"[MCP Registry] Server updated: id={server_id}, name={s.get('name')}")
                return MCPServerConfig(**s)

        print(f"[MCP Registry] Update failed: server not found id={server_id}")
        return None

    def delete_server(self, server_id: str) -> bool:
        """Delete a server config."""
        servers = self._load_servers()
        original_count = len(servers)
        servers = [s for s in servers if s.get("id") != server_id]

        if len(servers) < original_count:
            self._save_servers(servers)
            print(f"[MCP Registry] Server deleted: id={server_id}")
            return True
        print(f"[MCP Registry] Delete failed: server not found id={server_id}")
        return False


class MCPProcessManager:
    """Manager for MCP server processes.

    Handles starting, stopping, and monitoring server processes.
    """

    def __init__(self, registry: MCPServerRegistry):
        self._registry = registry
        self._processes: Dict[str, subprocess.Popen] = {}
        self._error_messages: Dict[str, str] = {}
        print("[MCP ProcessManager] Initialized process manager")

    def get_status(self, server_id: str) -> MCPServerStatus:
        """Get the current status of a server."""
        proc = self._processes.get(server_id)

        if proc is None:
            if server_id in self._error_messages:
                return MCPServerStatus.ERROR
            return MCPServerStatus.STOPPED

        # Check if process is still running
        poll_result = proc.poll()
        if poll_result is None:
            return MCPServerStatus.RUNNING
        else:
            # Process has exited
            del self._processes[server_id]
            if poll_result != 0:
                self._error_messages[server_id] = f"Process exited with code {poll_result}"
                return MCPServerStatus.ERROR
            return MCPServerStatus.STOPPED

    def get_error_message(self, server_id: str) -> Optional[str]:
        """Get the error message for a server if any."""
        return self._error_messages.get(server_id)

    def get_pid(self, server_id: str) -> Optional[int]:
        """Get the PID of a running server process."""
        proc = self._processes.get(server_id)
        if proc and proc.poll() is None:
            return proc.pid
        return None

    def start_server(self, server_id: str) -> bool:
        """Start a server by ID.

        Returns True if successfully started, False otherwise.
        """
        print(f"[MCP ProcessManager] Starting server: id={server_id}")

        # Check if already running
        if self.get_status(server_id) == MCPServerStatus.RUNNING:
            print(f"[MCP ProcessManager] Server already running: id={server_id}")
            return True

        # Get server config
        config = self._registry.get_server(server_id)
        if config is None:
            self._error_messages[server_id] = "Server configuration not found"
            print(f"[MCP ProcessManager] Start failed: config not found for id={server_id}")
            return False

        # Clear previous error
        if server_id in self._error_messages:
            del self._error_messages[server_id]

        try:
            # Build command
            cmd = [config.command] + config.args
            print(f"[MCP ProcessManager] Executing command: {' '.join(cmd)}")

            # Prepare environment
            env = os.environ.copy()
            env.update(config.env)
            if config.env:
                print(f"[MCP ProcessManager] Custom env vars: {list(config.env.keys())}")

            # Start process
            proc = subprocess.Popen(
                cmd,
                env=env,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                # Use process group for better cleanup on Unix
                preexec_fn=os.setsid if os.name != 'nt' else None,
            )

            self._processes[server_id] = proc
            print(f"[MCP ProcessManager] Server started: id={server_id}, pid={proc.pid}, name={config.name}")
            return True

        except FileNotFoundError as e:
            self._error_messages[server_id] = f"Command not found: {config.command}"
            print(f"[MCP ProcessManager] Start failed: command not found '{config.command}'")
            return False
        except PermissionError as e:
            self._error_messages[server_id] = f"Permission denied: {config.command}"
            print(f"[MCP ProcessManager] Start failed: permission denied '{config.command}'")
            return False
        except Exception as e:
            self._error_messages[server_id] = f"Failed to start: {str(e)}"
            print(f"[MCP ProcessManager] Start failed: {str(e)}")
            return False

    def stop_server(self, server_id: str) -> bool:
        """Stop a running server.

        Returns True if successfully stopped or already stopped.
        """
        print(f"[MCP ProcessManager] Stopping server: id={server_id}")

        proc = self._processes.get(server_id)
        if proc is None:
            print(f"[MCP ProcessManager] Server already stopped: id={server_id}")
            return True

        pid = proc.pid
        try:
            # Try graceful termination first
            print(f"[MCP ProcessManager] Sending SIGTERM to pid={pid}")
            if os.name == 'nt':
                # Windows
                proc.terminate()
            else:
                # Unix: send SIGTERM to process group
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                except ProcessLookupError:
                    pass

            # Wait for process to exit (with timeout)
            try:
                proc.wait(timeout=5.0)
                print(f"[MCP ProcessManager] Server stopped gracefully: id={server_id}, pid={pid}")
            except subprocess.TimeoutExpired:
                # Force kill if graceful termination failed
                print(f"[MCP ProcessManager] Timeout waiting, sending SIGKILL to pid={pid}")
                if os.name == 'nt':
                    proc.kill()
                else:
                    try:
                        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                proc.wait(timeout=1.0)
                print(f"[MCP ProcessManager] Server force killed: id={server_id}, pid={pid}")

            del self._processes[server_id]

            # Clear error message on successful stop
            if server_id in self._error_messages:
                del self._error_messages[server_id]

            return True

        except Exception as e:
            self._error_messages[server_id] = f"Failed to stop: {str(e)}"
            print(f"[MCP ProcessManager] Stop failed: id={server_id}, error={str(e)}")
            return False

    def restart_server(self, server_id: str) -> bool:
        """Restart a server.

        Returns True if successfully restarted.
        """
        print(f"[MCP ProcessManager] Restarting server: id={server_id}")
        self.stop_server(server_id)
        return self.start_server(server_id)

    def stop_all(self) -> int:
        """Stop all running servers.

        Returns the number of servers stopped.
        """
        print(f"[MCP ProcessManager] Stopping all servers: count={len(self._processes)}")
        count = 0
        for server_id in list(self._processes.keys()):
            if self.stop_server(server_id):
                count += 1
        print(f"[MCP ProcessManager] Stopped {count} servers")
        return count

    def get_server_info(self, server_id: str) -> Optional[MCPServerInfo]:
        """Get full server info including status."""
        config = self._registry.get_server(server_id)
        if config is None:
            return None

        status = self.get_status(server_id)

        return MCPServerInfo(
            id=config.id,
            name=config.name,
            command=config.command,
            args=config.args,
            env=config.env,
            enabled=config.enabled,
            auto_start=config.auto_start,
            created_at=config.created_at,
            status=status,
            error_message=self.get_error_message(server_id),
            pid=self.get_pid(server_id),
            description=config.description,
            trigger_keywords=config.trigger_keywords,
        )

    def list_servers_with_status(self) -> List[MCPServerInfo]:
        """Get all servers with their current status."""
        result = []
        for config in self._registry.list_servers():
            info = self.get_server_info(config.id)
            if info:
                result.append(info)
        return result

    def get_running_servers(self) -> List[MCPServerInfo]:
        """Get only running servers with their info.

        Used for conversation integration to find available tools.
        """
        result = []
        for config in self._registry.list_servers():
            if self.get_status(config.id) == MCPServerStatus.RUNNING:
                info = self.get_server_info(config.id)
                if info:
                    result.append(info)
        print(f"[MCP ProcessManager] Running servers: count={len(result)}, names={[s.name for s in result]}")
        return result

    def get_process(self, server_id: str) -> Optional[subprocess.Popen]:
        """Get the subprocess.Popen instance for a running server.

        Used for MCP tool executor to communicate via stdio.
        Returns None if server is not running.
        """
        proc = self._processes.get(server_id)
        if proc and proc.poll() is None:
            return proc
        return None


# Global instances
_registry: Optional[MCPServerRegistry] = None
_process_manager: Optional[MCPProcessManager] = None


def get_registry() -> MCPServerRegistry:
    """Get the global registry instance."""
    global _registry
    if _registry is None:
        _registry = MCPServerRegistry()
    return _registry


def get_process_manager() -> MCPProcessManager:
    """Get the global process manager instance."""
    global _process_manager
    if _process_manager is None:
        _process_manager = MCPProcessManager(get_registry())
    return _process_manager


def init_mcp_manager() -> None:
    """Initialize the MCP manager.

    Should be called during application startup.
    Automatically starts all enabled MCP servers.
    """
    print("[MCP] Initializing MCP manager")
    registry = get_registry()
    pm = get_process_manager()

    # Auto-start servers with auto_start enabled
    servers = registry.list_servers()
    auto_start_servers = [s for s in servers if s.auto_start and s.enabled]
    started_count = 0
    for server in auto_start_servers:
        print(f"[MCP] Auto-starting server: name={server.name}, id={server.id}")
        if pm.start_server(server.id):
            started_count += 1
        else:
            print(f"[MCP] Failed to auto-start server: name={server.name}")

    print(f"[MCP] MCP manager initialized, auto-started {started_count}/{len(auto_start_servers)} servers")


def shutdown_mcp_manager() -> int:
    """Shutdown the MCP manager and stop all servers.

    Should be called during application shutdown.
    Returns the number of servers stopped.
    """
    global _process_manager
    print("[MCP] Shutting down MCP manager")
    if _process_manager is not None:
        count = _process_manager.stop_all()
        _process_manager = None
        print(f"[MCP] MCP manager shutdown complete, stopped {count} servers")
        return count
    print("[MCP] MCP manager shutdown: no process manager active")
    return 0
