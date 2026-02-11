import { useState, useMemo } from 'react';
import { Button } from '@/components/ui/button';
import { Spinner } from '@/components/ui/spinner';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { ExecutionTimeline } from '@/components/features/execution/execution-timeline';
import { CurrentActionBar, mergeTimelineWithEvents } from '@/components/features/execution/execution-utils';
import { useSessionExecution } from '@/hooks/use-session-execution';

interface SessionExecutionSectionProps {
  sessionId: string;
}

export function SessionExecutionSection({ sessionId }: SessionExecutionSectionProps) {
  const {
    timelineItems,
    currentAction,
    realtimeEvents,
    loading,
    error,
    refresh,
  } = useSessionExecution(sessionId);

  const [fullDialogOpen, setFullDialogOpen] = useState(false);

  const mergedItems = useMemo(
    () => mergeTimelineWithEvents(timelineItems, realtimeEvents),
    [timelineItems, realtimeEvents]
  );

  const recentItems = mergedItems.slice(-5);

  if (loading) {
    return (
      <div className="mt-3 pl-5">
        <div className="text-[10px] font-bold text-muted-foreground mb-1">当前执行</div>
        <Spinner size="sm" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="mt-3 pl-5">
        <div className="text-[10px] font-bold text-muted-foreground mb-1">当前执行</div>
        <div className="text-[10px] text-red-500">{error}</div>
      </div>
    );
  }

  if (mergedItems.length === 0 && !currentAction) {
    return null;
  }

  return (
    <div className="mt-3 pl-5">
      <div className="flex items-center gap-2 mb-1">
        <div className="text-[10px] font-bold text-muted-foreground">当前执行</div>
        <Button
          variant="link"
          size="sm"
          className="text-[10px] p-0 h-auto"
          onClick={(e) => { e.stopPropagation(); refresh(); }}
        >
          刷新
        </Button>
      </div>

      {currentAction && <CurrentActionBar action={currentAction} />}

      {recentItems.length > 0 && (
        <div className="border-classic-inset bg-card p-2 mt-1">
          <ExecutionTimeline items={recentItems} />
        </div>
      )}

      {mergedItems.length > 5 && (
        <Button
          variant="link"
          size="sm"
          className="text-[10px] p-0 h-auto mt-1"
          onClick={(e) => { e.stopPropagation(); setFullDialogOpen(true); }}
        >
          查看全部执行历史 ({mergedItems.length} 条)
        </Button>
      )}

      <Dialog open={fullDialogOpen} onOpenChange={setFullDialogOpen}>
        <DialogContent className="sm:max-w-[700px] max-h-[80vh] flex flex-col">
          <DialogHeader>
            <DialogTitle>执行历史</DialogTitle>
          </DialogHeader>
          <div className="flex-1 min-h-0 overflow-auto p-2">
            <ExecutionTimeline items={mergedItems} />
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
