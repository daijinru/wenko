import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Spinner } from "@/components/ui/spinner"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { formatTime } from "@/lib/utils"
import type { WorkingMemory, ChatMessage } from "@/types/api"
import { MemoryDrilldown } from "./memory-drilldown"

interface MemoryListProps {
  memories: WorkingMemory[]
  loading: boolean
  expandedSessionId: string | null
  expandedMessages: ChatMessage[]
  messagesLoading: boolean
  onToggleExpand: (sessionId: string) => void
  onClearMemory: (sessionId: string) => void
  onTransfer: (memory: WorkingMemory) => void
  onSaveMessage: (message: ChatMessage) => void
}

export function MemoryList({
  memories,
  loading,
  expandedSessionId,
  expandedMessages,
  messagesLoading,
  onToggleExpand,
  onClearMemory,
  onTransfer,
  onSaveMessage,
}: MemoryListProps) {
  if (loading) {
    return (
      <div className="flex items-center justify-center h-32">
        <Spinner />
      </div>
    )
  }

  if (memories.length === 0) {
    return (
      <Alert variant="info">
        <AlertDescription>暂无活跃会话</AlertDescription>
      </Alert>
    )
  }

  return (
    <div className="border-classic-inset bg-card overflow-y-auto flex-1 min-h-0">
      {memories.map((wm) => (
        <div key={wm.session_id} className="p-2 border-b border-muted">
          {/* Header */}
          <div className="flex items-center gap-2 flex-wrap">
            <Button
              variant="ghost"
              size="sm"
              className="p-0 h-auto"
              onClick={() => onToggleExpand(wm.session_id)}
            >
              {expandedSessionId === wm.session_id ? "▼" : "▶"}
            </Button>
            <span
              className="font-bold text-xs cursor-pointer hover:underline"
              onClick={() => onToggleExpand(wm.session_id)}
            >
              会话: {wm.session_id.substring(0, 8)}...
            </span>
            {wm.last_emotion && (
              <Badge variant="cyan">{wm.last_emotion}</Badge>
            )}
            <Badge variant="blue">轮次: {wm.turn_count}</Badge>
            <div className="ml-auto flex gap-1">
              <Button size="sm" onClick={() => onTransfer(wm)}>
                保存到长期记忆
              </Button>
              <Button
                variant="destructive"
                size="sm"
                onClick={() => onClearMemory(wm.session_id)}
              >
                清除
              </Button>
            </div>
          </div>

          {/* Info */}
          <div className="grid grid-cols-[100px_1fr] gap-x-2 gap-y-1 text-xs mt-2">
            <span className="font-bold text-muted-foreground">当前话题:</span>
            <span className="font-mono">{wm.current_topic || "(无)"}</span>
            <span className="font-bold text-muted-foreground">更新时间:</span>
            <span className="font-mono">{formatTime(wm.updated_at)}</span>
          </div>

          {/* Context variables */}
          {Object.keys(wm.context_variables || {}).length > 0 && (
            <div className="mt-2">
              <span className="font-bold text-xs text-muted-foreground">
                上下文变量:
              </span>
              <div className="mt-1 p-2 bg-muted border border-border text-xs font-mono whitespace-pre-wrap">
                {JSON.stringify(wm.context_variables, null, 2)}
              </div>
            </div>
          )}

          {/* Drilldown */}
          {expandedSessionId === wm.session_id && (
            <MemoryDrilldown
              messages={expandedMessages}
              loading={messagesLoading}
              onSaveMessage={onSaveMessage}
            />
          )}
        </div>
      ))}
    </div>
  )
}
