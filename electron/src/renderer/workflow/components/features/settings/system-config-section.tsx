import { Input } from '@/components/ui/input';
import { Checkbox } from '@/components/ui/checkbox';
import type { Settings } from '@/hooks/use-settings';

interface SystemConfigSectionProps {
  settings: Partial<Settings>;
  onChange: (key: keyof Settings, value: string | number | boolean) => void;
}

export function SystemConfigSection({ settings, onChange }: SystemConfigSectionProps) {
  return (
    <div className="space-y-4 !p-[8px]">
      <div className="flex items-center space-x-3 gap-2 !mb-2">
        <Checkbox
          id="memory"
          checked={settings['system.memory_enabled'] === true}
          onCheckedChange={(checked) =>
            onChange('system.memory_enabled', checked === true)
          }
        />
        <div className="flex-1">
          <label htmlFor="memory" className="text-sm font-medium cursor-pointer">
            启用记忆系统
          </label>
          <p className="text-xs text-muted-foreground">
            自动存储和检索长期记忆
          </p>
        </div>
      </div>

      <div className="flex items-center space-x-3 gap-2 !mb-2">
        <Checkbox
          id="emotion"
          checked={settings['system.emotion_enabled'] === true}
          onCheckedChange={(checked) =>
            onChange('system.emotion_enabled', checked === true)
          }
        />
        <div className="flex-1">
          <label htmlFor="emotion" className="text-sm font-medium cursor-pointer">
            启用情绪系统
          </label>
          <p className="text-xs text-muted-foreground">
            自动检测用户情绪并调整回复策略
          </p>
        </div>
      </div>

      <div className="flex items-center space-x-3 gap-2 !mb-2">
        <Checkbox
          id="hitl"
          checked={settings['system.hitl_enabled'] === true}
          onCheckedChange={(checked) =>
            onChange('system.hitl_enabled', checked === true)
          }
        />
        <div className="flex-1">
          <label htmlFor="hitl" className="text-sm font-medium cursor-pointer">
            启用 HITL (人机交互) 系统
          </label>
          <p className="text-xs text-muted-foreground">
            允许 AI 请求用户确认敏感操作（如保存记忆、创建计划）
          </p>
        </div>
      </div>

      <div className="flex items-center space-x-3 gap-2 !mb-2">
        <Checkbox
          id="intent-recognition"
          checked={settings['system.intent_recognition_enabled'] === true}
          onCheckedChange={(checked) =>
            onChange('system.intent_recognition_enabled', checked === true)
          }
        />
        <div className="flex-1">
          <label htmlFor="intent-recognition" className="text-sm font-medium cursor-pointer">
            启用意图识别系统
          </label>
          <p className="text-xs text-muted-foreground">
            自动识别用户意图以优化响应（减少 token 消耗）
          </p>
        </div>
      </div>

      <div className="space-y-2 pt-2 border-t">
        <div className="text-sm font-medium mb-2">提醒设置</div>
        <div className="flex items-center space-x-3 gap-2 !mb-2">
          <Checkbox
            id="reminder-window"
            checked={settings['system.reminder_window_enabled'] !== false}
            onCheckedChange={(checked) =>
              onChange('system.reminder_window_enabled', checked === true)
            }
          />
          <div className="flex-1">
            <label htmlFor="reminder-window" className="text-sm font-medium cursor-pointer">
              启用弹窗提醒
            </label>
            <p className="text-xs text-muted-foreground">
              计划到期时弹出独立窗口提醒
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-3 gap-2 !mb-2">
          <Checkbox
            id="os-notification"
            checked={settings['system.os_notification_enabled'] !== false}
            onCheckedChange={(checked) =>
              onChange('system.os_notification_enabled', checked === true)
            }
          />
          <div className="flex-1">
            <label htmlFor="os-notification" className="text-sm font-medium cursor-pointer">
              启用系统通知
            </label>
            <p className="text-xs text-muted-foreground">
              计划到期时发送操作系统通知（macOS/Windows 通知中心）
            </p>
          </div>
        </div>
      </div>

      <div className="space-y-2 pt-2 border-t">
        <label className="text-sm font-medium">情绪识别置信度阈值</label>
        <Input
          type="number"
          value={settings['system.emotion_confidence_threshold'] ?? 0.5}
          onChange={(e) =>
            onChange('system.emotion_confidence_threshold', parseFloat(e.target.value) || 0.5)
          }
          min={0}
          max={1}
          step={0.1}
          className="w-32"
        />
        <p className="text-xs text-muted-foreground">
          低于此阈值的情绪检测将被视为中性 (0.0 - 1.0)
        </p>
      </div>
    </div>
  );
}
