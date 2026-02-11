import { useState, useEffect, useCallback } from 'react';
import { api, ApiError } from '@/lib/api-client';
import { useToast } from '@/hooks/use-toast';
import type {
  HumanExecutionState,
  ExecutionTimeline,
  ExecutionTimelineItem,
} from '@/types/execution';

interface UseExecutionState {
  /** Timeline items from HTTP API. */
  timelineItems: ExecutionTimelineItem[];
  /** Most recent non-terminal action from IPC. */
  currentAction: HumanExecutionState | null;
  /** All IPC events received (for real-time display). */
  realtimeEvents: HumanExecutionState[];
  /** Timeline summary stats. */
  summary: { total: number; finished: number; inProgress: number; hasIrreversible: boolean } | null;
  loading: boolean;
  error: string | null;
}

export function useExecution() {
  const { toast } = useToast();
  const [state, setState] = useState<UseExecutionState>({
    timelineItems: [],
    currentAction: null,
    realtimeEvents: [],
    summary: null,
    loading: false,
    error: null,
  });

  // Listen to IPC execution-state-update events from Live2D window
  useEffect(() => {
    if (!window.electronAPI?.on) return;

    const unsubscribe = window.electronAPI.on('execution-state-update', (...args: unknown[]) => {
      const data = args[0] as HumanExecutionState;
      if (!data || !data.行动) return;

      setState(prev => {
        const newEvents = [...prev.realtimeEvents, data];
        const currentAction = data.是否已结束 ? null : data;
        return { ...prev, realtimeEvents: newEvents, currentAction };
      });
    });

    return () => { unsubscribe(); };
  }, []);

  const fetchTimeline = useCallback(async (sessionId: string) => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    try {
      const data = await api.get<ExecutionTimeline>(
        `/api/execution/${sessionId}/timeline`,
        { human: 'true' }
      );
      setState(prev => ({
        ...prev,
        timelineItems: data.行动列表 || [],
        summary: {
          total: data.总数,
          finished: data.已结束,
          inProgress: data.进行中,
          hasIrreversible: data.含不可逆操作,
        },
        loading: false,
      }));
    } catch (error) {
      // 404 means no execution data for this session — treat as empty, not error
      if (error instanceof ApiError && error.status === 404) {
        setState(prev => ({
          ...prev,
          timelineItems: [],
          summary: null,
          loading: false,
          error: null,
        }));
        return;
      }
      const message = error instanceof ApiError ? error.message : '加载执行历史失败';
      setState(prev => ({ ...prev, loading: false, error: message }));
      toast.error(message);
    }
  }, [toast]);

  const refresh = useCallback(async (sessionId: string) => {
    await fetchTimeline(sessionId);
  }, [fetchTimeline]);

  const clearRealtimeEvents = useCallback(() => {
    setState(prev => ({ ...prev, realtimeEvents: [], currentAction: null }));
  }, []);

  return {
    ...state,
    fetchTimeline,
    refresh,
    clearRealtimeEvents,
  };
}
