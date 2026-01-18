import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Spinner } from "@/components/ui/spinner"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { formatTime, cn } from "@/lib/utils"
import type { ChatMessage } from "@/types/api"

interface MessageDetailProps {
  selectedSessionId: string | null
  messages: ChatMessage[]
  loading: boolean
  onSaveAsMemory: (message: ChatMessage) => void
}

export function MessageDetail({
  selectedSessionId,
  messages,
  loading,
  onSaveAsMemory,
}: MessageDetailProps) {
  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Spinner />
      </div>
    )
  }

  if (!selectedSessionId) {
    return (
      <Alert variant="info">
        <AlertDescription>请选择一个会话查看详情</AlertDescription>
      </Alert>
    )
  }

  if (messages.length === 0) {
    return (
      <Alert variant="info">
        <AlertDescription>该会话暂无消息</AlertDescription>
      </Alert>
    )
  }

  return (
    <div className="border-classic-inset bg-card p-2 overflow-y-auto flex-1 min-h-0">
      {messages.map((msg, index) => (
        <div
          key={msg.id || index}
          className={cn(
            "mb-2 p-2 border-l-[3px]",
            msg.role === "user"
              ? "bg-blue-50 border-l-blue-500"
              : "bg-green-50 border-l-green-500"
          )}
        >
          <div className="flex justify-between items-center mb-1">
            <Badge variant={msg.role === "user" ? "blue" : "green"}>
              {msg.role === "user" ? "用户" : "AI"}
            </Badge>
            <div className="flex items-center gap-2">
              <span className="text-[10px] text-muted-foreground">
                {formatTime(msg.created_at)}
              </span>
              <Button
                variant="link"
                size="sm"
                className="text-[10px] p-0 h-auto"
                onClick={() => onSaveAsMemory(msg)}
              >
                保存为记忆
              </Button>
            </div>
          </div>
          <div className="text-xs whitespace-pre-wrap break-words">
            {msg.content}
          </div>
        </div>
      ))}
    </div>
  )
}
