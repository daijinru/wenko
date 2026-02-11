import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Spinner } from "@/components/ui/spinner"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Fragment, useState } from "react"
import { formatTime, cn } from "@/lib/utils"
import type { WorkingMemory, ChatMessage, EmotionHistoryEntry } from "@/types/api"
import { MemoryDrilldown } from "./memory-drilldown"
import { SessionExecutionSection } from "./session-execution-section"
import { ContextVariableDialog } from "./context-variable-dialog"

const EMOTION_COLORS: Record<string, string> = {
  neutral: "#9ca3af",
  happy: "#22c55e",
  excited: "#f59e0b",
  grateful: "#ec4899",
  curious: "#8b5cf6",
  sad: "#3b82f6",
  anxious: "#ef4444",
  frustrated: "#f97316",
  confused: "#6366f1",
  help_seeking: "#14b8a6",
  info_seeking: "#0ea5e9",
  validation_seeking: "#a855f7",
}

function EmotionHistory({ history }: { history: EmotionHistoryEntry[] }) {
  if (!history || history.length === 0) {
    return (
      <div className="text-[10px] text-muted-foreground px-2 py-1">
        暂无情感记录
      </div>
    )
  }

  return (
    <div className="flex flex-wrap gap-1 px-2 py-1">
      {history.map((entry, idx) => (
        <div
          key={idx}
          className="flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded bg-muted/50 border border-border"
        >
          <span
            className="inline-block w-2 h-2 rounded-full flex-shrink-0"
            style={{ backgroundColor: EMOTION_COLORS[entry.emotion] || "#9ca3af" }}
          />
          <span className="font-mono">{entry.emotion}</span>
          <span className="text-muted-foreground">{Math.round(entry.confidence * 100)}%</span>
        </div>
      ))}
    </div>
  )
}

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
  const [contextDialogOpen, setContextDialogOpen] = useState(false)
  const [selectedMemory, setSelectedMemory] = useState<WorkingMemory | null>(null)

  const handleShowContextVariables = (memory: WorkingMemory) => {
    setSelectedMemory(memory)
    setContextDialogOpen(true)
  }

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
    <div className="border-classic-inset bg-card overflow-y-auto flex-1 min-h-0 !p-0">
      <table className="w-full text-xs border-collapse detailed">
        <thead className="bg-muted sticky top-0 z-10 font-bold text-muted-foreground">
          <tr>
            <th className="p-2 text-center border-b border-r border-border whitespace-nowrap w-8"></th>
            <th className="p-2 text-left border-b border-r border-border whitespace-nowrap">会话/话题</th>
            <th className="p-2 text-left border-b border-r border-border whitespace-nowrap w-32">状态</th>
            <th className="p-2 text-left border-b border-r border-border whitespace-nowrap w-24">时间</th>
            <th className="p-2 text-center border-b border-border whitespace-nowrap w-32">操作</th>
          </tr>
        </thead>
        <tbody>
          {memories.map((wm) => {
            const isExpanded = expandedSessionId === wm.session_id
            return (
              <Fragment key={wm.session_id}>
                <tr
                  className={cn(
                    "cursor-pointer hover:bg-primary hover:text-primary-foreground group transition-colors",
                    isExpanded ? "bg-muted/50" : "even:bg-muted/30"
                  )}
                  onClick={() => onToggleExpand(wm.session_id)}
                >
                  <td className="p-2 border-b border-r border-border text-center">
                    <span className="text-[10px]">{isExpanded ? "▼" : "▶"}</span>
                  </td>
                  <td className="p-2 border-b border-r border-border truncate max-w-[200px]">
                    <div className="font-bold font-mono" title={wm.session_id}>{wm.session_id.substring(0, 12)}...</div>
                    <div className="text-[10px] opacity-80 truncate" title={wm.current_topic || undefined}>
                      {wm.current_topic || "(无话题)"}
                    </div>
                  </td>
                  <td className="p-2 border-b border-r border-border">
                    <div className="flex gap-1 flex-wrap">
                      {wm.last_emotion && (
                        <Badge variant="cyan" className="text-[9px] px-1 h-4">
                          {wm.last_emotion}
                        </Badge>
                      )}
                      <Badge variant="blue" className="text-[9px] px-1 h-4">
                        {wm.turn_count}轮
                      </Badge>
                    </div>
                  </td>
                  <td className="p-2 border-b border-r border-border whitespace-nowrap text-[10px]">
                    {formatTime(wm.updated_at)}
                  </td>
                  <td className="p-2 border-b border-border text-center">
                    <div className="flex justify-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      <Button
                        size="sm"
                        variant="ghost"
                        className="h-3 text-[10px] px-2 bg-background/50 hover:bg-background text-foreground"
                        onClick={(e) => {
                          e.stopPropagation()
                          onTransfer(wm)
                        }}
                      >
                        保存
                      </Button>
                      <Button
                        variant="destructive"
                        size="sm"
                        className="h-3 text-[10px] px-2"
                        onClick={(e) => {
                          e.stopPropagation()
                          onClearMemory(wm.session_id)
                        }}
                      >
                        清除
                      </Button>
                      {Object.keys(wm.context_variables || {}).length > 0 && (
                        <Button
                          size="sm"
                          variant="outline"
                          className="h-3 text-[10px] px-2"
                          onClick={(e) => {
                            e.stopPropagation()
                            handleShowContextVariables(wm)
                          }}
                        >
                          采集数据
                        </Button>
                      )}
                    </div>
                  </td>
                </tr>
                {isExpanded && (
                  <tr className="bg-background/50">
                    <td colSpan={5} className="p-0 border-b border-border">
                      <div className="p-4">
                        {/* Emotion History */}
                        {wm.emotion_history && wm.emotion_history.length > 0 && (
                          <div className="!mb-1">
                            <div className="text-[10px] font-bold text-muted-foreground !mb-1 px-2">
                              情感历史
                            </div>
                            <EmotionHistory history={wm.emotion_history} />
                          </div>
                        )}
                        {/* Execution State */}
                        <div className="!mb-1">
                          <SessionExecutionSection sessionId={wm.session_id} />
                        </div>
                        {/* Drilldown */}
                        <MemoryDrilldown
                          messages={expandedMessages}
                          loading={messagesLoading}
                          onSaveMessage={onSaveMessage}
                        />
                      </div>
                    </td>
                  </tr>
                )}
              </Fragment>
            )
          })}
        </tbody>
      </table>

      {/* Context Variable Dialog */}
      <ContextVariableDialog
        open={contextDialogOpen}
        onOpenChange={setContextDialogOpen}
        memory={selectedMemory}
      />
    </div>
  )
}
