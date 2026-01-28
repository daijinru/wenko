import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Checkbox } from '@/components/ui/checkbox';
import { ApiKeyInput } from './api-key-input';
import type { Settings } from '@/hooks/use-settings';

interface LlmConfigSectionProps {
  settings: Partial<Settings>;
  onChange: (key: keyof Settings, value: string | number | boolean) => void;
}

export function LlmConfigSection({ settings, onChange }: LlmConfigSectionProps) {
  return (
    <div className="space-y-4 !p-[8px]">
      <h3 className="font-semibold text-lg border-b pb-2">LLM 配置</h3>

      <div className="grid gap-2">
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

        <div className="space-y-3 pt-4 border-t">
          <div className="flex items-start space-x-3 gap-2">
            <Checkbox
              id="deep-thinking"
              checked={settings['llm.deep_thinking_enabled'] === true}
              onCheckedChange={(checked) =>
                onChange('llm.deep_thinking_enabled', checked === true)
              }
            />
            <div className="flex-1">
              <label htmlFor="deep-thinking" className="text-sm font-medium cursor-pointer">
                深度思考模式
              </label>
              <p className="text-xs text-muted-foreground mt-1">
                启用后，AI 将进行更深入的分析和推理，适合处理复杂问题。
              </p>
              <div className="mt-2 p-2 bg-amber-50 dark:bg-amber-950/30 rounded-md border border-amber-200 dark:border-amber-800">
                <p className="text-xs text-amber-700 dark:text-amber-400">
                  <span className="font-medium">注意：</span>该模式仅对支持深度思考的模型有效。此模式可能会消耗更多 tokens（约 2-5 倍）并增加响应等待时间（约 3-10 秒）。建议仅在需要深度分析时开启。
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
