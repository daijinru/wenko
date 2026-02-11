import { useState, useEffect, useCallback, useMemo } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useExecution } from '@/hooks/use-execution';
import { ExecutionTimeline } from './execution-timeline';
import { api } from '@/lib/api-client';
import type { ChatHistoryResponse, ChatSession } from '@/types/api';
import type { HumanExecutionState, ExecutionTimelineItem } from '@/types/execution';

interface ConfirmDialogState {
  open: boolean;
  title: string;
  content: string;
  onConfirm: () => void;
}

interface ExecutionTabProps {
  onConfirmDialog: (state: ConfirmDialogState) => void;
}

/** Convert a realtime SSE event to a timeline item for unified display. */
function eventToTimelineItem(event: HumanExecutionState): ExecutionTimelineItem {
  return {
    行动: event.行动,
    状态: event.新状态,
    是否已结束: event.是否已结束,
    是否不可逆: event.是否不可逆,
    结果: null,
    错误: null,
  };
}

/**
 * Deduplicate realtime events: keep only the latest state per action name,
 * and skip intermediate non-terminal states for the same action.
 */
function deduplicateEvents(events: HumanExecutionState[]): HumanExecutionState[] {
  const latest = new Map<string, HumanExecutionState>();
  for (const e of events) {
    latest.set(e.行动, e);
  }
  return Array.from(latest.values());
}

function CurrentActionBar({ action }: { action: HumanExecutionState }) {
  const dotColor = action.是否需要关注
    ? 'bg-amber-500'
    : 'bg-blue-500 animate-pulse';

  const text = action.新状态 === '准备中'
    ? `${action.行动}——准备中`
    : `正在${action.行动}……`;

  return (
    <div className="flex items-center gap-2 px-3 py-2 bg-blue-50 border border-blue-200 rounded-md text-sm">
      <span className={`inline-block w-2 h-2 rounded-full ${dotColor}`} />
      <span>{text}</span>
      {action.是否需要关注 && <Badge variant="orange">需要关注</Badge>}
    </div>
  );
}

export function ExecutionTab({ onConfirmDialog: _onConfirmDialog }: ExecutionTabProps) {
  const {
    timelineItems,
    currentAction,
    realtimeEvents,
    summary,
    loading,
    error,
    fetchTimeline,
    clearRealtimeEvents,
  } = useExecution();

  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [sessionsLoading, setSessionsLoading] = useState(true);

  const loadSessions = useCallback(async () => {
    setSessionsLoading(true);
    try {
      const data = await api.get<ChatHistoryResponse>('/chat/history');
      const list = data.sessions || [];
      setSessions(list);
      if (!selectedSessionId && list.length > 0) {
        setSelectedSessionId(list[0].id);
      }
    } catch {
      // Silently handle — sessions may not be available
    } finally {
      setSessionsLoading(false);
    }
  }, [selectedSessionId]);

  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  useEffect(() => {
    if (selectedSessionId) {
      fetchTimeline(selectedSessionId);
    }
  }, [selectedSessionId, fetchTimeline]);

  const handleRefresh = useCallback(() => {
    if (selectedSessionId) {
      fetchTimeline(selectedSessionId);
    }
  }, [selectedSessionId, fetchTimeline]);

  // Merge HTTP timeline items with realtime IPC events for unified display.
  // Realtime events cover actions not persisted to checkpoint (e.g. MCP tool calls).
  const mergedItems = useMemo<ExecutionTimelineItem[]>(() => {
    const fromApi = timelineItems;
    const apiActions = new Set(fromApi.map(item => item.行动));
    // Only add realtime events whose action is not already in the API response
    const dedupedEvents = deduplicateEvents(realtimeEvents);
    const fromRealtime = dedupedEvents
      .filter(e => !apiActions.has(e.行动))
      .map(eventToTimelineItem);
    return [...fromApi, ...fromRealtime];
  }, [timelineItems, realtimeEvents]);

  const effectiveSummary = useMemo(() => {
    if (summary) return summary;
    if (mergedItems.length === 0) return null;
    return {
      total: mergedItems.length,
      finished: mergedItems.filter(i => i.是否已结束).length,
      inProgress: mergedItems.filter(i => !i.是否已结束).length,
      hasIrreversible: mergedItems.some(i => i.是否不可逆),
    };
  }, [summary, mergedItems]);

  if (sessionsLoading) {
    return (
      <div className="h-full flex items-center justify-center">
        <p className="text-muted-foreground">加载会话列表...</p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Toolbar */}
      <div className="flex gap-2 flex-wrap items-center !p-1 bg-slate-50 border border-slate-200 rounded-lg shadow-sm">
        <div className="flex gap-1.5 items-center border-r border-slate-300 pr-3 mr-1">
          <Button size="sm" onClick={handleRefresh} disabled={loading || !selectedSessionId} className="!h-3">
            刷新
          </Button>
          {realtimeEvents.length > 0 && (
            <Button size="sm" variant="outline" onClick={clearRealtimeEvents} className="!h-3">
              清除实时
            </Button>
          )}
        </div>

        <select
          className="!h-3 px-3 border border-slate-300 rounded-md text-sm bg-white hover:border-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors min-w-[180px]"
          value={selectedSessionId || ''}
          onChange={(e) => setSelectedSessionId(e.target.value || null)}
          disabled={sessions.length === 0}
        >
          {sessions.length === 0 ? (
            <option value="">无可用会话</option>
          ) : (
            sessions.map((s) => (
              <option key={s.id} value={s.id}>
                {s.title || s.id.slice(0, 8)} ({s.message_count} 条消息)
              </option>
            ))
          )}
        </select>

        {effectiveSummary && (
          <div className="ml-auto flex items-center gap-2 text-sm">
            <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded-md font-medium">
              {effectiveSummary.total} 个行动
            </span>
            {effectiveSummary.inProgress > 0 && (
              <Badge variant="blue">{effectiveSummary.inProgress} 进行中</Badge>
            )}
            {effectiveSummary.hasIrreversible && (
              <Badge variant="orange">含不可撤销</Badge>
            )}
          </div>
        )}
      </div>

      {/* Current action bar (real-time from IPC) */}
      {currentAction && <CurrentActionBar action={currentAction} />}

      {/* Error */}
      {error && (
        <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm flex items-center gap-2">
          <span className="text-red-500">!</span>
          {error}
        </div>
      )}

      {/* Timeline content */}
      <div className="flex-1 min-h-0 border border-slate-200 rounded-lg shadow-sm overflow-auto bg-white p-2">
        {loading ? (
          <div className="h-full flex flex-col items-center justify-center text-slate-400 gap-2">
            <span>加载执行历史...</span>
          </div>
        ) : !selectedSessionId ? (
          <div className="h-full flex flex-col items-center justify-center text-slate-400 gap-2">
            <span>请选择一个会话</span>
          </div>
        ) : mergedItems.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-slate-400 gap-2">
            <span>暂无执行记录</span>
          </div>
        ) : (
          <ExecutionTimeline items={mergedItems} />
        )}
      </div>
    </div>
  );
}
