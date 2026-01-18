import { useState } from "react"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { AppLayout, AppContent } from "@/components/layout/app-layout"
import { AppHeader } from "@/components/layout/app-header"
import { ChatHistoryTab } from "@/components/features/chat-history/chat-history-tab"
import { WorkingMemoryTab } from "@/components/features/working-memory/working-memory-tab"
import { LongTermMemoryTab } from "@/components/features/long-term-memory/long-term-memory-tab"
import { ConfirmDialog } from "@/components/ui/confirm-dialog"
import { ToastProvider } from "@/hooks/use-toast"
import { useHealth } from "@/hooks/use-health"
import "@/styles/globals.css"

interface ConfirmDialogState {
  open: boolean
  title: string
  content: string
  onConfirm: () => void
}

function AppInner() {
  const { online, checking } = useHealth()
  const [activeTab, setActiveTab] = useState("chatHistory")
  const [confirmDialog, setConfirmDialog] = useState<ConfirmDialogState>({
    open: false,
    title: "",
    content: "",
    onConfirm: () => {},
  })

  const handleConfirmDialog = (state: ConfirmDialogState) => {
    setConfirmDialog(state)
  }

  return (
    <AppLayout className="theme-classic">
      <AppHeader
        title="Emotion & Memory System"
        online={online}
        checking={checking}
      />
      <AppContent>
        <Tabs
          value={activeTab}
          onValueChange={setActiveTab}
          orientation="vertical"
          className="h-full flex"
        >
          <TabsList className="w-[120px] min-w-[120px] shrink-0">
            <TabsTrigger value="chatHistory">聊天历史</TabsTrigger>
            <TabsTrigger value="workingMemory">工作记忆</TabsTrigger>
            <TabsTrigger value="longTermMemory">长期记忆</TabsTrigger>
          </TabsList>
          <TabsContent value="chatHistory" className="flex-1">
            <ChatHistoryTab onConfirmDialog={handleConfirmDialog} />
          </TabsContent>
          <TabsContent value="workingMemory" className="flex-1">
            <WorkingMemoryTab onConfirmDialog={handleConfirmDialog} />
          </TabsContent>
          <TabsContent value="longTermMemory" className="flex-1">
            <LongTermMemoryTab onConfirmDialog={handleConfirmDialog} />
          </TabsContent>
        </Tabs>
      </AppContent>

      <ConfirmDialog
        open={confirmDialog.open}
        onOpenChange={(open) =>
          setConfirmDialog((prev) => ({ ...prev, open }))
        }
        title={confirmDialog.title}
        content={confirmDialog.content}
        onConfirm={confirmDialog.onConfirm}
      />
    </AppLayout>
  )
}

export default function App() {
  return (
    <ToastProvider>
      <AppInner />
    </ToastProvider>
  )
}
