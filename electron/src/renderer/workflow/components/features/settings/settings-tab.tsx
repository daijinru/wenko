import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { useSettings, type Settings } from '@/hooks/use-settings';
import { LlmConfigSection } from './llm-config-section';
import { useToast } from '@/hooks/use-toast';

interface ConfirmDialogState {
  open: boolean;
  title: string;
  content: string;
  onConfirm: () => void;
}

interface SettingsTabProps {
  onConfirmDialog: (state: ConfirmDialogState) => void;
}

export function SettingsTab({ onConfirmDialog }: SettingsTabProps) {
  const {
    settings,
    loading,
    saving,
    error,
    loadSettings,
    updateSettings,
    resetSettings,
  } = useSettings();

  const { toast } = useToast();

  // Local form state for editing
  const [formData, setFormData] = useState<Partial<Settings>>({});
  const [hasChanges, setHasChanges] = useState(false);

  // Initialize form data when settings load
  useEffect(() => {
    if (settings) {
      setFormData(settings);
      setHasChanges(false);
    }
  }, [settings]);

  const handleChange = (key: keyof Settings, value: string | number) => {
    setFormData((prev) => ({ ...prev, [key]: value }));
    setHasChanges(true);
  };

  const handleSave = async () => {
    const success = await updateSettings(formData);
    if (success) {
      toast.success('配置已保存');
      setHasChanges(false);
    } else {
      toast.error(error || '保存配置失败，请检查配置是否正确');
    }
  };

  const handleReset = () => {
    onConfirmDialog({
      open: true,
      title: '确认重置',
      content: '确定要将所有配置重置为默认值吗？此操作不可恢复！',
      onConfirm: async () => {
        const success = await resetSettings();
        if (success) {
          toast.success('配置已恢复为默认值');
        } else {
          toast.error(error || '重置配置失败，请稍后重试');
        }
      },
    });
  };

  const handleCancel = () => {
    if (settings) {
      setFormData(settings);
      setHasChanges(false);
    }
  };

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <p className="text-muted-foreground">加载配置中...</p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col !p-2">
      <div className="flex gap-1 !mb-1 !mt-1 !px-1 flex-wrap">
        <Button size="sm" onClick={loadSettings} disabled={loading}>
          {loading ? '加载中...' : '刷新'}
        </Button>
        <Button
          size="sm"
          onClick={handleSave}
          disabled={saving || !hasChanges}
        >
          {saving ? '保存中...' : '保存配置'}
        </Button>
        <Button
          size="sm"
          variant="outline"
          onClick={handleCancel}
          disabled={!hasChanges}
        >
          取消修改
        </Button>
        <Button size="sm" variant="destructive" onClick={handleReset}>
          重置为默认
        </Button>
      </div>

      {hasChanges && (
        <div className="mx-2 mb-2 p-2 bg-yellow-100 text-yellow-800 rounded text-sm">
          有未保存的更改
        </div>
      )}

      {error && (
        <div className="mx-2 mb-2 p-2 bg-red-100 text-red-800 rounded text-sm">
          {error}
        </div>
      )}

      <div className="flex-1 min-h-0 overflow-auto px-2 pb-4">
        <LlmConfigSection settings={formData} onChange={handleChange} />
      </div>
    </div>
  );
}
