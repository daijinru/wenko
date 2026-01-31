import { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '@/lib/api-client';
import type {
  MCPServer,
  MCPServerListResponse,
  MCPServerCreateRequest,
  MCPServerUpdateRequest,
  MCPServerActionResponse,
} from '@/types/api';

const POLL_INTERVAL = 5000; // 5 seconds

export function useMcpServices() {
  const [servers, setServers] = useState<MCPServer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [operating, setOperating] = useState(false);
  const pollRef = useRef<number | null>(null);

  const loadServers = useCallback(async () => {
    try {
      const response = await api.get<MCPServerListResponse>('/api/mcp/servers');
      setServers(response.servers);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载 MCP 服务列表失败');
    } finally {
      setLoading(false);
    }
  }, []);

  // Start polling for status updates
  const startPolling = useCallback(() => {
    if (pollRef.current) return;
    pollRef.current = window.setInterval(() => {
      loadServers();
    }, POLL_INTERVAL);
  }, [loadServers]);

  // Stop polling
  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  // Register a new server
  const registerServer = useCallback(async (data: MCPServerCreateRequest): Promise<MCPServer | null> => {
    setOperating(true);
    setError(null);
    try {
      const server = await api.post<MCPServer>('/api/mcp/servers', data);
      await loadServers();
      return server;
    } catch (err) {
      setError(err instanceof Error ? err.message : '注册 MCP 服务失败');
      return null;
    } finally {
      setOperating(false);
    }
  }, [loadServers]);

  // Update a server
  const updateServer = useCallback(async (id: string, data: MCPServerUpdateRequest): Promise<boolean> => {
    setOperating(true);
    setError(null);
    try {
      await api.put<MCPServer>(`/api/mcp/servers/${id}`, data);
      await loadServers();
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : '更新 MCP 服务失败');
      return false;
    } finally {
      setOperating(false);
    }
  }, [loadServers]);

  // Delete a server
  const deleteServer = useCallback(async (id: string): Promise<boolean> => {
    setOperating(true);
    setError(null);
    try {
      await api.delete(`/api/mcp/servers/${id}`);
      await loadServers();
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : '删除 MCP 服务失败');
      return false;
    } finally {
      setOperating(false);
    }
  }, [loadServers]);

  // Start a server
  const startServer = useCallback(async (id: string): Promise<boolean> => {
    setOperating(true);
    setError(null);
    try {
      const response = await api.post<MCPServerActionResponse>(`/api/mcp/servers/${id}/start`);
      await loadServers();
      if (!response.success) {
        setError(response.message || '启动服务失败');
      }
      return response.success;
    } catch (err) {
      setError(err instanceof Error ? err.message : '启动 MCP 服务失败');
      return false;
    } finally {
      setOperating(false);
    }
  }, [loadServers]);

  // Stop a server
  const stopServer = useCallback(async (id: string): Promise<boolean> => {
    setOperating(true);
    setError(null);
    try {
      const response = await api.post<MCPServerActionResponse>(`/api/mcp/servers/${id}/stop`);
      await loadServers();
      if (!response.success) {
        setError(response.message || '停止服务失败');
      }
      return response.success;
    } catch (err) {
      setError(err instanceof Error ? err.message : '停止 MCP 服务失败');
      return false;
    } finally {
      setOperating(false);
    }
  }, [loadServers]);

  // Restart a server
  const restartServer = useCallback(async (id: string): Promise<boolean> => {
    setOperating(true);
    setError(null);
    try {
      const response = await api.post<MCPServerActionResponse>(`/api/mcp/servers/${id}/restart`);
      await loadServers();
      if (!response.success) {
        setError(response.message || '重启服务失败');
      }
      return response.success;
    } catch (err) {
      setError(err instanceof Error ? err.message : '重启 MCP 服务失败');
      return false;
    } finally {
      setOperating(false);
    }
  }, [loadServers]);

  // Initial load and start polling
  useEffect(() => {
    loadServers();
    startPolling();
    return () => {
      stopPolling();
    };
  }, [loadServers, startPolling, stopPolling]);

  return {
    servers,
    loading,
    error,
    operating,
    loadServers,
    registerServer,
    updateServer,
    deleteServer,
    startServer,
    stopServer,
    restartServer,
    startPolling,
    stopPolling,
  };
}
