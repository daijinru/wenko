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
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

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
    created_at: str
    status: MCPServerStatus = MCPServerStatus.STOPPED
    error_message: Optional[str] = None
    pid: Optional[int] = None


class MCPServerRegistry:
    """Registry for MCP server configurations.

    Stores and retrieves server configurations from the database.
    """

    SETTINGS_KEY = "mcp.servers"

    def __init__(self):
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
        return [MCPServerConfig(**s) for s in servers_data]

    def get_server(self, server_id: str) -> Optional[MCPServerConfig]:
        """Get a specific server config by ID."""
        for server_data in self._load_servers():
            if server_data.get("id") == server_id:
                return MCPServerConfig(**server_data)
        return None

    def add_server(self, config: MCPServerConfig) -> MCPServerConfig:
        """Add a new server config."""
        servers = self._load_servers()

        # Check for duplicate name
        for s in servers:
            if s.get("name") == config.name:
                raise ValueError(f"Server with name '{config.name}' already exists")

        servers.append(config.model_dump())
        self._save_servers(servers)
        return config

    def update_server(self, server_id: str, **updates) -> Optional[MCPServerConfig]:
        """Update an existing server config."""
        servers = self._load_servers()

        for i, s in enumerate(servers):
            if s.get("id") == server_id:
                # Check for duplicate name if name is being updated
                new_name = updates.get("name")
                if new_name and new_name != s.get("name"):
                    for other in servers:
                        if other.get("id") != server_id and other.get("name") == new_name:
                            raise ValueError(f"Server with name '{new_name}' already exists")

                # Apply updates
                for key, value in updates.items():
                    if value is not None:
                        s[key] = value

                servers[i] = s
                self._save_servers(servers)
                return MCPServerConfig(**s)

        return None

    def delete_server(self, server_id: str) -> bool:
        """Delete a server config."""
        servers = self._load_servers()
        original_count = len(servers)
        servers = [s for s in servers if s.get("id") != server_id]

        if len(servers) < original_count:
            self._save_servers(servers)
            return True
        return False


class MCPProcessManager:
    """Manager for MCP server processes.

    Handles starting, stopping, and monitoring server processes.
    """

    def __init__(self, registry: MCPServerRegistry):
        self._registry = registry
        self._processes: Dict[str, subprocess.Popen] = {}
        self._error_messages: Dict[str, str] = {}

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
        # Check if already running
        if self.get_status(server_id) == MCPServerStatus.RUNNING:
            return True

        # Get server config
        config = self._registry.get_server(server_id)
        if config is None:
            self._error_messages[server_id] = "Server configuration not found"
            return False

        # Clear previous error
        if server_id in self._error_messages:
            del self._error_messages[server_id]

        try:
            # Build command
            cmd = [config.command] + config.args

            # Prepare environment
            env = os.environ.copy()
            env.update(config.env)

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
            return True

        except FileNotFoundError as e:
            self._error_messages[server_id] = f"Command not found: {config.command}"
            return False
        except PermissionError as e:
            self._error_messages[server_id] = f"Permission denied: {config.command}"
            return False
        except Exception as e:
            self._error_messages[server_id] = f"Failed to start: {str(e)}"
            return False

    def stop_server(self, server_id: str) -> bool:
        """Stop a running server.

        Returns True if successfully stopped or already stopped.
        """
        proc = self._processes.get(server_id)
        if proc is None:
            return True

        try:
            # Try graceful termination first
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
            except subprocess.TimeoutExpired:
                # Force kill if graceful termination failed
                if os.name == 'nt':
                    proc.kill()
                else:
                    try:
                        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                proc.wait(timeout=1.0)

            del self._processes[server_id]

            # Clear error message on successful stop
            if server_id in self._error_messages:
                del self._error_messages[server_id]

            return True

        except Exception as e:
            self._error_messages[server_id] = f"Failed to stop: {str(e)}"
            return False

    def restart_server(self, server_id: str) -> bool:
        """Restart a server.

        Returns True if successfully restarted.
        """
        self.stop_server(server_id)
        return self.start_server(server_id)

    def stop_all(self) -> int:
        """Stop all running servers.

        Returns the number of servers stopped.
        """
        count = 0
        for server_id in list(self._processes.keys()):
            if self.stop_server(server_id):
                count += 1
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
            created_at=config.created_at,
            status=status,
            error_message=self.get_error_message(server_id),
            pid=self.get_pid(server_id),
        )

    def list_servers_with_status(self) -> List[MCPServerInfo]:
        """Get all servers with their current status."""
        result = []
        for config in self._registry.list_servers():
            info = self.get_server_info(config.id)
            if info:
                result.append(info)
        return result


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
    """
    get_registry()
    get_process_manager()


def shutdown_mcp_manager() -> int:
    """Shutdown the MCP manager and stop all servers.

    Should be called during application shutdown.
    Returns the number of servers stopped.
    """
    global _process_manager
    if _process_manager is not None:
        count = _process_manager.stop_all()
        _process_manager = None
        return count
    return 0
