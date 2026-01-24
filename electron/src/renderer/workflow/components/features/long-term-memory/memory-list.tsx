import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Checkbox } from "@/components/ui/checkbox"
import { Spinner } from "@/components/ui/spinner"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { MemoryDetailDialog } from "./memory-detail-dialog"
import { formatTime, cn } from "@/lib/utils"
import type { LongTermMemory, MemoryCategory } from "@/types/api"

interface MemoryListProps {
  memories: LongTermMemory[]
  loading: boolean
  selectedIds: string[]
  onToggleSelect: (id: string) => void
  onEdit: (memory: LongTermMemory) => void
  onDelete: (id: string) => void
}

const CATEGORY_VARIANTS: Record<MemoryCategory, "blue" | "green" | "orange" | "purple"> = {
  preference: "blue",
  fact: "green",
  pattern: "orange",
  plan: "purple",
}

const REPEAT_TYPE_LABELS: Record<string, string> = {
  none: '不重复',
  daily: '每天',
  weekly: '每周',
  monthly: '每月',
}

const PLAN_STATUS_LABELS: Record<string, string> = {
  pending: '待执行',
  completed: '已完成',
  dismissed: '已取消',
  snoozed: '已暂停',
}

function formatPlanTime(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const isToday = date.toDateString() === now.toDateString()
  const tomorrow = new Date(now)
  tomorrow.setDate(tomorrow.getDate() + 1)
  const isTomorrow = date.toDateString() === tomorrow.toDateString()

  const timeStr = date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })

  if (isToday) {
    return `今天 ${timeStr}`
  } else if (isTomorrow) {
    return `明天 ${timeStr}`
  } else {
    return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' }) + ' ' + timeStr
  }
}

export function LongTermMemoryList({
  memories,
  loading,
  selectedIds,
  onToggleSelect,
  onEdit,
  onDelete,
}: MemoryListProps) {
  const [detailOpen, setDetailOpen] = useState(false)
  const [detailMemory, setDetailMemory] = useState<LongTermMemory | null>(null)

  const handleRowClick = (memory: LongTermMemory) => {
    setDetailMemory(memory)
    setDetailOpen(true)
  }

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
    <div className="border-classic-inset bg-card overflow-y-auto flex-1 min-h-0 !p-0">
      <table className="w-full text-xs border-collapse detailed">
        <thead className="bg-muted sticky top-0 z-10 font-bold text-muted-foreground">
          <tr>
            <th className="p-2 text-center border-b border-r border-border whitespace-nowrap w-8"></th>
            <th className="p-2 text-left border-b border-r border-border whitespace-nowrap w-40">键 / 类别</th>
            <th className="p-2 text-left border-b border-r border-border whitespace-nowrap">值</th>
            <th className="p-2 text-left border-b border-r border-border whitespace-nowrap w-32">属性</th>
            <th className="p-2 text-left border-b border-r border-border whitespace-nowrap w-32">统计</th>
            <th className="p-2 text-center border-b border-border whitespace-nowrap w-20">操作</th>
          </tr>
        </thead>
        <tbody>
          {memories.map((memory) => (
            <tr
              key={memory.id}
              className={cn(
                "cursor-pointer hover:bg-primary hover:text-primary-foreground group transition-colors",
                selectedIds.includes(memory.id) ? "bg-muted/50" : "even:bg-muted/30"
              )}
              onClick={() => handleRowClick(memory)}
            >
              <td className="p-2 border-b border-r border-border text-center" onClick={(e) => e.stopPropagation()}>
                <Checkbox
                  checked={selectedIds.includes(memory.id)}
                  onCheckedChange={() => onToggleSelect(memory.id)}
                />
              </td>
              <td className="p-2 border-b border-r border-border truncate max-w-[160px]">
                <div className="font-bold">{memory.key}</div>
                <Badge variant={CATEGORY_VARIANTS[memory.category]} className="text-[9px] px-1 h-4 mt-1">
                  {memory.category}
                </Badge>
              </td>
              <td className="p-2 border-b border-r border-border max-w-[300px]">
                {memory.category === 'plan' && memory.target_time ? (
                  <div className="space-y-1">
                    <div className="line-clamp-2 whitespace-pre-wrap text-[11px] font-mono opacity-90">
                      {typeof memory.value === "object"
                        ? JSON.stringify(memory.value, null, 2)
                        : memory.value}
                    </div>
                    <div className="flex flex-wrap gap-1 mt-1">
                      <Badge variant="purple" className="text-[9px] px-1 h-4">
                        {formatPlanTime(memory.target_time)}
                      </Badge>
                      {memory.repeat_type && memory.repeat_type !== 'none' && (
                        <Badge variant="cyan" className="text-[9px] px-1 h-4">
                          {REPEAT_TYPE_LABELS[memory.repeat_type] || memory.repeat_type}
                        </Badge>
                      )}
                      {memory.plan_status && (
                        <Badge
                          variant={memory.plan_status === 'completed' ? 'green' : memory.plan_status === 'dismissed' ? 'orange' : 'blue'}
                          className="text-[9px] px-1 h-4"
                        >
                          {PLAN_STATUS_LABELS[memory.plan_status] || memory.plan_status}
                        </Badge>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="line-clamp-3 whitespace-pre-wrap text-[11px] font-mono opacity-90">
                    {typeof memory.value === "object"
                      ? JSON.stringify(memory.value, null, 2)
                      : memory.value}
                  </div>
                )}
              </td>
              <td className="p-2 border-b border-r border-border">
                <div className="flex flex-col space-y-1">
                  <Badge variant="cyan" className="text-[9px] px-1 h-4 w-full justify-center">
                    置信度: {Math.round(memory.confidence * 100)}%
                  </Badge>
                  <Badge variant="orange" className="text-[9px] px-1 h-4 w-full justify-center">
                    记忆来源：{memory.source}
                  </Badge>
                </div>
              </td>
              <td className="p-2 border-b border-r border-border text-[10px]">
                <div className="space-y-0.5">
                  <div>访问: {memory.access_count}次</div>
                  <div className="opacity-70">创建: {formatTime(memory.created_at)}</div>
                  <div className="opacity-70">最后: {formatTime(memory.last_accessed)}</div>
                </div>
              </td>
              <td className="p-2 border-b border-border text-center">
                <div className="flex flex-row gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  <Button
                    size="sm"
                    variant="ghost"
                    className="h-3 text-[10px] px-2 bg-background/50 hover:bg-background text-foreground"
                    onClick={(e) => {
                      e.stopPropagation()
                      onEdit(memory)
                    }}
                  >
                    编辑
                  </Button>
                  <Button
                    variant="destructive"
                    size="sm"
                    className="h-3 text-[10px] px-2"
                    onClick={(e) => {
                      e.stopPropagation()
                      onDelete(memory.id)
                    }}
                  >
                    删除
                  </Button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <MemoryDetailDialog
        open={detailOpen}
        onOpenChange={setDetailOpen}
        memory={detailMemory}
        onEdit={onEdit}
      />
    </div>
  )
}
