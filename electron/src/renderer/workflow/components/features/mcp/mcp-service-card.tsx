import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { MCPServer, MCPServerStatus } from '@/types/api';

interface McpServiceCardProps {
  server: MCPServer;
  operating: boolean;
  onStart: () => void;
  onStop: () => void;
  onRestart: () => void;
  onEdit: () => void;
  onDelete: () => void;
}

function getStatusBadge(status: MCPServerStatus) {
  switch (status) {
    case 'running':
      return <Badge variant="default" className="bg-green-500">运行中</Badge>;
    case 'stopped':
      return <Badge variant="secondary">已停止</Badge>;
    case 'error':
      return <Badge variant="destructive">错误</Badge>;
    default:
      return <Badge variant="outline">{status}</Badge>;
  }
}

export function McpServiceCard({
  server,
  operating,
  onStart,
  onStop,
  onRestart,
  onEdit,
  onDelete,
}: McpServiceCardProps) {
  const isRunning = server.status === 'running';
  const commandDisplay = [server.command, ...server.args].join(' ');

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <span>{server.name}</span>
            {getStatusBadge(server.status)}
          </CardTitle>
          {server.pid && (
            <span className="text-xs text-muted-foreground">
              PID: {server.pid}
            </span>
          )}
        </div>
        <CardDescription className="font-mono text-xs truncate">
          {commandDisplay}
        </CardDescription>
      </CardHeader>

      <CardContent>
        {server.error_message && (
          <div className="mb-2 p-2 bg-red-50 text-red-700 rounded text-xs">
            {server.error_message}
          </div>
        )}

        {Object.keys(server.env).length > 0 && (
          <div className="mb-2 text-xs text-muted-foreground">
            <span className="font-medium">环境变量: </span>
            {Object.keys(server.env).join(', ')}
          </div>
        )}

        <div className="flex gap-1 flex-wrap">
          {isRunning ? (
            <>
              <Button
                size="sm"
                variant="outline"
                onClick={onStop}
                disabled={operating}
              >
                停止
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={onRestart}
                disabled={operating}
              >
                重启
              </Button>
            </>
          ) : (
            <Button
              size="sm"
              onClick={onStart}
              disabled={operating}
            >
              启动
            </Button>
          )}
          <Button
            size="sm"
            variant="outline"
            onClick={onEdit}
            disabled={operating || isRunning}
            title={isRunning ? '请先停止服务再编辑' : undefined}
          >
            编辑
          </Button>
          <Button
            size="sm"
            variant="destructive"
            onClick={onDelete}
            disabled={operating}
          >
            删除
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
