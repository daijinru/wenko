import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import { useWorkingMemory } from "@/hooks/use-working-memory"
import { MemoryList } from "./memory-list"
import { TransferDialog } from "./transfer-dialog"
import { SaveMemoryDialog } from "@/components/features/chat-history/save-memory-dialog"
import type { WorkingMemory, ChatMessage } from "@/types/api"

interface ConfirmDialogState {
  open: boolean
  title: string
  content: string
  onConfirm: () => void
}

interface WorkingMemoryTabProps {
  onConfirmDialog: (state: ConfirmDialogState) => void
}

export function WorkingMemoryTab({ onConfirmDialog }: WorkingMemoryTabProps) {
  const {
    memories,
    loading,
    expandedSessionId,
    expandedMessages,
    messagesLoading,
    loadMemories,
    clearMemory,
    toggleExpand,
  } = useWorkingMemory()

  const [transferDialogOpen, setTransferDialogOpen] = useState(false)
  const [selectedMemory, setSelectedMemory] = useState<WorkingMemory | null>(null)

  const [saveDialogOpen, setSaveDialogOpen] = useState(false)
  const [selectedMessage, setSelectedMessage] = useState<ChatMessage | null>(null)

  useEffect(() => {
    loadMemories()
  }, [loadMemories])

  const handleClearMemory = (sessionId: string) => {
    onConfirmDialog({
      open: true,
      title: "确认清除",
      content: "确定要清除这个会话的工作记忆吗？",
      onConfirm: () => clearMemory(sessionId),
    })
  }

  const handleTransfer = (memory: WorkingMemory) => {
    setSelectedMemory(memory)
    setTransferDialogOpen(true)
  }

  const handleSaveMessage = (message: ChatMessage) => {
    setSelectedMessage(message)
    setSaveDialogOpen(true)
  }

  return (
    <div className="h-full flex flex-col">
      <div className="flex gap-1 !mb-1 !mt-1 !px-1 flex-wrap">
        <Button size="sm" onClick={loadMemories} disabled={loading}>
          {loading ? "加载中..." : "刷新列表"}
        </Button>
      </div>

      <div className="flex-1 min-h-0 flex flex-col">
        <MemoryList
          memories={memories}
          loading={loading}
          expandedSessionId={expandedSessionId}
          expandedMessages={expandedMessages}
          messagesLoading={messagesLoading}
          onToggleExpand={toggleExpand}
          onClearMemory={handleClearMemory}
          onTransfer={handleTransfer}
          onSaveMessage={handleSaveMessage}
        />
      </div>

      <TransferDialog
        open={transferDialogOpen}
        onOpenChange={setTransferDialogOpen}
        memory={selectedMemory}
      />

      <SaveMemoryDialog
        open={saveDialogOpen}
        onOpenChange={setSaveDialogOpen}
        message={selectedMessage}
      />
    </div>
  )
}
