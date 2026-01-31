import { useState } from "react"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { AppLayout, AppContent } from "@/components/layout/app-layout"
import { AppHeader } from "@/components/layout/app-header"
import { ChatHistoryTab } from "@/components/features/chat-history/chat-history-tab"
import { WorkingMemoryTab } from "@/components/features/working-memory/working-memory-tab"
import { LongTermMemoryTab } from "@/components/features/long-term-memory/long-term-memory-tab"
import { SettingsTab } from "@/components/features/settings/settings-tab"
import { McpTab } from "@/components/features/mcp"
import { ConfirmDialog } from "@/components/ui/confirm-dialog"
import { ToastProvider } from "@/hooks/use-toast"
import { useHealth } from "@/hooks/use-health"
import "@/styles/globals.css"
import 'classic-stylesheets/layout.css';
import 'classic-stylesheets/themes/macos9/theme.css';
import 'classic-stylesheets/themes/macos9/skins/bubbles.css';

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
        title="Wenko Assistant"
        online={online}
        checking={checking}
      />
      <AppContent>
        <Tabs
          value={activeTab}
          onValueChange={setActiveTab}
          className="h-full flex flex-col"
        >
          <TabsList className="w-full justify-start">
            <TabsTrigger value="chatHistory">聊天历史</TabsTrigger>
            <TabsTrigger value="workingMemory">工作记忆</TabsTrigger>
            <TabsTrigger value="longTermMemory">长期记忆</TabsTrigger>
            <TabsTrigger value="mcpServices">MCP 服务</TabsTrigger>
            <TabsTrigger value="settings">设置</TabsTrigger>
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
          <TabsContent value="mcpServices" className="flex-1">
            <McpTab onConfirmDialog={handleConfirmDialog} />
          </TabsContent>
          <TabsContent value="settings" className="flex-1">
            <SettingsTab onConfirmDialog={handleConfirmDialog} />
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
