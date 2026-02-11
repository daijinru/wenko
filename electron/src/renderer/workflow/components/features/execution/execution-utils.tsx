import { Badge } from '@/components/ui/badge';
import type { HumanExecutionState, ExecutionTimelineItem } from '@/types/execution';

/** Convert a realtime SSE event to a timeline item for unified display. */
export function eventToTimelineItem(event: HumanExecutionState): ExecutionTimelineItem {
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
export function deduplicateEvents(events: HumanExecutionState[]): HumanExecutionState[] {
  const latest = new Map<string, HumanExecutionState>();
  for (const e of events) {
    latest.set(e.行动, e);
  }
  return Array.from(latest.values());
}

/**
 * Merge HTTP timeline items with realtime IPC events for unified display.
 * Realtime events cover actions not persisted to checkpoint (e.g. MCP tool calls).
 */
export function mergeTimelineWithEvents(
  timelineItems: ExecutionTimelineItem[],
  realtimeEvents: HumanExecutionState[],
): ExecutionTimelineItem[] {
  const apiActions = new Set(timelineItems.map(item => item.行动));
  const dedupedEvents = deduplicateEvents(realtimeEvents);
  const fromRealtime = dedupedEvents
    .filter(e => !apiActions.has(e.行动))
    .map(eventToTimelineItem);
  return [...timelineItems, ...fromRealtime];
}

export function CurrentActionBar({ action }: { action: HumanExecutionState }) {
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
