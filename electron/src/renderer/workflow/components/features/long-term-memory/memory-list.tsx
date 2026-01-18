import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Checkbox } from "@/components/ui/checkbox"
import { Spinner } from "@/components/ui/spinner"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { formatTime } from "@/lib/utils"
import type { LongTermMemory, MemoryCategory } from "@/types/api"

interface MemoryListProps {
  memories: LongTermMemory[]
  loading: boolean
  selectedIds: string[]
  onToggleSelect: (id: string) => void
  onEdit: (memory: LongTermMemory) => void
  onDelete: (id: string) => void
}

const CATEGORY_VARIANTS: Record<MemoryCategory, "blue" | "green" | "orange"> = {
  preference: "blue",
  fact: "green",
  pattern: "orange",
}

export function LongTermMemoryList({
  memories,
  loading,
  selectedIds,
  onToggleSelect,
  onEdit,
  onDelete,
}: MemoryListProps) {
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
        <AlertDescription>暂无记忆数据</AlertDescription>
      </Alert>
    )
  }

  return (
    <div className="border-classic-inset bg-card overflow-y-auto flex-1 min-h-0">
      {memories.map((memory) => (
        <div key={memory.id} className="p-2 border-b border-muted">
          {/* Header */}
          <div className="flex items-center gap-2 flex-wrap">
            <Checkbox
              checked={selectedIds.includes(memory.id)}
              onCheckedChange={() => onToggleSelect(memory.id)}
            />
            <Badge variant={CATEGORY_VARIANTS[memory.category]}>
              {memory.category}
            </Badge>
            <span className="font-bold text-xs">{memory.key}</span>
            <Badge variant="cyan">
              置信度: {Math.round(memory.confidence * 100)}%
            </Badge>
            <span className="text-[10px] px-1.5 py-0.5 bg-muted border border-border text-muted-foreground">
              {memory.source}
            </span>
            <div className="ml-auto flex gap-1">
              <Button size="sm" onClick={() => onEdit(memory)}>
                编辑
              </Button>
              <Button
                variant="destructive"
                size="sm"
                onClick={() => onDelete(memory.id)}
              >
                删除
              </Button>
            </div>
          </div>

          {/* Value */}
          <div className="mt-1 p-2 bg-muted border border-border text-xs font-mono whitespace-pre-wrap break-words">
            {typeof memory.value === "object"
              ? JSON.stringify(memory.value, null, 2)
              : memory.value}
          </div>

          {/* Meta */}
          <div className="flex gap-3 mt-1 text-[10px] text-muted-foreground">
            <span>访问 {memory.access_count} 次</span>
            <span>创建: {formatTime(memory.created_at)}</span>
            <span>最后访问: {formatTime(memory.last_accessed)}</span>
          </div>
        </div>
      ))}
    </div>
  )
}
