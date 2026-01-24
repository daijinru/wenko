import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { formatTime } from "@/lib/utils"
import type { LongTermMemory, MemoryCategory } from "@/types/api"

interface MemoryDetailDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  memory: LongTermMemory | null
  onEdit: (memory: LongTermMemory) => void
}

const CATEGORY_LABELS: Record<MemoryCategory, string> = {
  preference: "偏好",
  fact: "事实",
  pattern: "模式",
  plan: "计划",
}

const CATEGORY_VARIANTS: Record<MemoryCategory, "blue" | "green" | "orange" | "purple"> = {
  preference: "blue",
  fact: "green",
  pattern: "orange",
  plan: "purple",
}

const SOURCE_LABELS: Record<string, string> = {
  user_stated: "用户声明",
  inferred: "推断",
  system: "系统",
}

export function MemoryDetailDialog({
  open,
  onOpenChange,
  memory,
  onEdit,
}: MemoryDetailDialogProps) {
  if (!memory) return null

  const handleEdit = () => {
    onEdit(memory)
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>记忆详情</DialogTitle>
        </DialogHeader>

        <div className="p-4 space-y-4">
          <div className="space-y-2">
            <label className="text-xs font-bold">类别</label>
            <div>
              <Badge variant={CATEGORY_VARIANTS[memory.category]} className="text-xs">
                {CATEGORY_LABELS[memory.category]}
              </Badge>
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-xs font-bold">键名 (Key)</label>
            <div className="text-sm font-mono bg-muted p-2 rounded border-classic-inset">
              {memory.key}
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-xs font-bold">值 (Value)</label>
            <div className="text-sm font-mono bg-muted p-2 rounded border-classic-inset whitespace-pre-wrap max-h-48 overflow-y-auto">
              {typeof memory.value === "object"
                ? JSON.stringify(memory.value, null, 2)
                : memory.value}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-xs font-bold">置信度</label>
              <div className="text-sm">
                <Badge variant="cyan">{Math.round(memory.confidence * 100)}%</Badge>
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-xs font-bold">来源</label>
              <div className="text-sm">
                <Badge variant="orange">{SOURCE_LABELS[memory.source] || memory.source}</Badge>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-xs font-bold">访问次数</label>
              <div className="text-sm">{memory.access_count} 次</div>
            </div>
            <div className="space-y-2">
              <label className="text-xs font-bold">创建时间</label>
              <div className="text-sm opacity-80">{formatTime(memory.created_at)}</div>
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-xs font-bold">最后访问</label>
            <div className="text-sm opacity-80">{formatTime(memory.last_accessed)}</div>
          </div>
        </div>

        <DialogFooter className="!mt-4 !mb-1 !mr-1 flex gap-1">
          <Button variant="secondary" onClick={() => onOpenChange(false)}>
            关闭
          </Button>
          <Button onClick={handleEdit}>
            编辑
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
