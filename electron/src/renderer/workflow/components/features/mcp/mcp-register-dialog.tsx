import { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';

interface McpRegisterDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (data: {
    name: string;
    command: string;
    args: string[];
    env: Record<string, string>;
  }) => void;
  operating: boolean;
  initialData?: {
    name: string;
    command: string;
    args: string[];
    env: Record<string, string>;
  };
  isEditing?: boolean;
}

export function McpRegisterDialog({
  open,
  onOpenChange,
  onSubmit,
  operating,
  initialData,
  isEditing = false,
}: McpRegisterDialogProps) {
  const [name, setName] = useState('');
  const [command, setCommand] = useState('');
  const [argsText, setArgsText] = useState('');
  const [envText, setEnvText] = useState('');
  const [error, setError] = useState<string | null>(null);

  // Reset form when dialog opens
  useEffect(() => {
    if (open) {
      if (initialData) {
        setName(initialData.name);
        setCommand(initialData.command);
        setArgsText(initialData.args.join('\n'));
        setEnvText(
          Object.entries(initialData.env)
            .map(([k, v]) => `${k}=${v}`)
            .join('\n')
        );
      } else {
        setName('');
        setCommand('');
        setArgsText('');
        setEnvText('');
      }
      setError(null);
    }
  }, [open, initialData]);

  const handleSubmit = () => {
    setError(null);

    // Validate
    if (!name.trim()) {
      setError('请输入服务名称');
      return;
    }
    if (!command.trim()) {
      setError('请输入启动命令');
      return;
    }

    // Parse args (one per line)
    const args = argsText
      .split('\n')
      .map(line => line.trim())
      .filter(line => line.length > 0);

    // Parse env (KEY=VALUE per line)
    const env: Record<string, string> = {};
    const envLines = envText.split('\n').filter(line => line.trim().length > 0);
    for (const line of envLines) {
      const eqIndex = line.indexOf('=');
      if (eqIndex === -1) {
        setError(`环境变量格式错误: ${line}\n请使用 KEY=VALUE 格式`);
        return;
      }
      const key = line.substring(0, eqIndex).trim();
      const value = line.substring(eqIndex + 1).trim();
      if (!key) {
        setError(`环境变量键名不能为空: ${line}`);
        return;
      }
      env[key] = value;
    }

    onSubmit({
      name: name.trim(),
      command: command.trim(),
      args,
      env,
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>{isEditing ? '编辑 MCP 服务' : '注册 MCP 服务'}</DialogTitle>
        </DialogHeader>

        <div className="p-4 space-y-4">
          {error && (
            <div className="p-2 bg-red-100 text-red-800 rounded text-sm">
              {error}
            </div>
          )}

          <div className="space-y-2">
            <label className="text-sm font-medium">服务名称 *</label>
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="例如: 文件系统服务"
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">启动命令 *</label>
            <Input
              value={command}
              onChange={(e) => setCommand(e.target.value)}
              placeholder="例如: uvx, npx, python"
              className="font-mono"
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">命令参数</label>
            <Textarea
              value={argsText}
              onChange={(e) => setArgsText(e.target.value)}
              placeholder={"每行一个参数，例如:\nmcp-server-filesystem\n/path/to/allowed"}
              className="font-mono text-sm h-20"
            />
            <p className="text-xs text-muted-foreground">每行一个参数</p>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">环境变量</label>
            <Textarea
              value={envText}
              onChange={(e) => setEnvText(e.target.value)}
              placeholder={"每行一个，KEY=VALUE 格式\n例如:\nAPI_KEY=your-key\nDEBUG=true"}
              className="font-mono text-sm h-20"
            />
            <p className="text-xs text-muted-foreground">每行一个，使用 KEY=VALUE 格式</p>
          </div>
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={operating}
          >
            取消
          </Button>
          <Button onClick={handleSubmit} disabled={operating}>
            {operating ? '处理中...' : isEditing ? '保存' : '注册'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
