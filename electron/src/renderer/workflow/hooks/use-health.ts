import { useState, useEffect, useCallback } from 'react';
import { api } from '@/lib/api-client';
import type { HealthResponse } from '@/types/api';

interface HealthStatus {
  online: boolean;
  checking: boolean;
}

export function useHealth() {
  const [status, setStatus] = useState<HealthStatus>({
    online: false,
    checking: true,
  });

  const checkHealth = useCallback(async () => {
    setStatus((prev) => ({ ...prev, checking: true }));
    try {
      await api.get<HealthResponse>('/health');
      setStatus({ online: true, checking: false });
    } catch {
      setStatus({ online: false, checking: false });
    }
  }, []);

  useEffect(() => {
    checkHealth();
  }, [checkHealth]);

  return {
    ...status,
    checkHealth,
  };
}
