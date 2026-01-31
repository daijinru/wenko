import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useMcpServices } from '@/hooks/use-mcp-services';
import { McpRegisterDialog } from './mcp-register-dialog';
import { useToast } from '@/hooks/use-toast';
import type { MCPServerStatus } from '@/types/api';
import { cn } from '@/lib/utils';

interface ConfirmDialogState {
  open: boolean;
  title: string;
  content: string;
  onConfirm: () => void;
}

interface McpTabProps {
  onConfirmDialog: (state: ConfirmDialogState) => void;
}

function getStatusBadge(status: MCPServerStatus) {
  switch (status) {
    case 'running':
      return <Badge variant="green" className="text-[9px] px-1 h-4">运行中</Badge>;
    case 'stopped':
      return <Badge variant="orange" className="text-[9px] px-1 h-4">已停止</Badge>;
    case 'error':
      return <Badge variant="destructive" className="text-[9px] px-1 h-4">错误</Badge>;
    default:
      return <Badge variant="outline" className="text-[9px] px-1 h-4">{status}</Badge>;
  }
}

export function McpTab({ onConfirmDialog }: McpTabProps) {
  const {
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
  } = useMcpServices();

  const { toast } = useToast();
  const [showRegisterDialog, setShowRegisterDialog] = useState(false);
  const [editingServerId, setEditingServerId] = useState<string | null>(null);

  const handleRegister = async (data: {
    name: string;
    command: string;
    args: string[];
    env: Record<string, string>;
    description?: string;
    trigger_keywords?: string[];
  }) => {
    const server = await registerServer(data);
    if (server) {
      toast.success('MCP 服务注册成功');
      setShowRegisterDialog(false);
    } else {
      toast.error(error || '注册失败');
    }
  };

  const handleUpdate = async (id: string, data: {
    name: string;
    command: string;
    args: string[];
    env: Record<string, string>;
    description?: string;
    trigger_keywords?: string[];
  }) => {
    const success = await updateServer(id, data);
    if (success) {
      toast.success('MCP 服务更新成功');
      setEditingServerId(null);
    } else {
      toast.error(error || '更新失败');
    }
  };

  const handleDelete = (id: string, name: string) => {
    onConfirmDialog({
      open: true,
      title: '确认删除',
      content: `确定要删除 MCP 服务 "${name}" 吗？此操作不可恢复！`,
      onConfirm: async () => {
        const success = await deleteServer(id);
        if (success) {
          toast.success('MCP 服务已删除');
        } else {
          toast.error(error || '删除失败');
        }
      },
    });
  };

  const handleStart = async (id: string) => {
    const success = await startServer(id);
    if (success) {
      toast.success('MCP 服务已启动');
    } else {
      toast.error(error || '启动失败');
    }
  };

  const handleStop = async (id: string) => {
    const success = await stopServer(id);
    if (success) {
      toast.success('MCP 服务已停止');
    } else {
      toast.error(error || '停止失败');
    }
  };

  const handleRestart = async (id: string) => {
    const success = await restartServer(id);
    if (success) {
      toast.success('MCP 服务已重启');
    } else {
      toast.error(error || '重启失败');
    }
  };

  if (loading && servers.length === 0) {
    return (
      <div className="h-full flex items-center justify-center">
        <p className="text-muted-foreground">加载 MCP 服务列表中...</p>
      </div>
    );
  }

  const editingServer = editingServerId
    ? servers.find(s => s.id === editingServerId)
    : null;

  return (
    <div className="h-full flex flex-col">
      {/* Toolbar */}
      <div className="flex gap-1 !mb-2 !mt-1 !px-1 flex-wrap">
        <Button
          size="sm"
          onClick={() => setShowRegisterDialog(true)}
          disabled={operating}
        >
          + 添加服务
        </Button>
        <Button
          size="sm"
          variant="outline"
          onClick={loadServers}
          disabled={loading}
        >
          {loading ? '刷新中...' : '刷新'}
        </Button>
      </div>

      {/* Error display */}
      {error && (
        <div className="mx-2 mb-2 p-2 bg-red-100 text-red-800 rounded text-sm">
          {error}
        </div>
      )}

      {/* Server list */}
      <div className="flex-1 min-h-0 overflow-auto !px-2 !pb-2">
        {servers.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
            <p className="mb-2">暂无 MCP 服务</p>
            <p className="text-sm">点击"添加服务"按钮注册新的 MCP 服务器</p>
          </div>
        ) : (
          <div className="border-classic-inset bg-card overflow-y-auto flex-1 min-h-0 !p-0">
            <table className="w-full text-xs border-collapse detailed">
              <thead className="bg-muted sticky top-0 z-10 font-bold text-muted-foreground">
                <tr>
                  <th className="p-2 text-left border-b border-r border-border whitespace-nowrap w-32">名称</th>
                  <th className="p-2 text-left border-b border-r border-border whitespace-nowrap">命令</th>
                  <th className="p-2 text-center border-b border-r border-border whitespace-nowrap w-20">状态</th>
                  <th className="p-2 text-center border-b border-border whitespace-nowrap w-36">操作</th>
                </tr>
              </thead>
              <tbody>
                {servers.map((server) => (
                  <tr
                    key={server.id}
                    className={cn(
                      "hover:bg-primary hover:text-primary-foreground group transition-colors",
                      "even:bg-muted/30"
                    )}
                  >
                    <td className="p-2 border-b border-r border-border">
                      <div className="font-bold">{server.name}</div>
                      {server.pid && (
                        <div className="text-[10px] opacity-70">PID: {server.pid}</div>
                      )}
                    </td>
                    <td className="p-2 border-b border-r border-border">
                      <div className="font-mono text-[11px] truncate max-w-[200px]">
                        {server.command} {server.args.join(' ')}
                      </div>
                      {server.error_message && (
                        <div className="text-[10px] text-red-600 truncate max-w-[200px]">
                          {server.error_message}
                        </div>
                      )}
                    </td>
                    <td className="p-2 border-b border-r border-border text-center">
                      {getStatusBadge(server.status)}
                    </td>
                    <td className="p-2 border-b border-border text-center">
                      <div className="flex flex-row gap-1 justify-center">
                        {server.status === 'running' ? (
                          <>
                            <Button
                              size="sm"
                              variant="outline"
                              className="h-3 text-[10px] px-2"
                              onClick={() => handleStop(server.id)}
                              disabled={operating}
                            >
                              停止
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              className="h-3 text-[10px] px-2"
                              onClick={() => handleRestart(server.id)}
                              disabled={operating}
                            >
                              重启
                            </Button>
                          </>
                        ) : (
                          <Button
                            size="sm"
                            className="h-3 text-[10px] px-2"
                            onClick={() => handleStart(server.id)}
                            disabled={operating}
                          >
                            启动
                          </Button>
                        )}
                        <Button
                          size="sm"
                          variant="ghost"
                          className="h-3 text-[10px] px-2"
                          onClick={() => setEditingServerId(server.id)}
                          disabled={operating || server.status === 'running'}
                          title={server.status === 'running' ? '请先停止服务再编辑' : undefined}
                        >
                          编辑
                        </Button>
                        <Button
                          size="sm"
                          variant="destructive"
                          className="h-3 text-[10px] px-2"
                          onClick={() => handleDelete(server.id, server.name)}
                          disabled={operating}
                        >
                          删除
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Register dialog */}
      <McpRegisterDialog
        open={showRegisterDialog}
        onOpenChange={setShowRegisterDialog}
        onSubmit={handleRegister}
        operating={operating}
      />

      {/* Edit dialog */}
      {editingServer && (
        <McpRegisterDialog
          open={!!editingServerId}
          onOpenChange={(open) => !open && setEditingServerId(null)}
          onSubmit={(data) => handleUpdate(editingServer.id, data)}
          operating={operating}
          initialData={{
            name: editingServer.name,
            command: editingServer.command,
            args: editingServer.args,
            env: editingServer.env,
            description: editingServer.description || '',
            trigger_keywords: editingServer.trigger_keywords || [],
          }}
          isEditing
        />
      )}
    </div>
  );
}
