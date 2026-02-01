import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Spinner } from "@/components/ui/spinner"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { formatTime, cn } from "@/lib/utils"
import type { ChatMessage } from "@/types/api"

interface MemoryDrilldownProps {
  messages: ChatMessage[]
  loading: boolean
  onSaveMessage: (message: ChatMessage) => void
}

export function MemoryDrilldown({
  messages,
  loading,
  onSaveMessage,
}: MemoryDrilldownProps) {
  return (
    <div className="mt-3 pl-5">
      <div className="text-[11px] font-bold text-muted-foreground mb-2">
        会话消息 (点击单条消息可保存到长期记忆)
      </div>

      {loading ? (
        <Spinner size="sm" />
      ) : messages.length === 0 ? (
        <Alert variant="info" className="text-[11px]">
          <AlertDescription>该会话暂无消息</AlertDescription>
        </Alert>
      ) : (
        <div className="border-classic-inset bg-card p-2 max-h-[300px] overflow-y-auto">
          {messages.map((msg, index) => (
            <div
              key={msg.id || index}
              className={cn(
                "mb-1.5 p-2 border-l-[3px] transition-colors hover:opacity-80",
                msg.role === "user"
                  ? "bg-blue-50 border-l-blue-500"
                  : "bg-green-50 border-l-green-500"
              )}
              // onClick={() => onSaveMessage(msg)}
              // title="点击保存到长期记忆"
            >
              <div className="flex justify-between items-center mb-1">
                <Badge
                  variant={msg.role === "user" ? "blue" : "green"}
                  className="text-[9px]"
                >
                  {msg.role === "user" ? "用户" : "AI"}
                </Badge>
                <div className="flex items-center gap-1.5">
                  <span className="text-[10px] text-muted-foreground">
                    {formatTime(msg.created_at)}
                  </span>
                  <Button
                    variant="link"
                    size="sm"
                    className="text-[10px] p-0 h-auto"
                    onClick={(e) => {
                      e.stopPropagation()
                      onSaveMessage(msg)
                    }}
                  >
                    保存
                  </Button>
                </div>
              </div>
              <div className="text-[11px] whitespace-pre-wrap break-words">
                {msg.content.length > 200
                  ? msg.content.substring(0, 200) + "..."
                  : msg.content}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
