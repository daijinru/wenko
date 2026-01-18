import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import { useChatSessions } from "@/hooks/use-chat-sessions"
import { SessionList } from "./session-list"
import { MessageDetail } from "./message-detail"
import { SaveMemoryDialog } from "./save-memory-dialog"
import type { ChatMessage } from "@/types/api"

interface ConfirmDialogState {
  open: boolean
  title: string
  content: string
  onConfirm: () => void
}

interface ChatHistoryTabProps {
  onConfirmDialog: (state: ConfirmDialogState) => void
}

export function ChatHistoryTab({ onConfirmDialog }: ChatHistoryTabProps) {
  const {
    sessions,
    loading,
    selectedSessionId,
    messages,
    messagesLoading,
    loadSessions,
    loadSessionMessages,
    deleteSession,
    clearAllSessions,
  } = useChatSessions()

  const [saveDialogOpen, setSaveDialogOpen] = useState(false)
  const [selectedMessage, setSelectedMessage] = useState<ChatMessage | null>(null)

  useEffect(() => {
    loadSessions()
  }, [loadSessions])

  const handleDeleteSession = (sessionId: string) => {
    onConfirmDialog({
      open: true,
      title: "确认删除",
      content: "确定要删除这个聊天会话吗？所有消息将被永久删除。",
      onConfirm: () => deleteSession(sessionId),
    })
  }

  const handleClearAll = () => {
    onConfirmDialog({
      open: true,
      title: "确认清空",
      content: "确定要清空所有聊天记录吗？此操作不可恢复！",
      onConfirm: clearAllSessions,
    })
  }

  const handleSaveAsMemory = (message: ChatMessage) => {
    setSelectedMessage(message)
    setSaveDialogOpen(true)
  }

  return (
    <div className="h-full flex flex-col">
      <h4 className="text-xs font-bold mb-2 pb-1 border-b border-border">
        聊天记录
      </h4>

      <div className="flex gap-1 mb-3 flex-wrap">
        <Button size="sm" onClick={loadSessions} disabled={loading}>
          {loading ? "加载中..." : "刷新列表"}
        </Button>
        <Button
          variant="destructive"
          size="sm"
          onClick={handleClearAll}
          disabled={sessions.length === 0}
        >
          清空所有记录
        </Button>
      </div>

      <div className="flex-1 flex gap-3 min-h-0">
        <div className="w-2/5 min-w-[280px] flex flex-col min-h-0">
          <h5 className="text-xs font-bold mb-2 shrink-0">会话列表</h5>
          <SessionList
            sessions={sessions}
            loading={loading}
            selectedSessionId={selectedSessionId}
            onSelectSession={loadSessionMessages}
            onDeleteSession={handleDeleteSession}
          />
        </div>

        <div className="flex-1 min-w-[350px] flex flex-col min-h-0">
          <h5 className="text-xs font-bold mb-2 shrink-0">消息详情</h5>
          <MessageDetail
            selectedSessionId={selectedSessionId}
            messages={messages}
            loading={messagesLoading}
            onSaveAsMemory={handleSaveAsMemory}
          />
        </div>
      </div>

      <SaveMemoryDialog
        open={saveDialogOpen}
        onOpenChange={setSaveDialogOpen}
        message={selectedMessage}
      />
    </div>
  )
}
