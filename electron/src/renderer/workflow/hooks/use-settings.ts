import { useState, useEffect, useCallback } from 'react';
import { api } from '@/lib/api-client';

export interface Settings {
  'llm.api_base': string;
  'llm.api_key': string;
  'llm.model': string;
  'llm.system_prompt': string;
  'llm.max_tokens': number;
  'llm.temperature': number;
  'llm.vision_model': string;
  [key: string]: string | number | boolean;
}

interface SettingsResponse {
  settings: Settings;
}

interface BatchUpdateResponse {
  success: boolean;
  updated_count: number;
}

interface ResetResponse {
  success: boolean;
  reset_count: number;
}

export function useSettings() {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadSettings = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get<SettingsResponse>('/api/settings');
      setSettings(response.settings);
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载配置失败');
    } finally {
      setLoading(false);
    }
  }, []);

  const updateSettings = useCallback(async (newSettings: Partial<Settings>): Promise<boolean> => {
    setSaving(true);
    setError(null);
    try {
      await api.put<BatchUpdateResponse>('/api/settings', { settings: newSettings });
      // Reload settings after update
      await loadSettings();
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : '保存配置失败');
      return false;
    } finally {
      setSaving(false);
    }
  }, [loadSettings]);

  const resetSettings = useCallback(async (): Promise<boolean> => {
    setSaving(true);
    setError(null);
    try {
      await api.post<ResetResponse>('/api/settings/reset');
      // Reload settings after reset
      await loadSettings();
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : '重置配置失败');
      return false;
    } finally {
      setSaving(false);
    }
  }, [loadSettings]);

  useEffect(() => {
    loadSettings();
  }, [loadSettings]);

  return {
    settings,
    loading,
    saving,
    error,
    loadSettings,
    updateSettings,
    resetSettings,
  };
}
