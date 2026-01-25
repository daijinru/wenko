import { useState, useEffect } from "react"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Slider } from "@/components/ui/slider"
import type { LongTermMemory, MemoryCategory, MemoryFormData, RepeatType } from "@/types/api"

interface MemoryFormDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  memory: LongTermMemory | null
  onSave: (data: MemoryFormData) => Promise<boolean>
}

const CATEGORIES: { value: MemoryCategory; label: string }[] = [
  { value: "preference", label: "偏好" },
  { value: "fact", label: "事实" },
  { value: "pattern", label: "模式" },
  { value: "plan", label: "计划" },
]

const REMINDER_OPTIONS = [
  { value: 0, label: '准时提醒' },
  { value: 5, label: '提前5分钟' },
  { value: 10, label: '提前10分钟' },
  { value: 30, label: '提前30分钟' },
  { value: 60, label: '提前1小时' },
]

const REPEAT_OPTIONS: { value: RepeatType; label: string }[] = [
  { value: 'none', label: '不重复' },
  { value: 'daily', label: '每天' },
  { value: 'weekly', label: '每周' },
  { value: 'monthly', label: '每月' },
]

function formatDateTimeLocal(dateStr: string): string {
  const date = new Date(dateStr)
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  return `${year}-${month}-${day}T${hours}:${minutes}`
}

function getDefaultTargetTime(): string {
  const defaultTime = new Date()
  defaultTime.setHours(defaultTime.getHours() + 1)
  defaultTime.setMinutes(0)
  return formatDateTimeLocal(defaultTime.toISOString())
}

export function MemoryFormDialog({
  open,
  onOpenChange,
  memory,
  onSave,
}: MemoryFormDialogProps) {
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState<MemoryFormData>({
    category: "fact",
    key: "",
    value: "",
    confidence: 0.9,
    target_time: getDefaultTargetTime(),
    reminder_offset_minutes: 10,
    repeat_type: 'none',
  })

  useEffect(() => {
    if (open) {
      if (memory) {
        setForm({
          category: memory.category,
          key: memory.key,
          value:
            typeof memory.value === "object"
              ? JSON.stringify(memory.value)
              : memory.value,
          confidence: memory.confidence,
          target_time: memory.target_time ? formatDateTimeLocal(memory.target_time) : getDefaultTargetTime(),
          reminder_offset_minutes: memory.reminder_offset_minutes ?? 10,
          repeat_type: memory.repeat_type ?? 'none',
        })
      } else {
        setForm({
          category: "fact",
          key: "",
          value: "",
          confidence: 0.9,
          target_time: getDefaultTargetTime(),
          reminder_offset_minutes: 10,
          repeat_type: 'none',
        })
      }
    }
  }, [open, memory])

  const handleSave = async () => {
    if (!form.key.trim()) {
      return
    }

    // For plan category, validate target_time
    if (form.category === 'plan' && !form.target_time) {
      return
    }

    setSaving(true)

    // Convert target_time to ISO string for plan category
    const formData: MemoryFormData = {
      ...form,
      target_time: form.category === 'plan' && form.target_time
        ? new Date(form.target_time).toISOString()
        : undefined,
    }

    const success = await onSave(formData)
    setSaving(false)

    if (success) {
      onOpenChange(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>{memory ? "编辑记忆" : "添加记忆"}</DialogTitle>
        </DialogHeader>

        <div className="p-4 space-y-4">
          <div className="space-y-2">
            <label className="text-xs font-bold">类别</label>
            <div className="flex gap-1 !mt-1 !mb-1">
              {CATEGORIES.map((cat) => (
                <Button
                  key={cat.value}
                  variant={form.category === cat.value ? "default" : "secondary"}
                  size="sm"
                  onClick={() => setForm((f) => ({ ...f, category: cat.value }))}
                >
                  {cat.label}
                </Button>
              ))}
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-xs font-bold">键名 (Key)</label>
            <Input
              value={form.key}
              onChange={(e) => setForm((f) => ({ ...f, key: e.target.value }))}
              placeholder="例如: preferred_language, name"
            />
          </div>

          <div className="space-y-2">
            <label className="text-xs font-bold">值 (Value)</label>
            <Textarea
              value={form.value}
              onChange={(e) => setForm((f) => ({ ...f, value: e.target.value }))}
              placeholder="输入记忆内容"
              rows={8}
            />
          </div>

          <div className="space-y-2">
            <label className="text-xs font-bold">
              置信度: {Math.round(form.confidence * 100)}%
            </label>
            <Slider
              value={[form.confidence * 100]}
              onValueChange={([value]) =>
                setForm((f) => ({ ...f, confidence: value / 100 }))
              }
              min={0}
              max={100}
              step={1}
            />
          </div>

          {/* Plan-specific fields */}
          {form.category === 'plan' && (
            <>
              <div className="space-y-2">
                <label className="text-xs font-bold">
                  目标时间 <span className="text-red-500">*</span>
                </label>
                <Input
                  type="datetime-local"
                  value={form.target_time || ''}
                  onChange={(e) => setForm((f) => ({ ...f, target_time: e.target.value }))}
                />
              </div>

              <div className="space-y-2">
                <label className="text-xs font-bold">提前提醒</label>
                <select
                  value={form.reminder_offset_minutes ?? 10}
                  onChange={(e) => setForm((f) => ({ ...f, reminder_offset_minutes: Number(e.target.value) }))}
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                >
                  {REMINDER_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-2">
                <label className="text-xs font-bold">重复</label>
                <select
                  value={form.repeat_type || 'none'}
                  onChange={(e) => setForm((f) => ({ ...f, repeat_type: e.target.value as RepeatType }))}
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                >
                  {REPEAT_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>
            </>
          )}
        </div>

        <DialogFooter className="!mt-4 !mb-1 !mr-1 flex gap-1">
          <Button variant="secondary" onClick={() => onOpenChange(false)}>
            取消
          </Button>
          <Button
            onClick={handleSave}
            disabled={saving || !form.key.trim() || (form.category === 'plan' && !form.target_time)}
          >
            {saving ? "保存中..." : "保存"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
