import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Spinner } from "@/components/ui/spinner"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { formatTime, cn } from "@/lib/utils"
import type { ChatSession } from "@/types/api"

interface SessionListProps {
  sessions: ChatSession[]
  loading: boolean
  selectedSessionId: string | null
  onSelectSession: (sessionId: string) => void
  onDeleteSession: (sessionId: string) => void
}

export function SessionList({
  sessions,
  loading,
  selectedSessionId,
  onSelectSession,
  onDeleteSession,
}: SessionListProps) {
  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Spinner />
      </div>
    )
  }

  if (sessions.length === 0) {
    return (
      <Alert variant="info">
        <AlertDescription>暂无聊天记录</AlertDescription>
      </Alert>
    )
  }

  return (
    <div className="border-classic-inset bg-card overflow-y-auto flex-1 min-h-0">
      {sessions.map((session) => (
        <div
          key={session.id}
          className={cn(
            "p-2 border-b border-muted cursor-pointer hover:bg-primary hover:text-primary-foreground",
            selectedSessionId === session.id && "bg-primary text-primary-foreground"
          )}
          onClick={() => onSelectSession(session.id)}
        >
          <div className="flex justify-between items-start gap-2">
            <div className="flex-1 min-w-0">
              <div className="font-bold text-xs truncate">
                {session.title || "(无标题)"}
              </div>
              <div className="flex items-center gap-1.5 mt-0.5">
                <span className="text-[10px] opacity-70">
                  {formatTime(session.updated_at)}
                </span>
                <Badge variant="blue" className="text-[9px]">
                  {session.message_count} 条
                </Badge>
              </div>
            </div>
            <Button
              variant="destructive"
              size="sm"
              className="shrink-0"
              onClick={(e) => {
                e.stopPropagation()
                onDeleteSession(session.id)
              }}
            >
              删除
            </Button>
          </div>
        </div>
      ))}
    </div>
  )
}
