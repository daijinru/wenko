import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { ApiKeyInput } from './api-key-input';
import type { Settings } from '@/hooks/use-settings';

interface LlmConfigSectionProps {
  settings: Partial<Settings>;
  onChange: (key: keyof Settings, value: string | number) => void;
}

export function LlmConfigSection({ settings, onChange }: LlmConfigSectionProps) {
  return (
    <div className="space-y-4">
      <h3 className="font-semibold text-lg border-b pb-2">LLM 配置</h3>

      <div className="grid gap-4">
        <div className="space-y-2">
          <label className="text-sm font-medium">API Base URL</label>
          <Input
            value={settings['llm.api_base'] || ''}
            onChange={(e) => onChange('llm.api_base', e.target.value)}
            placeholder="https://api.openai.com/v1"
          />
          <p className="text-xs text-muted-foreground">
            LLM API 端点地址，支持 OpenAI 兼容接口
          </p>
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium">API Key</label>
          <ApiKeyInput
            value={String(settings['llm.api_key'] || '')}
            onChange={(value) => onChange('llm.api_key', value)}
            placeholder="sk-..."
          />
          <p className="text-xs text-muted-foreground">
            API 密钥，用于身份验证
          </p>
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium">模型名称</label>
          <Input
            value={settings['llm.model'] || ''}
            onChange={(e) => onChange('llm.model', e.target.value)}
            placeholder="gpt-4o-mini"
          />
          <p className="text-xs text-muted-foreground">
            对话使用的模型，如 gpt-4o-mini, deepseek-chat 等
          </p>
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium">系统提示词</label>
          <Textarea
            value={settings['llm.system_prompt'] || ''}
            onChange={(e) => onChange('llm.system_prompt', e.target.value)}
            placeholder="你是一个友好的 AI 助手。"
            rows={3}
          />
          <p className="text-xs text-muted-foreground">
            定义 AI 的角色和行为
          </p>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">最大 Token 数</label>
            <Input
              type="number"
              value={settings['llm.max_tokens'] || 1024}
              onChange={(e) => onChange('llm.max_tokens', parseInt(e.target.value) || 1024)}
              min={1}
              max={8192}
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Temperature</label>
            <Input
              type="number"
              value={settings['llm.temperature'] || 0.7}
              onChange={(e) => onChange('llm.temperature', parseFloat(e.target.value) || 0.7)}
              min={0}
              max={2}
              step={0.1}
            />
          </div>
        </div>

        <div className="space-y-2">
          <label className="text-sm font-medium">视觉模型</label>
          <Input
            value={settings['llm.vision_model'] || ''}
            onChange={(e) => onChange('llm.vision_model', e.target.value)}
            placeholder="gpt-4o-mini"
          />
          <p className="text-xs text-muted-foreground">
            图片分析使用的模型
          </p>
        </div>
      </div>
    </div>
  );
}
