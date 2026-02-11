import { useState, useEffect, useCallback } from 'react';
import { api, ApiError } from '@/lib/api-client';
import type {
  HumanExecutionState,
  ExecutionTimeline,
  ExecutionTimelineItem,
} from '@/types/execution';

export function useSessionExecution(sessionId: string | null) {
  const [timelineItems, setTimelineItems] = useState<ExecutionTimelineItem[]>([]);
  const [currentAction, setCurrentAction] = useState<HumanExecutionState | null>(null);
  const [realtimeEvents, setRealtimeEvents] = useState<HumanExecutionState[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchTimeline = useCallback(async (sid: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.get<ExecutionTimeline>(
        `/api/execution/${sid}/timeline`,
        { human: 'true' }
      );
      setTimelineItems(data.行动列表 || []);
      setLoading(false);
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setTimelineItems([]);
        setLoading(false);
        return;
      }
      const message = err instanceof ApiError ? err.message : '加载执行历史失败';
      setError(message);
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (sessionId) {
      fetchTimeline(sessionId);
    } else {
      setTimelineItems([]);
      setError(null);
    }
  }, [sessionId, fetchTimeline]);

  // IPC listener — events are ambient (no session_id), shown for the expanded session
  useEffect(() => {
    if (!window.electronAPI?.on) return;
    const unsubscribe = window.electronAPI.on('execution-state-update', (...args: unknown[]) => {
      const data = args[0] as HumanExecutionState;
      if (!data || !data.行动) return;
      setRealtimeEvents(prev => [...prev, data]);
      setCurrentAction(data.是否已结束 ? null : data);
    });
    return () => { unsubscribe(); };
  }, []);

  const clearRealtimeEvents = useCallback(() => {
    setRealtimeEvents([]);
    setCurrentAction(null);
  }, []);

  const refresh = useCallback(() => {
    if (sessionId) fetchTimeline(sessionId);
  }, [sessionId, fetchTimeline]);

  return {
    timelineItems,
    currentAction,
    realtimeEvents,
    loading,
    error,
    refresh,
    clearRealtimeEvents,
  };
}
