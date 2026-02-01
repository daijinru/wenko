import { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { api } from '@/lib/api-client';
import type { MCPToolListResponse } from '@/types/api';

interface McpToolsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  serverId: string;
  serverName: string;
}

export function McpToolsDialog({
  open,
  onOpenChange,
  serverId,
  serverName,
}: McpToolsDialogProps) {
  const [tools, setTools] = useState<MCPToolListResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open && serverId) {
      loadTools();
    }
  }, [open, serverId]);

  const loadTools = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get<MCPToolListResponse>(`/api/mcp/servers/${serverId}/tools`);
      setTools(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : '获取工具列表失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[800px] max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>工具列表 - {serverName}</DialogTitle>
        </DialogHeader>

        <div className="flex-1 min-h-0 overflow-auto">
          {loading && (
            <div className="flex items-center justify-center py-8">
              <p className="text-muted-foreground">加载中...</p>
            </div>
          )}

          {error && (
            <div className="p-3 bg-red-100 text-red-800 rounded text-sm">
              {error}
            </div>
          )}

          {!loading && !error && tools && (
            <>
              {tools.tools.length === 0 ? (
                <div className="flex items-center justify-center py-8">
                  <p className="text-muted-foreground">该服务暂无可用工具</p>
                </div>
              ) : (
                <div className="border-classic-inset bg-card overflow-y-auto !p-0">
                  <table className="w-full text-xs border-collapse detailed" style={{ tableLayout: 'fixed' }}>
                    <colgroup>
                      <col style={{ width: '30%' }} />
                      <col style={{ width: '40%' }} />
                      <col style={{ width: '30%' }} />
                    </colgroup>
                    <thead className="bg-muted sticky top-0 z-10 font-bold text-muted-foreground">
                      <tr>
                        <th className="p-2 text-left border-b border-r border-border whitespace-nowrap">工具名称</th>
                        <th className="p-2 text-left border-b border-r border-border whitespace-nowrap">参数</th>
                        <th className="p-2 text-left border-b border-border whitespace-nowrap">描述</th>
                      </tr>
                    </thead>
                    <tbody>
                      {tools.tools.map((tool, index) => {
                        const requiredParams = tool.input_schema?.required as string[] | undefined;
                        const properties = tool.input_schema?.properties as Record<string, { type?: string }> | undefined;

                        return (
                          <tr
                            key={tool.name}
                            className="hover:bg-primary/10 even:bg-muted/30"
                          >
                            <td className="!p-2 border-b border-r border-border overflow-hidden">
                              <code className="text-[11px] font-mono font-bold truncate block">{tool.name}</code>
                            </td>
                            <td className="!p-2 border-b border-r border-border overflow-hidden">
                              {requiredParams && requiredParams.length > 0 ? (
                                <div className="text-[10px] font-mono text-muted-foreground truncate">
                                  {requiredParams.map((param, i) => (
                                    <p key={param}>
                                      {param}
                                      {properties?.[param]?.type && (
                                        <span className="text-blue-600">:{properties[param].type}</span>
                                      )}
                                      {i < requiredParams.length - 1 && ', '}
                                    </p>
                                  ))}
                                </div>
                              ) : (
                                <span className="text-[10px] text-muted-foreground">-</span>
                              )}
                            </td>
                            <td className="!p-2 border-b border-border overflow-hidden">
                              <div
                                className="text-[11px] truncate"
                                title={tool.description || undefined}
                              >
                                {tool.description || '-'}
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
              <div className="mt-2 text-xs text-muted-foreground text-right">
                共 {tools.total} 个工具
              </div>
            </>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
