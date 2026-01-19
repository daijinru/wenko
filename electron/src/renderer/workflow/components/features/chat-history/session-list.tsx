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
    <div className="border-classic-inset bg-card overflow-y-auto flex-1 min-h-0 !p-0">
      <table className="w-full text-xs border-collapse detailed">
        <thead className="bg-muted sticky top-0 z-10 font-bold text-muted-foreground">
          <tr>
            <th className="p-2 text-left border-b border-r border-border whitespace-nowrap">标题</th>
            <th className="p-2 text-left border-b border-r border-border whitespace-nowrap w-24">时间</th>
            <th className="p-2 text-center border-b border-r border-border whitespace-nowrap w-12">条数</th>
            <th className="p-2 text-center border-b border-border whitespace-nowrap w-16">操作</th>
          </tr>
        </thead>
        <tbody>
          {sessions.map((session) => (
            <tr
              key={session.id}
              className={cn(
                "cursor-pointer hover:bg-primary hover:text-primary-foreground group",
                selectedSessionId === session.id 
                  ? "bg-primary text-primary-foreground" 
                  : "even:bg-muted/30"
              )}
              onClick={() => onSelectSession(session.id)}
            >
              <td className="p-2 border-b border-r border-border truncate max-w-[150px]">
                {session.title || "(无标题)"}
              </td>
              <td className="p-2 border-b border-r border-border whitespace-nowrap text-[10px]">
                {formatTime(session.updated_at)}
              </td>
              <td className="p-2 border-b border-r border-border text-center">
                <Badge variant="outline" className={cn(
                  "text-[9px] px-1 h-4 bg-transparent border-current",
                  selectedSessionId === session.id ? "text-primary-foreground" : "text-foreground"
                )}>
                  {session.message_count}
                </Badge>
              </td>
              <td className="p-2 border-b border-border text-center">
                <Button
                  variant="destructive"
                  size="icon"
                  className="h-3 w-3 opacity-0 group-hover:opacity-100 transition-opacity !cursor-pointer"
                  onClick={(e) => {
                    e.stopPropagation()
                    onDeleteSession(session.id)
                  }}
                >
                  <span className="text-[10px]">×</span>
                </Button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
