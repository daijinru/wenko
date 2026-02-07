import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import { useLongTermMemory } from "@/hooks/use-long-term-memory"
import type { MemoryOrderBy } from "@/hooks/use-long-term-memory"
import { MemoryFilter } from "./memory-filter"
import { LongTermMemoryList } from "./memory-list"
import { MemoryFormDialog } from "./memory-form-dialog"
import { cn } from "@/lib/utils"
import type { LongTermMemory, MemoryFormData } from "@/types/api"

interface ConfirmDialogState {
  open: boolean
  title: string
  content: string
  onConfirm: () => void
}

interface LongTermMemoryTabProps {
  onConfirmDialog: (state: ConfirmDialogState) => void
}

const SORT_OPTIONS: { key: MemoryOrderBy; label: string }[] = [
  { key: "created_at", label: "创建时间" },
  { key: "access_count", label: "访问次数" },
  { key: "last_accessed", label: "最后访问" },
]

function MemorySortBar({
  currentOrder,
  onOrderChange,
}: {
  currentOrder: MemoryOrderBy
  onOrderChange: (order: MemoryOrderBy) => void
}) {
  return (
    <div className="flex items-center gap-2 bg-secondary border-classic-inset !p-1">
      <span className="text-[11px] font-bold">排序:</span>
      <div className="flex gap-0.5">
        {SORT_OPTIONS.map((item) => (
          <button
            key={item.key}
            className={cn(
              "px-2 py-0.5 text-[11px] border border-border cursor-pointer transition-colors",
              currentOrder === item.key
                ? "bg-primary text-primary-foreground border-primary"
                : "bg-secondary hover:bg-accent"
            )}
            onClick={() => onOrderChange(item.key)}
          >
            {item.label}
          </button>
        ))}
      </div>
    </div>
  )
}

export function LongTermMemoryTab({ onConfirmDialog }: LongTermMemoryTabProps) {
  const {
    memories,
    total,
    loading,
    categoryFilter,
    orderBy,
    selectedIds,
    loadMemories,
    createMemory,
    updateMemory,
    deleteMemory,
    batchDelete,
    clearAll,
    exportMemories,
    toggleSelect,
    setFilter,
    setOrderBy,
  } = useLongTermMemory()

  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingMemory, setEditingMemory] = useState<LongTermMemory | null>(null)

  useEffect(() => {
    loadMemories()
  }, [loadMemories])

  const handleAddMemory = () => {
    setEditingMemory(null)
    setDialogOpen(true)
  }

  const handleEditMemory = (memory: LongTermMemory) => {
    setEditingMemory(memory)
    setDialogOpen(true)
  }

  const handleDeleteMemory = (id: string) => {
    onConfirmDialog({
      open: true,
      title: "确认删除",
      content: "确定要删除这条记忆吗？",
      onConfirm: () => deleteMemory(id),
    })
  }

  const handleBatchDelete = () => {
    onConfirmDialog({
      open: true,
      title: "确认批量删除",
      content: `确定要删除选中的 ${selectedIds.length} 条记忆吗？`,
      onConfirm: batchDelete,
    })
  }

  const handleClearAll = () => {
    onConfirmDialog({
      open: true,
      title: "确认清空",
      content: "确定要清空所有长期记忆吗？此操作不可恢复！",
      onConfirm: clearAll,
    })
  }

  const handleSave = async (data: MemoryFormData): Promise<boolean> => {
    if (editingMemory) {
      return updateMemory(editingMemory.id, data)
    } else {
      return createMemory({ ...data, source: "user_stated" })
    }
  }

  return (
    <div className="h-full flex flex-col">
      <div className="flex gap-1 !mb-1 !mt-1 !px-1 flex-wrap">
        <Button size="sm" onClick={() => loadMemories()} disabled={loading}>
          {loading ? "加载中..." : "刷新列表"}
        </Button>
        <Button size="sm" onClick={handleAddMemory}>
          添加记忆
        </Button>
        <Button size="sm" onClick={exportMemories}>
          导出 JSON
        </Button>
        <Button
          variant="destructive"
          size="sm"
          onClick={handleBatchDelete}
          disabled={selectedIds.length === 0}
        >
          批量删除 ({selectedIds.length})
        </Button>
        <Button
          variant="destructive"
          size="sm"
          onClick={handleClearAll}
          disabled={memories.length === 0}
        >
          清空所有
        </Button>
      </div>

      <MemoryFilter
        currentFilter={categoryFilter}
        total={total}
        onFilterChange={setFilter}
      />

      <MemorySortBar currentOrder={orderBy} onOrderChange={setOrderBy} />

      <div className="flex-1 min-h-0 flex flex-col">
        <LongTermMemoryList
          memories={memories}
          loading={loading}
          selectedIds={selectedIds}
          onToggleSelect={toggleSelect}
          onEdit={handleEditMemory}
          onDelete={handleDeleteMemory}
        />
      </div>

      <MemoryFormDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        memory={editingMemory}
        onSave={handleSave}
      />
    </div>
  )
}
